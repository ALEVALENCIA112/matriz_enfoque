# core/interfaces.py
from abc import ABC, abstractmethod
from typing import List
from core.entities import KanbanTask


class ITaskRepository(ABC):
    """Contrato abstracto para el almacenamiento de tareas (SOLID - DIP)."""
    
    @abstractmethod
    def save_task(self, task: KanbanTask) -> None:
        """Guarda o actualiza una tarea."""
        pass

    @abstractmethod
    def get_all_tasks(self) -> List[KanbanTask]:
        """Carga perezosa (JIT): Devuelve la lista completa de tareas desde el medio físico."""
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> None:
        """Elimina una tarea por su ID."""
        pass

    def get_metrics(self) -> dict:
        """Retorna las métricas históricas acumuladas."""
        return {"tareas_completadas": 0, "actividades_clave_completadas": 0}

    def increment_metrics(self, completed_tasks: int = 0, completed_key_activities: int = 0) -> None:
        """Incrementa las métricas de rendimiento acumuladas."""
        pass