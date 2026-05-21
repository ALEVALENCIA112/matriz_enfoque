# views/components/kanban_card.py
import tkinter as tk
from core.entities import KanbanColumn, BuJoSymbol


class KanbanCard(tk.Frame):
    """
    Componente visual aislado (SOLID - SRP) que representa un Post-it en el tablero.
    Centraliza el estilo, los colores neurodivergentes y los eventos de interacción.
    """

    def __init__(self, parent, task, controller, colors):
        # Inicializamos el Frame contenedor con bordes sólidos estilo tarjeta
        super().__init__(parent, bg=colors["bg"], bd=1, relief="solid", padx=8, pady=8)
        self.task = task
        self.controller = controller
        self.colors = colors
        
        self._render_content()

    def _render_content(self):
        """Dibuja el texto del elemento y los botones de acción."""
        # 1. Definición dinámica de colores y grosores según el símbolo BuJo
        lbl_color = self.colors["text"]
        font_weight = "normal"
        
        if self.task.symbol == BuJoSymbol.KEY_ACTIVITY:
            lbl_color = self.colors["accent_ac"]
            font_weight = "bold"
        elif self.task.symbol == BuJoSymbol.AVOIDED_ACTIVITY:
            lbl_color = self.colors["accent_ae"]
        elif self.task.symbol == BuJoSymbol.DECISION:
            lbl_color = self.colors["accent_d"]
            font_weight = "bold"

        elif self.task.symbol == BuJoSymbol.SCHEDULED_TASK:
            lbl_color = "#3498DB"  # Un azul/celeste vivo (combina con la paleta)
            font_weight = "normal" # Mantener grosor normal para no competir con el visto '✓'

        # 2. Configuración de los significadores contextuales clásicos (* y !)
        prefix = f" {self.task.symbol.value} "
        if self.task.is_starred: 
            prefix = "⭐" + prefix
        if self.task.is_inspired: 
            prefix = "💡" + prefix
        
        # 3. Label del Texto de la Tarea
        lbl_title = tk.Label(
            self, 
            text=f"{prefix}{self.task.title}", 
            fg=lbl_color, 
            bg=self.colors["bg"],
            font=("Segoe UI", 10, font_weight), 
            wraplength=240, 
            justify="left"
        )
        lbl_title.pack(anchor="w", fill="x")
        
        # 4. Panel inferior de botones kinestésicos
        btn_frame = tk.Frame(self, bg=self.colors["bg"])
        btn_frame.pack(anchor="e", pady=4)

        # 🗑️ BOTÓN DE BORRADO FÍSICO DIRECTO PARA EL ESCRITORIO
        tk.Button(btn_frame, text="🗑️", font=("Segoe UI", 8), bd=0, bg=self.colors["bg"], fg="#E74C3C",
                  command=lambda: self.controller.delete_bujo_item(self.task.id)).pack(side="left", padx=2)
        
        # Conmutadores rápidos (* / !)
        tk.Button(btn_frame, text="⭐", font=("Segoe UI", 8), bd=0, bg=self.colors["bg"],
                  command=lambda: self.controller.toggle_item_priority(self.task.id)).pack(side="left", padx=2)
                  
        tk.Button(btn_frame, text="💡", font=("Segoe UI", 8), bd=0, bg=self.colors["bg"],
                  command=lambda: self.controller.toggle_item_inspiration(self.task.id)).pack(side="left", padx=2)

        # Flechas de navegación espacial en el Kanban
        if self.task.column != KanbanColumn.TO_DO:
            tk.Button(btn_frame, text="◀", font=("Segoe UI", 8, "bold"), bd=1,
                      command=self._move_left).pack(side="left", padx=2)
                      
        if self.task.column != KanbanColumn.DONE:
            tk.Button(btn_frame, text="▶", font=("Segoe UI", 8, "bold"), bd=1,
                      command=self._move_right).pack(side="left", padx=2)

    def _move_right(self):
        next_col = KanbanColumn.IN_PROGRESS if self.task.column == KanbanColumn.TO_DO else KanbanColumn.DONE
        self.controller.move_bujo_item(self.task.id, next_col)

    def _move_left(self):
        # Si se devuelve de 'En Proceso' a 'Por Hacer', mutará a Actividad Evitada (//) en el dominio
        prev_col = KanbanColumn.TO_DO if self.task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(self.task.id, prev_col)