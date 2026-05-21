# core/entities.py
from datetime import datetime
from enum import Enum
from typing import Optional


class BuJoSymbol(Enum):
    # --- Nomenclatura Clásica BuJo ---
    TASK_PENDING = "•"         # Tarea pendiente
    TASK_COMPLETED = "X"       # Tarea completada
    TASK_MIGRATED = ">"        # Tarea migrada / pospuesta (al dia siguiente)
    SCHEDULED_TASK = "<"       # Tarea Programada (Futura / Calendario)
    NOTE = "-"                 # Nota / Pensamiento rápido
    EVENT = "O"                # Evento / Fecha límite
    PRIORITY = "*"             # Prioridad (Significador clásico)
    INSPIRATION = "!"          # Inspiración / Idea (Significador clásico)
    
    # --- Tus 3 Extensiones Neurodivergentes ---
    KEY_ACTIVITY = "✓"        # Actividad Clave (Única e importante)
    AVOIDED_ACTIVITY = "//"    # Actividad Evitada (Pospuesta temporalmente)
    DECISION = "D"             # Decisión importante en encrucijada


class KanbanColumn(Enum):
    TO_DO = "Por Hacer"
    IN_PROGRESS = "En Proceso"
    DONE = "Hecho"


class KanbanTask:
    """Representa una tarea dentro de la Matriz de Enfoque."""
    
    def __init__(self, task_id: str, title: str, symbol: BuJoSymbol = BuJoSymbol.TASK_PENDING):
        self.id = task_id
        self.title = title
        self.symbol = symbol  # El símbolo define la naturaleza del elemento BuJo
        self.column = KanbanColumn.TO_DO
        self.created_at = datetime.now()
        self.is_starred = False  # Para soporte del significador de prioridad (*)
        self.is_inspired = False # Para soporte del significador de idea (!)
        
    def move_to(self, target_column: KanbanColumn) -> None:
        """Maneja las transiciones de estado aplicando las reglas de tu sistema."""
        
        # Regla de Transición: Si está en progreso y se devuelve a 'Por Hacer',
        # es una Actividad Evitada (AE). Automáticamente muta su símbolo a '//'
        if self.column == KanbanColumn.IN_PROGRESS and target_column == KanbanColumn.TO_DO:
            self.symbol = BuJoSymbol.AVOIDED_ACTIVITY
            
        # Al completarse, se actualiza el símbolo visual
        if target_column == KanbanColumn.DONE:
            # Si era una Actividad Clave o Decisión, podemos mantener su etiqueta visual 
            # para el historial, pero si era una tarea común, se marca con la clásica 'X'
            if self.symbol in [BuJoSymbol.TASK_PENDING, BuJoSymbol.TASK_MIGRATED]:
                self.symbol = BuJoSymbol.TASK_COMPLETED
                
        self.column = target_column

    def migrate_task(self) -> None:
        """Mapea el comportamiento clásico de posponer/migrar una tarea ('>')."""
        if self.column != KanbanColumn.DONE:
            self.symbol = BuJoSymbol.TASK_MIGRATED

    def __repr__(self) -> str:
        star = "*" if self.is_starred else ""
        insp = "!" if self.is_inspired else ""
        return f"{star}{insp}[{self.symbol.value}] {self.title} -> {self.column.value}"

class PomodoroInverse:
    """Controla el flujo del Pomodoro Inverso (50 min trabajo / 10 min descanso + 5 min arranque)."""
    
    def __init__(self, work_duration: int = 50, break_duration: int = 10, startup_duration: int = 5):
        self.work_duration = work_duration * 60       # Convertido a segundos
        self.break_duration = break_duration * 60     # Convertido a segundos
        self.startup_duration = startup_duration * 60 # Convertido a segundos
        
        self.current_time_left = self.startup_duration
        self.current_phase = "Arranque"  # Fases: Arranque, Enfoque, Descanso, Terminado
        self.is_running = False

    def tick(self) -> None:
        """Decrementa el reloj segundo a segundo (Invocado por el controlador)."""
        if not self.is_running:
            return
            
        if self.current_time_left > 0:
            self.current_time_left -= 1
        else:
            self._transition_to_next_phase()

    def _transition_to_next_phase(self) -> None:
        """Lógica interna de transición de estados del Pomodoro."""
        if self.current_phase == "Arranque":
            self.current_phase = "Enfoque"
            self.current_time_left = self.work_duration
        elif self.current_phase == "Enfoque":
            self.current_phase = "Descanso"  # Momento para el Cierre Feynman
            self.current_time_left = self.break_duration
        elif self.current_phase == "Descanso":
            self.current_phase = "Terminado"
            self.is_running = False