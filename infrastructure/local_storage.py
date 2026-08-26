# infrastructure/local_storage.py
import json
import os
import sys
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository


def resolve_storage_path(filename: str) -> str:
    """
    Resuelve una ruta de almacenamiento segura y persistente según la plataforma
    (Windows Desktop, macOS, Linux, y Android APK con Flet).
    """
    # Si ya es una ruta absoluta válida y writable, usarla
    if os.path.isabs(filename):
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception:
                pass
        return filename

    # 1. Detección de Android APK en Flet / Kivy / Chaquopy
    is_android = "ANDROID_DATA" in os.environ or "ANDROID_ROOT" in os.environ or "FLET_APP_STORAGE_DATA" in os.environ
    if is_android:
        # En Android Flet, usar la carpeta de almacenamiento de la app o el home
        app_storage = os.environ.get("FLET_APP_STORAGE_DATA")
        if app_storage and os.path.exists(app_storage):
            return os.path.join(app_storage, filename)
        user_home = os.path.expanduser("~")
        if user_home and os.path.exists(user_home):
            return os.path.join(user_home, filename)

    # 2. Detección de ejecutable empaquetado con PyInstaller
    if getattr(sys, 'frozen', False):
        # En ejecutable, guardar junto al .exe o en %APPDATA%
        exe_dir = os.path.dirname(sys.executable)
        test_file = os.path.join(exe_dir, ".write_test")
        try:
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return os.path.join(exe_dir, filename)
        except Exception:
            # Si el directorio del exe no es escribible (ej. Program Files), usar AppData / Home
            app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
            target_dir = os.path.join(app_data, "MatrizEnfoque")
            os.makedirs(target_dir, exist_ok=True)
            return os.path.join(target_dir, filename)

    # 3. Entorno de desarrollo local normal
    # Probar si el directorio actual es escribible
    try:
        test_file = os.path.join(".", ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return os.path.abspath(filename)
    except Exception:
        app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
        target_dir = os.path.join(app_data, "MatrizEnfoque")
        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, filename)


class JSONTaskRepository(ITaskRepository):
    """
    Implementación concreta de persistencia basada en JSON (SOLID - DIP).
    Almacena el estado transaccional local con alta resiliencia y soporte offline-first.
    """

    def __init__(self, filepath: str = "matriz_datos.json"):
        self.raw_filepath = filepath
        self.filepath = resolve_storage_path(filepath)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Crea el archivo con la estructura base si no existe."""
        if not os.path.exists(self.filepath):
            dir_name = os.path.dirname(self.filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            self._write_raw({
                "tasks": [], 
                "pending_ops": [],
                "historico_metricas": {"tareas_completadas": 0, "actividades_clave_completadas": 0}
            })

    def _read_raw(self) -> Dict[str, Any]:
        default_structure = {
            "tasks": [], 
            "pending_ops": [],
            "historico_metricas": {"tareas_completadas": 0, "actividades_clave_completadas": 0}
        }
        if not os.path.exists(self.filepath):
            return default_structure
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = json.load(f)
                if not isinstance(content, dict):
                    return default_structure
                if "tasks" not in content:
                    content["tasks"] = []
                if "pending_ops" not in content:
                    content["pending_ops"] = []
                if "historico_metricas" not in content:
                    content["historico_metricas"] = default_structure["historico_metricas"]
                return content
        except (json.JSONDecodeError, IOError):
            return default_structure
        
    def _write_raw(self, data: Dict[str, Any]) -> None:
        """Escritura atómica segura para evitar corrupción de datos en caso de corte."""
        dir_name = os.path.dirname(self.filepath) or "."
        try:
            # Escribir primero en archivo temporal en el mismo directorio
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=4, ensure_ascii=False)
                temp_name = tf.name
            
            # Reemplazo atómico
            if os.path.exists(self.filepath):
                os.replace(temp_name, self.filepath)
            else:
                os.rename(temp_name, self.filepath)
        except Exception:
            # Fallback a escritura directa
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ Error al escribir datos locales en {self.filepath}: {e}")

    def save_task(self, task: KanbanTask) -> None:
        """Guarda o actualiza una tarea en el almacenamiento local."""
        raw = self._read_raw()

        task_data = {
            "id": task.id,
            "title": task.title,
            "symbol": task.symbol.value,
            "column": task.column.value,
            "is_starred": getattr(task, 'is_starred', False),
            "is_inspired": getattr(task, 'is_inspired', False),
            "created_at": task.created_at.isoformat() if hasattr(task, 'created_at') and task.created_at else datetime.now().isoformat(),
            "is_archived": getattr(task, 'is_archived', False),
            "is_deleted_locally": False
        }

        exists = False
        for i, t in enumerate(raw["tasks"]):
            if t["id"] == task.id:
                raw["tasks"][i] = task_data
                exists = True
                break
        if not exists:
            raw["tasks"].append(task_data)

        self._write_raw(raw)

    def get_all_tasks(self) -> List[KanbanTask]:
        """Devuelve solo las tareas activas (no marcadas como eliminadas localmente)."""
        raw = self._read_raw()
        domain_tasks = []
        for t in raw.get("tasks", []):
            if t.get("is_deleted_locally", False):
                continue
            try:
                created_dt = None
                if "created_at" in t and t["created_at"]:
                    try:
                        created_dt = datetime.fromisoformat(t["created_at"])
                    except Exception:
                        created_dt = None

                sym_val = t.get("symbol", BuJoSymbol.TASK_PENDING.value)
                # Resolver símbolo de forma segura
                symbol = BuJoSymbol.TASK_PENDING
                for s in BuJoSymbol:
                    if s.value == sym_val:
                        symbol = s
                        break

                col_val = t.get("column", KanbanColumn.TO_DO.value)
                column = KanbanColumn.TO_DO
                for c in KanbanColumn:
                    if c.value == col_val:
                        column = c
                        break

                task = KanbanTask(task_id=t["id"], title=t.get("title", ""), symbol=symbol, created_at=created_dt)
                task.column = column
                task.is_starred = bool(t.get("is_starred", False))
                task.is_inspired = bool(t.get("is_inspired", False))
                task.is_archived = bool(t.get("is_archived", False))
                domain_tasks.append(task)
            except Exception:
                continue
        return domain_tasks

    def get_all_raw_tasks_including_deleted(self) -> List[Dict[str, Any]]:
        """Devuelve todas las tareas crudas incluyendo las marcadas para eliminación (necesario para el sync)."""
        return self._read_raw().get("tasks", [])

    def delete_task(self, task_id: str) -> None:
        """Aplica una 'lápida' (soft-delete) para que el motor de sincronización sepa que debe borrarla de Firebase."""
        raw = self._read_raw()
        for t in raw.get("tasks", []):
            if t["id"] == task_id:
                t["is_deleted_locally"] = True
                break
        self._write_raw(raw)

    def hard_delete_task(self, task_id: str) -> None:
        """Elimina físicamente del JSON (usado tras confirmar sincronización o purgar)."""
        raw = self._read_raw()
        raw["tasks"] = [t for t in raw.get("tasks", []) if t["id"] != task_id]
        self._write_raw(raw)

    # --- Gestión de operaciones pendientes de sincronización ---

    def get_pending_ops(self) -> List[Dict[str, Any]]:
        return self._read_raw().get("pending_ops", [])

    def add_pending_op(self, action: str, task_id: str) -> None:
        raw = self._read_raw()
        ops = raw.get("pending_ops", [])

        if action == "delete":
            # Si se va a eliminar, remover cualquier operación "save" pendiente previa de la misma tarea
            ops = [op for op in ops if op.get("task_id") != task_id]
            ops.append({"action": "delete", "task_id": task_id})
        elif action == "save":
            # Evitar duplicar "save" si ya está en cola
            if not any(op.get("action") == "save" and op.get("task_id") == task_id for op in ops):
                ops.append({"action": "save", "task_id": task_id})

        raw["pending_ops"] = ops
        self._write_raw(raw)

    def remove_pending_op(self, action: str, task_id: str) -> None:
        """Remueve una operación específica de la cola una vez completada con éxito."""
        raw = self._read_raw()
        ops = raw.get("pending_ops", [])
        raw["pending_ops"] = [op for op in ops if not (op.get("action") == action and op.get("task_id") == task_id)]
        self._write_raw(raw)

    def clear_pending_ops(self, ops_to_remove: List[Dict[str, Any]]) -> None:
        raw = self._read_raw()
        raw["pending_ops"] = [op for op in raw.get("pending_ops", []) if op not in ops_to_remove]
        self._write_raw(raw)

    # --- Métricas Históricas ---

    def get_metrics(self) -> Dict[str, int]:
        return self._read_raw().get("historico_metricas", {"tareas_completadas": 0, "actividades_clave_completadas": 0})

    def increment_metrics(self, completed_tasks: int = 0, completed_key_activities: int = 0) -> None:
        raw = self._read_raw()
        if "historico_metricas" not in raw:
            raw["historico_metricas"] = {"tareas_completadas": 0, "actividades_clave_completadas": 0}
        raw["historico_metricas"]["tareas_completadas"] += completed_tasks
        raw["historico_metricas"]["actividades_clave_completadas"] += completed_key_activities
        self._write_raw(raw)