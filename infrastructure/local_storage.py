# infrastructure/local_storage.py
import json
import os
from typing import List
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
                json.dump([], f)

    def get_all_tasks(self) -> List[KanbanTask]:
        """Carga perezosa (JIT): Lee el archivo físico únicamente bajo demanda."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data_list = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        tasks = []
        for item in data_list:
            task = KanbanTask(task_id=item["id"], title=item["title"])
            task.column = KanbanColumn(item["column"])
            task.symbol = BuJoSymbol(item["symbol"])
            task.is_starred = item.get("is_starred", False)
            task.is_inspired = item.get("is_inspired", False)
            # Leemos el campo del JSON y se lo asignamos al objeto reconstruido
            task.is_archived = item.get("is_archived", False)
            tasks.append(task)
        return tasks

    def save_task(self, task: KanbanTask) -> None:
        """Guarda una tarea nueva o actualiza una existente (Upsert)."""
        tasks = self.get_all_tasks()
        
        # Diccionario intermedio para actualizar de forma eficiente
        task_dict = {t.id: t for t in tasks}
        task_dict[task.id] = task
        
        self._write_to_disk(list(task_dict.values()))

    def delete_task(self, task_id: str) -> None:
        tasks = self.get_all_tasks()
        filtered_tasks = [t for t in tasks if t.id != task_id]
        self._write_to_disk(filtered_tasks)

    def _write_to_disk(self, tasks: List[KanbanTask]) -> None:
        """Traduce los objetos del dominio a estructuras primitivas nativas de JSON."""
        serializable_data = []
        for t in tasks:
            serializable_data.append({
                "id": t.id,
                "title": t.title,
                "column": t.column.value,
                "symbol": t.symbol.value,
                "is_starred": t.is_starred,
                "is_inspired": t.is_inspired,
                "is_archived": getattr(t, 'is_archived', False)
            })
            
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=4, ensure_ascii=False)