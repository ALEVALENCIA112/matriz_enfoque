# infrastructure/cloud_storage.py
import requests
from typing import List
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository


class FirebaseTaskRepository(ITaskRepository):
    """
    Implementación de persistencia en la nube usando Firebase Realtime Database.
    Cumple con el DIP (Dependency Inversion Principle) al heredar de ITaskRepository.
    """

    def __init__(self, database_url: str, user_id: str = "usuario_unico"):
        """
        :param database_url: La URL de tu base de datos de Firebase (ej: https://tu-app.firebaseio.com/)
        :param user_id: ID para separar tus tareas en la nube (útil para cuando conectes el móvil)
        """
        # Aseguramos que la URL termine en barra diagonal y apunte al nodo de tareas
        self.base_url = f"{database_url.rstrip('/')}/users/{user_id}/tasks.json"

    def get_all_tasks(self) -> List[KanbanTask]:
        """Obtiene todas las tareas en tiempo real desde Firebase."""
        try:
            response = requests.get(self.base_url)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if not data:
                return []

            tasks = []
            # Firebase guarda los datos como un diccionario de diccionarios {id: {datos}}
            for task_id, item in data.items():
                task = KanbanTask(task_id=task_id, title=item["title"])
                task.column = KanbanColumn(item["column"])
                task.symbol = BuJoSymbol(item["symbol"])
                task.is_starred = item.get("is_starred", False)
                task.is_inspired = item.get("is_inspired", False)
                task.is_archived = item.get("is_archived", False)
                tasks.append(task)
            return tasks
            
        except Exception as e:
            print(f"⚠️ Error de conexión con Firebase: {e}")
            return []

    def save_task(self, task: KanbanTask) -> None:
        """Guarda o actualiza una tarea en Firebase (Operación Upsert)."""
        # Creamos la URL específica para el ID de esta tarea
        task_url = self.base_url.replace(".json", f"/{task.id}.json")
        
        payload = {
            "title": task.title,
            "column": task.column.value,
            "symbol": task.symbol.value,
            "is_starred": task.is_starred,
            "is_inspired": task.is_inspired,
            "is_archived": getattr(task, 'is_archived', False)
        }
        
        try:
            # PUT sobreescribe o crea el nodo exactamente con ese ID
            requests.put(task_url, json=payload)
        except Exception as e:
            print(f"⚠️ No se pudo guardar en la nube: {e}")

    def delete_task(self, task_id: str) -> None:
        """Elimina la tarea de la base de datos en la nube."""
        task_url = self.base_url.replace(".json", f"/{task_id}.json")
        try:
            requests.delete(task_url)
        except Exception as e:
            print(f"⚠️ No se pudo eliminar de la nube: {e}")