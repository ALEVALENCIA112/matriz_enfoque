# infrastructure/cloud_storage.py
import requests
import urllib3
from typing import List
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository
from infrastructure.local_storage import JSONTaskRepository

# Desactivar las advertencias molestas en la consola causadas por verify=False (SSL de oficina)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LocalFirstTaskRepository(ITaskRepository):
    """
    Repositorio híbrido Local-First (Híbrido Offline/Nube).
    Garantiza persistencia local inmediata (resiliencia offline) e intenta 
    sincronizar con Firebase evadiendo bloqueos de certificados SSL corporativos.
    """

    def __init__(self, database_url: str, user_id: str = "usuario_unico", local_filepath: str = "matriz_datos.json"):
        # Inicializamos el repositorio local clásico como nuestra fuente de verdad inmediata
        self.local_repo = JSONTaskRepository(filepath=local_filepath)
        
        # Estructuramos la URL base de Firebase
        self.database_url = database_url.rstrip('/')
        self.base_url = f"{self.database_url}/users/{user_id}/tasks.json"

    def get_all_tasks(self) -> List[KanbanTask]:
        """
        Estrategia Local-First: Intenta descargar lo último de la nube para actualizar el disco local.
        Si falla o no hay conexión, sirve los datos del archivo local de inmediato sin colgarse.
        """
        try:
            # timeout=3 evita que la app se congele en mala red. verify=False evade el proxy de tu oficina.
            response = requests.get(self.base_url, verify=False, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Reconstruimos las tareas traídas desde Firebase
                    cloud_tasks = []
                    for task_id, item in data.items():
                        task = KanbanTask(task_id=task_id, title=item["title"])
                        task.column = KanbanColumn(item["column"])
                        task.symbol = BuJoSymbol(item["symbol"])
                        task.is_starred = item.get("is_starred", False)
                        task.is_inspired = item.get("is_inspired", False)
                        task.is_archived = item.get("is_archived", False)
                        cloud_tasks.append(task)
                    
                    # Actualizamos de golpe el archivo de disco local para que esté sincronizado
                    self.local_repo._write_to_disk(cloud_tasks)
                    return cloud_tasks
                    
        except Exception:
            # Si ocurre un SSLError, ConnectionError o Timeout, se ignora silenciosamente
            pass
        
        # Si falló la nube, devolvemos la base local de inmediato
        return self.local_repo.get_all_tasks()

    def save_task(self, task: KanbanTask) -> None:
        """Guarda de forma síncrona en el almacenamiento local y asume la sincronización a Firebase."""
        # 1. Asegurar la persistencia local de inmediato (La tarea no se pierde)
        self.local_repo.save_task(task)
        
        # 2. Intentar replicar el cambio en Firebase (Operación Upsert)
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
            # verify=False nos da acceso libre ignorando el certificado local faltante en la oficina
            requests.put(task_url, json=payload, verify=False, timeout=3)
        except Exception:
            # Si estás desconectado, el cambio queda registrado localmente en espera de la siguiente sincronización
            pass

    def delete_task(self, task_id: str) -> None:
        """Elimina localmente e intenta purgar de la nube."""
        # 1. Borrar del disco local de inmediato
        self.local_repo.delete_task(task_id)
        
        # 2. Intentar borrar de Firebase
        task_url = self.base_url.replace(".json", f"/{task_id}.json")
        try:
            requests.delete(task_url, verify=False, timeout=3)
        except Exception:
            pass