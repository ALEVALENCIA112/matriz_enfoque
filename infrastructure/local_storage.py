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
                json.dump({"tasks": [], "pending_ops": []}, f, indent=4)

    def _read_raw(self) -> Dict[str, Any]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"tasks": [], "pending_ops": []}
        
    def _write_raw(self, data: Dict[str, Any]) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_all_tasks(self) -> List[KanbanTask]:
        """Devuelve solo las tareas que están activas (no marcadas como eliminadas localmente)."""
        raw = self._read_raw()
        tasks = []
        for item in raw.get("tasks", []):
            # Ignorar si está marcada como eliminada localmente (Tombstone)
            if item.get("is_deleted_locally", False):
                continue
                
            task = KanbanTask(task_id=item["id"], title=item["title"])
            task.column = KanbanColumn(item["column"])
            task.symbol = BuJoSymbol(item["symbol"])
            task.is_starred = item.get("is_starred", False)
            task.is_inspired = item.get("is_inspired", False)
            task.is_archived = item.get("is_archived", False)
            tasks.append(task)
        return tasks

    def get_all_raw_tasks_including_deleted(self) -> List[Dict[str, Any]]:
        """Devuelve los diccionarios primitivos de todas las tareas (util para el sync engine)."""
        return self._read_raw().get("tasks", [])

    def save_task(self, task: KanbanTask) -> None:
        """Guarda o actualiza una tarea en el almacenamiento local."""
        raw = self._read_raw()
        tasks_list = raw["tasks"]
        
        # Mapeamos a diccionario primitivo
        task_data = {
            "id": task.id,
            "title": task.title,
            "column": task.column.value,
            "symbol": task.symbol.value,
            "is_starred": task.is_starred,
            "is_inspired": task.is_inspired,
            "is_archived": getattr(task, 'is_archived', False),
            "is_deleted_locally": False  # Asegurar que esté activa
        }
        
        # Reemplazar si ya existe, si no agregar
        updated = False
        for i, t in enumerate(tasks_list):
            if t["id"] == task.id:
                tasks_list[i] = task_data
                updated = True
                break
        if not updated:
            tasks_list.append(task_data)
            
        raw["tasks"] = tasks_list
        self._write_raw(raw)

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

    def remove_pending_op(self, action: str, task_id: str) -> None:
        raw = self._read_raw()
        raw["pending_ops"] = [op for op in raw["pending_ops"] if not (op["action"] == action and op["task_id"] == task_id)]
        self._write_raw(raw)