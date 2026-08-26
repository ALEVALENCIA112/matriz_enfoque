# views/components/kanban_card.py
import tkinter as tk
from core.entities import KanbanColumn, BuJoSymbol


class KanbanCard(tk.Frame):
    """
    Componente visual modularizado (SOLID - SRP) que representa un Post-it en el tablero de escritorio.
    Centraliza el estilo, los colores neurodivergentes y los eventos kinestésicos de interacción.
    """

    def __init__(self, parent, task, controller, colors):
        self.task = task
        self.controller = controller
        self.colors = colors

        # Determinar color de fondo según el tipo de actividad
        is_key_activity = (self.task.symbol == BuJoSymbol.KEY_ACTIVITY)
        self.card_bg = "#FFF5F5" if is_key_activity else colors.get("card", "#FFFFFF")
        bd_width = 2 if is_key_activity else 1
        relief_style = "ridge" if is_key_activity else "solid"

        # Inicializamos el Frame contenedor
        super().__init__(
            parent, 
            bg=self.card_bg, 
            bd=bd_width, 
            relief=relief_style, 
            padx=8, 
            pady=8
        )
        
        self._render_content()

    def _render_content(self):
        """Dibuja el contenido de la tarjeta con estilo visual limpio."""
        # 1. Definición dinámica de colores y tipografía según el símbolo BuJo
        lbl_color = self.colors["text"]
        font_weight = "normal"
        
        if self.task.symbol == BuJoSymbol.KEY_ACTIVITY:
            lbl_color = self.colors["accent_ac"]
            font_weight = "bold"
        elif self.task.symbol == BuJoSymbol.AVOIDED_ACTIVITY:
            lbl_color = self.colors["accent_ae"]
            font_weight = "bold"
        elif self.task.symbol == BuJoSymbol.DECISION:
            lbl_color = self.colors["accent_d"]
            font_weight = "bold"
        elif self.task.symbol == BuJoSymbol.SCHEDULED_TASK:
            lbl_color = "#2980B9"
            font_weight = "normal"

        # 2. Configuración de los significadores contextuales (* y !)
        prefix = f" {self.task.symbol.value} "
        if getattr(self.task, 'is_starred', False): 
            prefix = "⭐ " + prefix
        if getattr(self.task, 'is_inspired', False): 
            prefix = "💡 " + prefix
        
        # 3. Label del Texto de la Tarea
        lbl_title = tk.Label(
            self, 
            text=f"{prefix}{self.task.title}", 
            fg=lbl_color, 
            bg=self.card_bg,
            font=("Segoe UI", 10, font_weight), 
            wraplength=260, 
            justify="left"
        )
        lbl_title.pack(anchor="w", fill="x")
        
        # 4. Panel inferior de botones de acción
        btn_frame = tk.Frame(self, bg=self.card_bg)
        btn_frame.pack(anchor="e", fill="x", pady=(4, 0))

        # Botón de borrado
        btn_del = tk.Button(
            btn_frame, 
            text="🗑️", 
            font=("Segoe UI", 8), 
            bd=0, 
            bg=self.card_bg, 
            fg="#E74C3C",
            activebackground=self.card_bg,
            cursor="hand2",
            command=lambda: self.controller.delete_bujo_item(self.task.id)
        )
        btn_del.pack(side="left", padx=2)
        
        # Conmutadores de significadores (* / !)
        star_color = "#F39C12" if getattr(self.task, 'is_starred', False) else "#BDC3C7"
        btn_star = tk.Button(
            btn_frame, 
            text="⭐", 
            font=("Segoe UI", 8), 
            bd=0, 
            bg=self.card_bg,
            fg=star_color,
            activebackground=self.card_bg,
            cursor="hand2",
            command=lambda: self.controller.toggle_item_priority(self.task.id)
        )
        btn_star.pack(side="left", padx=2)
                  
        bulb_color = "#E67E22" if getattr(self.task, 'is_inspired', False) else "#BDC3C7"
        btn_bulb = tk.Button(
            btn_frame, 
            text="💡", 
            font=("Segoe UI", 8), 
            bd=0, 
            bg=self.card_bg,
            fg=bulb_color,
            activebackground=self.card_bg,
            cursor="hand2",
            command=lambda: self.controller.toggle_item_inspiration(self.task.id)
        )
        btn_bulb.pack(side="left", padx=2)

        # Flechas de navegación espacial en el Kanban
        if self.task.column != KanbanColumn.TO_DO:
            btn_left = tk.Button(
                btn_frame, 
                text="◀", 
                font=("Segoe UI", 8, "bold"), 
                bd=1,
                relief="groove",
                bg=self.card_bg,
                cursor="hand2",
                command=self._move_left
            )
            btn_left.pack(side="right", padx=2)
                      
        if self.task.column != KanbanColumn.DONE:
            btn_right = tk.Button(
                btn_frame, 
                text="▶", 
                font=("Segoe UI", 8, "bold"), 
                bd=1,
                relief="groove",
                bg=self.card_bg,
                cursor="hand2",
                command=self._move_right
            )
            btn_right.pack(side="right", padx=2)

    def _move_left(self):
        prev_col = KanbanColumn.TO_DO if self.task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(self.task.id, prev_col)

    def _move_right(self):
        next_col = KanbanColumn.IN_PROGRESS if self.task.column == KanbanColumn.TO_DO else KanbanColumn.DONE
        self.controller.move_bujo_item(self.task.id, next_col)