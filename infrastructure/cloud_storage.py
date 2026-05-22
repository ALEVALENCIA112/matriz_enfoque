# infrastructure/cloud_storage.py
import urllib.request
import json
import ssl
from typing import List, Dict, Any
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository
from infrastructure.local_storage import JSONTaskRepository

class LocalFirstTaskRepository(ITaskRepository):
    """
    Repositorio Local-First Avanzado con Sincronización Diferida Bidireccional.
    Resuelve conflictos de desconexión tanto para ejecutables de PC como para APKs.
    """

    def __init__(self, database_url: str, user_id: str = "usuario_unico", local_filepath: str = "matriz_datos.json"):
        self.local_repo = JSONTaskRepository(filepath=local_filepath)
        self.database_url = database_url.rstrip('/')
        self.base_url = f"{self.database_url}/users/{user_id}/tasks.json"
        self.ssl_context = ssl._create_unverified_context()

    def _net_request(self, url: str, data: bytes = None, method: str = 'GET') -> Any:
        """Helper centralizado para realizar peticiones HTTP seguras contra fallos de red."""
        req = urllib.request.Request(url=url, method=method)
        if data:
            req.data = data
            req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, context=self.ssl_context, timeout=4) as response:
            if method == 'GET':
                return json.loads(response.read().decode('utf-8'))
        return None

    def _sync_pending_operations(self) -> bool:
        """Intenta vaciar la cola local de cambios hacia Firebase. Devuelve True si hubo éxito de red."""
        try:
            pending_ops = self.local_repo.get_pending_ops()
            all_local_raw = self.local_repo.get_all_raw_tasks_including_deleted()
            local_tasks_dict = {t["id"]: t for t in all_local_raw}

            for op in list(pending_ops):
                action = op["action"]
                tid = op["task_id"]
                task_url = self.base_url.replace(".json", f"/{tid}.json")

                if action == "save" and tid in local_tasks_dict:
                    # Si la tarea fue borrada después de ser editada offline, ignoramos el save
                    if local_tasks_dict[tid].get("is_deleted_locally", False):
                        self.local_repo.remove_pending_op("save", tid)
                        continue
                    
                    # Subir estado actual a Firebase
                    payload = local_tasks_dict[tid].copy()
                    payload.pop("is_deleted_locally", None)  # No ensuar Firebase con banderas locales
                    data_bytes = json.dumps(payload).encode('utf-8')
                    self._net_request(url=task_url, data=data_bytes, method='PUT')
                    self.local_repo.remove_pending_op("save", tid)

                elif action == "delete":
                    # Purgar de Firebase
                    self._net_request(url=task_url, method='DELETE')
                    self.local_repo.remove_pending_op("delete", tid)
                    self.local_repo.hard_delete_task(tid)  # Ahora sí, borrado físico total

            return True
        except Exception:
            return False  # Sin conexión, reintentará en el siguiente ciclo

    def get_all_tasks(self) -> List[KanbanTask]:
        """Sincroniza de forma bidireccional si hay internet y consolida la Base de Datos Local."""
        # 1. Intentar subir cambios locales pendientes primero
        has_internet = self._sync_pending_operations()

        if has_internet:
            try:
                # 2. Descargar el estado maestro actual de Firebase
                cloud_data = self._net_request(self.base_url, method='GET') or {}
                
                # Obtener lo que tenemos localmente antes de sincronizar
                local_raw = self.local_repo.get_all_raw_tasks_including_deleted()
                local_tasks_dict = {t["id"]: t for t in local_raw}

                # 3. Mezclar nubes y tierra (Unificación Dinámica)
                # Si una tarea está en Firebase pero no está en nuestro local y no está marcada como borrada
                for tid, cloud_task in cloud_data.items():
                    if cloud_task is None:
                        continue
                    
                    if tid not in local_tasks_dict:
                        # Tarea nueva creada desde el otro dispositivo (ej: creada en PC, descargándose en APK)
                        new_task = KanbanTask(task_id=tid, title=cloud_task["title"])
                        new_task.column = KanbanColumn(cloud_task["column"])
                        new_task.symbol = BuJoSymbol(cloud_task["symbol"])
                        new_task.is_starred = cloud_task.get("is_starred", False)
                        new_task.is_inspired = cloud_task.get("is_inspired", False)
                        self.local_repo.save_task(new_task)
                    else:
                        # Si existe en ambos lados, respetamos el estado local si tiene operaciones pendientes, 
                        # si no, actualizamos con lo de la nube
                        is_deleted_here = local_tasks_dict[tid].get("is_deleted_locally", False)
                        has_pending_save = any(op["action"] == "save" and op["task_id"] == tid for op in self.local_repo.get_pending_ops())
                        
                        if not is_deleted_here and not has_pending_save:
                            # Actualización limpia desde el exterior
                            updated_task = KanbanTask(task_id=tid, title=cloud_task["title"])
                            updated_task.column = KanbanColumn(cloud_task["column"])
                            updated_task.symbol = BuJoSymbol(cloud_task["symbol"])
                            updated_task.is_starred = cloud_task.get("is_starred", False)
                            updated_task.is_inspired = cloud_task.get("is_inspired", False)
                            self.local_repo.save_task(updated_task)

                # 4. Limpieza inversa: Si una tarea está en local pero NO está en Firebase, y NO tiene cambios pendientes, 
                # significa que fue eliminada desde el OTRO dispositivo. Debemos borrarla localmente.
                for tid, local_task in local_tasks_dict.items():
                    if local_task.get("is_deleted_locally", False):
                        continue
                    
                    # Si no está en la nube y no está pendiente por subirse desde aquí, el otro dispositivo la borró
                    has_pending_save = any(op["action"] == "save" and op["task_id"] == tid for op in self.local_repo.get_pending_ops())
                    if tid not in cloud_data and not has_pending_save:
                        self.local_repo.hard_delete_task(tid)

            except Exception:
                pass  # Si Firebase falla a mitad de la lectura, nos replegamos al modo offline de inmediato

        # 5. La fuente de la verdad para la UI siempre es el almacenamiento local consolidado
        return self.local_repo.get_all_tasks()

    def save_task(self, task: KanbanTask) -> None:
        """Persiste inmediatamente en local y encola la sincronización con la nube."""
        # Escribir a disco local de inmediato (Resiliencia Offline absoluta)
        self.local_repo.save_task(task)
        self.local_repo.add_pending_op("save", task.id)
        
        # Intentar vaciar la cola inmediatamente por si hay internet reactivo
        self._sync_pending_operations()

    def delete_task(self, task_id: str) -> None:
        """Marca para eliminación local y encola el borrado en la nube."""
        self.local_repo.delete_task(task_id)
        self.local_repo.add_pending_op("delete", task_id)
        
        # Intentar procesar el borrado en la nube de inmediato
        self._sync_pending_operations()