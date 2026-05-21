# controllers/main_controller.py
import uuid
from typing import Callable, List, Optional
from core.entities import KanbanColumn, BuJoSymbol, PomodoroInverse, KanbanTask
from core.use_cases import KanbanManager

class MainController:
    """
    Controlador central de la aplicación (MVC).
    Mantiene la alta cohesión delegando las operaciones a los casos de uso del Core
    y notificando a la Vista mediante Callbacks sin acoplarse a ella.
    """
    
    def __init__(self, kanban_manager: KanbanManager):
        self.kanban_manager = kanban_manager
        self.pomodoro = PomodoroInverse()
        
        # Callbacks para actualizar la Vista de forma reactiva (SOLID - DIP)
        self._on_kanban_changed: Optional[Callable[[], None]] = None
        self._on_pomodoro_tick: Optional[Callable[[str, int], None]] = None

    def register_view_callbacks(self, on_kanban_changed: Callable[[], None], 
                                 on_pomodoro_tick: Callable[[str, int], None]) -> None:
        """Permite a la Vista suscribirse a los cambios del Modelo."""
        self._on_kanban_changed = on_kanban_changed
        self._on_pomodoro_tick = on_pomodoro_tick

    # --- Operaciones del Tablero Kanban / BuJo ---

    def add_bujo_item(self, title: str, symbol: BuJoSymbol) -> Optional[str]:
        """Crea un nuevo elemento en el tablero usando un identificador único."""
        if not title.strip():
            return "El título no puede estar vacío."
        
        try:
            task_id = str(uuid.uuid4())
            self.kanban_manager.create_bujo_item(task_id, title, symbol)
            self._notify_kanban_change()
            return None  # Indica éxito
        except ValueError as e:
            return str(e)  # Retorna el mensaje de error de la regla de negocio (ej: doble AC)

    def move_bujo_item(self, item_id: str, target_column: KanbanColumn) -> None:
        """Mueve un elemento entre columnas (Por Hacer, En Proceso, Hecho)."""
        self.kanban_manager.move_task(item_id, target_column)
        self._notify_kanban_change()

    def toggle_item_priority(self, item_id: str) -> None:
        """Alterna el marcador clásico de prioridad (*) en el elemento."""
        self.kanban_manager.toggle_signifier(item_id, "priority")
        self._notify_kanban_change()

    def toggle_item_inspiration(self, item_id: str) -> None:
        """Alterna el marcador clásico de inspiración/idea (!) en el elemento."""
        self.kanban_manager.toggle_signifier(item_id, "inspiration")
        self._notify_kanban_change()

    def get_column_content(self, column: KanbanColumn) -> List[KanbanTask]:
        """Carga perezosa (JIT): Solicita los datos específicos requeridos por la vista."""
        return self.kanban_manager.get_items_by_column(column)

    def archive_completed_tasks(self) -> None:
        """Ordena al mánager archivar las tareas terminadas y refresca la interfaz."""
        self.kanban_manager.archive_done_tasks()
        self._notify_kanban_change()

    # --- Operaciones del Pomodoro Inverso ---

    def start_pomodoro(self) -> None:
        """Inicia o reanuda el temporizador del Pomodoro Inverso."""
        self.pomodoro.is_running = True

    def pause_pomodoro(self) -> None:
        """Pausa el temporizador."""
        self.pomodoro.is_running = False

    def reset_pomodoro(self) -> None:
        """Reinicia el temporizador al estado inicial de arranque (5 minutos)."""
        self.pomodoro = PomodoroInverse()
        self._notify_pomodoro_tick()

    def update_timer(self) -> None:
        """
        Debe ser llamado por la Vista una vez por segundo.
        Actualiza el estado del reloj y notifica los cambios.
        """
        if self.pomodoro.is_running:
            self.pomodoro.tick()
            self._notify_pomodoro_tick()
            
            # Alerta implícita para el cambio de ciclo (fácilmente captable por la UI)
            if self.pomodoro.current_phase == "Terminado":
                self.pause_pomodoro()

    # --- Helpers de Notificación ---

    def _notify_kanban_change(self) -> None:
        if self._on_kanban_changed:
            self._on_kanban_changed()

    def _notify_pomodoro_tick(self) -> None:
        if self._on_pomodoro_tick:
            # Pasa la fase actual (Arranque, Enfoque, Descanso) y los segundos restantes
            self._on_pomodoro_tick(self.pomodoro.current_phase, self.pomodoro.current_time_left)