# core/use_cases.py
from typing import List, Optional
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository


class KanbanManager:
    """Caso de uso para gestionar las reglas del Tablero Kanban."""
    
    def __init__(self, repository: ITaskRepository):
        self.repository = repository

    def create_bujo_item(self, item_id: str, title: str, symbol: BuJoSymbol) -> KanbanTask:
        """Crea una entrada respetando la nomenclatura unificada."""
        tasks = self.repository.get_all_tasks()
        
        # Regla de negocio TDAH: Solo puede haber una Actividad Clave (AC) activa en Por Hacer
        if symbol == BuJoSymbol.KEY_ACTIVITY:
            for t in tasks:
                if t.symbol == BuJoSymbol.KEY_ACTIVITY and t.column != KanbanColumn.DONE:
                    raise ValueError("⚠️ Ya definiste tu Actividad Clave (AC) para hoy. ¡Mantén el enfoque!")

        new_task = KanbanTask(item_id, title, symbol)
        self.repository.save_task(new_task)
        return new_task

    def move_task(self, task_id: str, target_column: KanbanColumn) -> Optional[KanbanTask]:
        """Cambia de columna un Post-it/Elemento y dispara las mutaciones de símbolos correspondientes."""
        tasks = self.repository.get_all_tasks()
        for task in tasks:
            if task.id == task_id:
                task.move_to(target_column)
                self.repository.save_task(task)
                return task
        return None

    def toggle_signifier(self, item_id: str, signifier_type: str) -> Optional[KanbanTask]:
        """Añade o quita marcadores extra de contexto (* o !) para evitar la ceguera visual."""
        tasks = self.repository.get_all_tasks()
        for item in tasks:
            if item.id == item_id:
                if signifier_type == "priority":
                    item.is_starred = not item.is_starred
                elif signifier_type == "inspiration":
                    item.is_inspired = not item.is_inspired
                self.repository.save_task(item)
                return item
        return None

    def get_items_by_column(self, column: KanbanColumn) -> List[KanbanTask]:
        """Carga perezosa (JIT): Filtra bajo demanda los elementos de una columna específica."""
        all_tasks = self.repository.get_all_tasks()
        # Modificación: Ya no filtramos por 'is_archived', devolvemos la columna limpia
        return [t for t in all_tasks if t.column == column]
    
    def archive_done_tasks(self) -> None:
        """Marca todas las tareas en la columna 'Hecho' como archivadas para despejar el tablero."""
        all_tasks = self.repository.get_all_tasks()
        for task in all_tasks:
            if task.column == KanbanColumn.DONE:
                # Modificación: En lugar de guardar con bandera, borramos directamente
                self.repository.delete_task(task.id)