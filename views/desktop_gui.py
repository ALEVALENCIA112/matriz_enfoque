# views/desktop_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
from core.entities import KanbanColumn, BuJoSymbol
# Importación del nuevo componente modularizado
from views.components.kanban_card import KanbanCard


class DesktopGUI:
    """
    La Vista (MVC) de la aplicación.
    Se encarga exclusivamente del renderizado visual y de capturar los eventos
    físicos del usuario para enviarlos al Controlador.
    """

    def __init__(self, controller):
        self.controller = controller
        
        # Configuración de la ventana principal
        self.root = tk.Tk()
        self.root.title("Matriz de Enfoque Elástico - TDAH Kinestésico")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        
        # Paleta de colores sutiles para evitar la sobreestimulación visual
        self.colors = {
            "bg": "#F4F6F9",
            "card": "#FFFFFF",
            "text": "#2C3E50",
            "primary": "#3498DB",
            "accent_ac": "#E74C3C",  # Rojo neón/chillón para Actividad Clave
            "accent_ae": "#F39C12",  # Naranja para Actividad Evitada
            "accent_d": "#9B59B6",   # Morado para Decisiones
            "break_phase": "#2ECC71" # Verde para el descanso (Feynman)
        }
        
        self.root.configure(bg=self.colors["bg"])
        self._setup_styles()
        self._build_ui()
        
        # Registrar esta vista en el controlador para recibir actualizaciones reactivas
        self.controller.register_view_callbacks(
            on_kanban_changed=self.refresh_kanban,
            on_pomodoro_tick=self.refresh_pomodoro
        )
        
        # Inicializar datos en la pantalla
        self.refresh_kanban()
        self._start_ui_timer_loop()

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["text"])
        self.style.configure("TLabel", font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Timer.TLabel", font=("Segoe UI", 36, "bold"), foreground=self.colors["primary"])
        self.style.configure("Column.TLabelframe", background=self.colors["card"])
        self.style.configure("Column.TLabelframe.Label", font=("Segoe UI", 12, "bold"))

    def _build_ui(self):
        # --- CONTENEDOR SUPERIOR: POMODORO INVERSO & ENFOQUE ---
        pomodoro_frame = ttk.LabelFrame(self.root, text=" ⏱️ Control de Tiempos: Pomodoro Inverso (50/10 + 5) ", padding=15)
        pomodoro_frame.pack(fill="x", padx=20, pady=15)
        
        self.lbl_phase = ttk.Label(pomodoro_frame, text="Fase: Inactivo", font=("Segoe UI", 12, "italic"))
        self.lbl_phase.pack(side="left", padx=15)
        
        self.lbl_timer = ttk.Label(pomodoro_frame, text="05:00", style="Timer.TLabel")
        self.lbl_timer.pack(side="left", padx=30)
        
        btn_start = ttk.Button(pomodoro_frame, text="▶ Arrancar (5 min)", command=self.controller.start_pomodoro)
        btn_start.pack(side="left", padx=5)
        
        btn_pause = ttk.Button(pomodoro_frame, text="⏸ Pausar", command=self.controller.pause_pomodoro)
        btn_pause.pack(side="left", padx=5)
        
        btn_reset = ttk.Button(pomodoro_frame, text="🔄 Reiniciar", command=self.controller.reset_pomodoro)
        btn_reset.pack(side="left", padx=5)

        # --- CONTENEDOR INTERMEDIO: CAPTURA RÁPIDA BUJO ---
        capture_frame = ttk.LabelFrame(self.root, text=" 📝 Captura Rápida Bullet Journal ", padding=10)
        capture_frame.pack(fill="x", padx=20, pady=5)
        
        ttk.Label(capture_frame, text="Nueva Entrada:").pack(side="left", padx=5)
        self.ent_task_title = ttk.Entry(capture_frame, font=("Segoe UI", 11), width=30)
        self.ent_task_title.pack(side="left", padx=5, fill="x", expand=True)
        
        # Dropdown para elegir la nomenclatura exacta
        ttk.Label(capture_frame, text="Símbolo:").pack(side="left", padx=5)
        self.cmb_symbol = ttk.Combobox(capture_frame, state="readonly", width=30, font=("Segoe UI", 10))

        # Mapeo manual y amigable para el cerebro en Español de Ecuador
        bujo_traducciones = {
            BuJoSymbol.TASK_PENDING: "•  Tarea Pendiente",
            BuJoSymbol.TASK_COMPLETED: "X  Tarea Realizada",
            BuJoSymbol.TASK_MIGRATED: ">  Tarea Pospuesta (siguiente día)",
            BuJoSymbol.SCHEDULED_TASK: "<  Tarea Programada (Calendario)",
            BuJoSymbol.NOTE: "—  Nota o Pensamiento",
            BuJoSymbol.EVENT: "O  Evento / Fecha Límite",
            BuJoSymbol.PRIORITY: "*  Prioridad Alta",
            BuJoSymbol.INSPIRATION: "!  Idea o Inspiración",
            BuJoSymbol.KEY_ACTIVITY: "✓  Actividad Clave (Única)",
            BuJoSymbol.AVOIDED_ACTIVITY: "//  Actividad Evitada",
            BuJoSymbol.DECISION: "D  Decisión Importante"
        }

        self.cmb_symbol["values"] = list(bujo_traducciones.values())
        self.cmb_symbol.current(0)  # Por defecto el punto '•' Selecciona por defecto 'Tarea Pendiente'
        self.cmb_symbol.pack(side="left", padx=5)
        
        btn_add = ttk.Button(capture_frame, text="➕ Agregar Papel", command=self._add_item_event)
        btn_add.pack(side="left", padx=10)

        # --- CONTENEDOR INFERIOR: TABLERO KANBAN DE 3 COLUMNAS ---
        kanban_frame = ttk.Frame(self.root)
        kanban_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        self.columns_ui = {}
        columns_meta = [
            (KanbanColumn.TO_DO, "📥 POR HACER", 0),
            (KanbanColumn.IN_PROGRESS, "⚡ EN PROCESO", 1),
            (KanbanColumn.DONE, "✅ HECHO / REALIZADO", 2)
        ]
        
        for col_enum, col_title, grid_col in columns_meta:
            frame = ttk.LabelFrame(kanban_frame, text=f"  {col_title}  ", style="Column.TLabelframe", padding=10)
            frame.grid(row=0, column=grid_col, sticky="nsew", padx=8)
            kanban_frame.columnconfigure(grid_col, weight=1)
            
            # NUEVO: Si es la columna de HECHO (col_col == 2), agregamos el botón de escoba 🧹
            if grid_col == 2:
                btn_archive = tk.Button(
                    frame, 
                    text="🧹 Limpiar Mesa", 
                    font=("Segoe UI", 9, "bold"),
                    bg=self.colors["bg"], 
                    fg=self.colors["text"],
                    bd=1, 
                    relief="groove",
                    command=self.controller.archive_completed_tasks
                )
                # Lo posicionamos arriba antes del canvas de las tareas
                btn_archive.pack(fill="x", pady=(0, 5))

            # Contenedor con scrollbar interno para listas largas de tareas
            canvas = tk.Canvas(frame, bg=self.colors["card"], highlightthickness=0)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_list = tk.Frame(canvas, background=self.colors["card"])
            
            scrollable_list.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            canvas.create_window((0, 0), window=scrollable_list, anchor="nw", width=280)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Guardamos la referencia para redibujar el contenido dinámicamente
            self.columns_ui[col_enum] = scrollable_list
            
        kanban_frame.rowconfigure(0, weight=1)

    def _add_item_event(self):
        title = self.ent_task_title.get()
        selected_text = self.cmb_symbol.get()

        # Encontrar el símbolo correspondiente al texto seleccionado
        symbol = BuJoSymbol.TASK_PENDING  # Por defecto

        for s in BuJoSymbol:
            if selected_text.startswith(s.value):
                symbol = s
                break
        
        error_msg = self.controller.add_bujo_item(title, symbol)
        if error_msg:
            messagebox.showwarning("Regla del Sistema", error_msg)
        else:
            self.ent_task_title.delete(0, tk.END)

    def refresh_kanban(self):
        """Redibuja de forma limpia (JIT) las tareas en cada columna cuando hay cambios."""
        for col_enum, container_frame in self.columns_ui.items():
            # Limpiar elementos previos en el Frame de la interfaz
            for widget in container_frame.winfo_children():
                widget.destroy()
                
            # Obtener las tareas actualizadas desde el controlador
            tasks = self.controller.get_column_content(col_enum)
            
            for task in tasks:
                # INSTANCIACIÓN MODULAR: Delegamos la tarjeta a su propia clase
                card_widget = KanbanCard(container_frame, task, self.controller, self.colors)
                card_widget.pack(fill="x", pady=6, padx=4)

    def refresh_pomodoro(self, phase, seconds_left):
        """Actualiza los textos del reloj de forma reactiva."""
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        self.lbl_timer.configure(text=f"{minutes:02d}:{seconds:02d}")
        self.lbl_phase.configure(text=f"Fase: {phase}")
        
        # Cambiar el color de fondo para alertar visualmente la transición de estados sin sonar alarmas estresantes
        if phase == "Descanso":
            self.lbl_timer.configure(foreground=self.colors["break_phase"])
            # Recordatorio implícito en pantalla de tu técnica para el descanso
            self.lbl_phase.configure(text="Fase: ¡Descanso! (Aplica Cierre Feynman 🗣️)")
        elif phase == "Enfoque":
            self.lbl_timer.configure(foreground=self.colors["accent_ac"])
        else:
            self.lbl_timer.configure(foreground=self.colors["primary"])

    def _start_ui_timer_loop(self):
        """Ciclo asíncrono controlado por el loop de tkinter para actualizar el reloj cada segundo."""
        self.controller.update_timer()
        self.root.after(1000, self._start_ui_timer_loop)

    def run(self):
        self.root.mainloop()
        