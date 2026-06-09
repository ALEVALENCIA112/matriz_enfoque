# infrastructure/local_storage.py
import json
import os
from typing import List, Dict, Any
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository


class JSONTaskRepository(ITaskRepository):
    """
    Implementación concreta de persistencia basada en JSON (SOLID - DIP).
    Aplica conceptos de SCP aislando por completo el manejo del disco de la lógica de negocio.
    """

    def __init__(self, filepath: str = "matriz_datos.json"):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "tasks": [], 
                    "pending_ops": [],
                    "historico_metricas": {"tareas_completadas": 0, "actividades_clave_completadas": 0}
                }, f, indent=4, ensure_ascii=False)

    def _read_raw(self) -> Dict[str, Any]:
        default_structure = {
            "tasks": [], 
            "pending_ops": [],
            "historico_metricas": {"tareas_completadas": 0, "actividades_clave_completadas": 0}
        }
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = json.load(f)
                if "historico_metricas" not in content:
                    content["historico_metricas"] = default_structure["historico_metricas"]
                return content
        except (json.JSONDecodeError, IOError):
            return default_structure
        
    def _write_raw(self, data: Dict[str, Any]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def save_task(self, task: KanbanTask) -> None:
        """Guarda o actualiza una tarea en el almacenamiento local."""
        raw = self._read_raw()

        # Mapeamos a diccionario primitivo
        task_data = {
            "id": task.id,
            "title": task.title,
            "symbol": task.symbol.value,
            "column": task.column.value,
            "is_starred": task.is_starred,
            "is_inspired": task.is_inspired,
            "created_at": task.created_at.isoformat(),
            "is_archived": getattr(task, 'is_archived', False)
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
        """Devuelve solo las tareas que están activas (no marcadas como eliminadas localmente)."""
        raw = self._read_raw()
        domain_tasks = []
        for t in raw["tasks"]:
            if t.get("is_deleted_locally", False):
                continue
            try:
                task = KanbanTask(task_id=t["id"], title=t["title"], symbol=BuJoSymbol(t["symbol"]))
                task.column = KanbanColumn(t["column"])
                task.is_starred = t.get("is_starred", False)
                task.is_inspired = t.get("is_inspired", False)
                task.is_archived = t.get("is_archived", False)
                if t.get("is_archived", False):
                    task.is_archived = True
                domain_tasks.append(task)
            except Exception:
                continue
        return domain_tasks

    def delete_task(self, task_id: str) -> None:
        """Aplica una 'lápida' (soft-delete) para que el motor de sincronización sepa que debe borrarla de Firebase."""
        raw = self._read_raw()
        for t in raw["tasks"]:
            if t["id"] == task_id:
                t["is_deleted_locally"] = True
                break
        self._write_raw(raw)

    def hard_delete_task(self, task_id: str) -> None:
        """Elimina físicamente del JSON (usado solo tras confirmar sincronización con la nube)."""
        raw = self._read_raw()
        raw["tasks"] = [t for t in raw["tasks"] if t["id"] != task_id]
        self._write_raw(raw)

    # --- Gestión de operaciones pendientes ---
    def get_pending_ops(self) -> List[Dict[str, Any]]:
        return self._read_raw().get("pending_ops", [])

    def add_pending_op(self, action: str, task_id: str) -> None:
        raw = self._read_raw()
        # Evitar duplicar la misma acción exacta para la misma tarea en la cola
        exists = any(op["action"] == action and op["task_id"] == task_id for op in raw["pending_ops"])
        if not exists:
            raw["pending_ops"].append({"action": action, "task_id": task_id})
            self._write_raw(raw)

    def clear_pending_ops(self, ops_to_remove: List[Dict[str, Any]]) -> None:
        raw = self._read_raw()
        raw["pending_ops"] = [op for op in raw["pending_ops"] if op not in ops_to_remove]
        self._write_raw(raw)