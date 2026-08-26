# views/desktop_gui.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
from core.entities import KanbanColumn, BuJoSymbol
from views.components.kanban_card import KanbanCard


class DesktopGUI:
    """
    Vista de Escritorio (MVC - Tkinter).
    Renderizado reactivo con soporte Local-First y compatibilidad para redes corporativas.
    """

    VERSION = "1.0.4"
    COPYRIGHT = "© 2026 CRAV - Todos los derechos reservados"

    def __init__(self, controller):
        self.controller = controller
        
        # Configuración de la ventana principal
        self.root = tk.Tk()
        self.root.title("Matriz de Enfoque - Suite de Escritorio")
        self.root.geometry("1120x760")
        self.root.minsize(920, 620)
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"⚠️ Nota de icono: {e}")

        # Paleta de colores optimizada
        self.colors = {
            "bg": "#F4F6F9",
            "card": "#FFFFFF",
            "text": "#2C3E50",
            "primary": "#3498DB",
            "accent_ac": "#E74C3C",  # Rojo para Actividad Clave
            "accent_ae": "#F39C12",  # Naranja para Actividad Evitada
            "accent_d": "#9B59B6",   # Morado para Decisiones
            "break_phase": "#2ECC71" # Verde para el descanso (Feynman)
        }
        
        self.root.configure(bg=self.colors["bg"])
        self.columns_ui = {}
        self.column_canvases = []
        
        self._setup_styles()
        self._build_ui()
        
        # Registrar callbacks reactivos en el controlador
        self.controller.register_view_callbacks(
            on_kanban_changed=self.refresh_kanban,
            on_pomodoro_tick=self.refresh_pomodoro
        )
        
        # Carga inicial y bucle de reloj
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
        self.style.configure("Column.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

    def _build_ui(self):
        # --- CONTENEDOR SUPERIOR: POMODORO INVERSO ---
        pomodoro_frame = ttk.LabelFrame(self.root, text=" ⏱️ Control de Tiempos: Pomodoro Inverso (50/10 + 5) ", padding=12)
        pomodoro_frame.pack(fill="x", padx=18, pady=(12, 6))
        
        self.lbl_phase = ttk.Label(pomodoro_frame, text="Fase: Arranque (5 min)", font=("Segoe UI", 11, "italic"))
        self.lbl_phase.pack(side="left", padx=12)
        
        self.lbl_timer = ttk.Label(pomodoro_frame, text="05:00", style="Timer.TLabel")
        self.lbl_timer.pack(side="left", padx=24)
        
        btn_start = ttk.Button(pomodoro_frame, text="▶ Iniciar", command=self.controller.start_pomodoro)
        btn_start.pack(side="left", padx=4)
        
        btn_pause = ttk.Button(pomodoro_frame, text="⏸ Pausar", command=self.controller.pause_pomodoro)
        btn_pause.pack(side="left", padx=4)
        
        btn_reset = ttk.Button(pomodoro_frame, text="🔄 Reiniciar", command=self.controller.reset_pomodoro)
        btn_reset.pack(side="left", padx=4)

        # Botones de la derecha: Métricas y Sincronizar
        btn_sync = tk.Button(
            pomodoro_frame,
            text="🔄 Sincronizar",
            font=("Segoe UI", 9),
            bg="#ECF0F1",
            fg=self.colors["text"],
            bd=1,
            relief="groove",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._handle_manual_sync
        )
        btn_sync.pack(side="right", padx=6)

        btn_metrics = tk.Button(
            pomodoro_frame,
            text="📊 Rendimiento",
            font=("Segoe UI", 9, "bold"),
            bg="#3498DB",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._show_metrics_desktop
        )
        btn_metrics.pack(side="right", padx=6)

        # --- CONTENEDOR INTERMEDIO: CAPTURA RÁPIDA BUJO ---
        capture_frame = ttk.LabelFrame(self.root, text=" 📝 Captura Rápida Bullet Journal ", padding=10)
        capture_frame.pack(fill="x", padx=18, pady=6)
        
        ttk.Label(capture_frame, text="Nueva Entrada:").pack(side="left", padx=5)
        self.ent_task_title = ttk.Entry(capture_frame, font=("Segoe UI", 10), width=32)
        self.ent_task_title.pack(side="left", padx=5, fill="x", expand=True)
        # Soporte para presionar Enter
        self.ent_task_title.bind("<Return>", lambda event: self._add_item_event())
        
        # Dropdown para elegir la nomenclatura BuJo
        ttk.Label(capture_frame, text="Símbolo:").pack(side="left", padx=5)
        self.cmb_symbol = ttk.Combobox(capture_frame, state="readonly", width=28, font=("Segoe UI", 9))

        bujo_traducciones = {
            BuJoSymbol.TASK_PENDING: "•  Tarea Pendiente",
            BuJoSymbol.TASK_COMPLETED: "X  Tarea Realizada",
            BuJoSymbol.TASK_MIGRATED: ">  Tarea Pospuesta",
            BuJoSymbol.SCHEDULED_TASK: "<  Tarea Programada",
            BuJoSymbol.NOTE: "—  Nota o Pensamiento",
            BuJoSymbol.EVENT: "O  Evento / Fecha Límite",
            BuJoSymbol.PRIORITY: "*  Prioridad Alta",
            BuJoSymbol.INSPIRATION: "!  Idea o Inspiración",
            BuJoSymbol.KEY_ACTIVITY: "✓  Actividad Clave (Única)",
            BuJoSymbol.AVOIDED_ACTIVITY: "//  Actividad Evitada",
            BuJoSymbol.DECISION: "D  Decisión Importante"
        }

        self.cmb_symbol["values"] = list(bujo_traducciones.values())
        self.cmb_symbol.current(0)
        self.cmb_symbol.pack(side="left", padx=5)
        
        btn_add = ttk.Button(capture_frame, text="➕ Agregar Tarea (Enter)", command=self._add_item_event)
        btn_add.pack(side="left", padx=8)

        # --- CONTENEDOR INFERIOR: TABLERO KANBAN ---
        kanban_frame = ttk.Frame(self.root)
        kanban_frame.pack(fill="both", expand=True, padx=18, pady=(6, 4))
        
        columns_meta = [
            (KanbanColumn.TO_DO, "📥 POR HACER", 0),
            (KanbanColumn.IN_PROGRESS, "⚡ EN PROCESO", 1),
            (KanbanColumn.DONE, "✅ HECHO / REALIZADO", 2)
        ]
        
        for col_enum, col_title, grid_col in columns_meta:
            frame = ttk.LabelFrame(kanban_frame, text=f"  {col_title}  ", style="Column.TLabelframe", padding=8)
            frame.grid(row=0, column=grid_col, sticky="nsew", padx=6)
            kanban_frame.columnconfigure(grid_col, weight=1)
            
            # Botón de escoba en columna HECHO
            if col_enum == KanbanColumn.DONE:
                btn_archive = tk.Button(
                    frame, 
                    text="🧹 Limpiar Mesa", 
                    font=("Segoe UI", 9, "bold"),
                    bg="#EBF5FB", 
                    fg="#2980B9",
                    bd=1, 
                    relief="groove",
                    cursor="hand2",
                    command=self._handle_archive_desktop
                )
                btn_archive.pack(fill="x", pady=(0, 6))

            # Contenedor con scrollbar adaptativo
            canvas = tk.Canvas(frame, bg=self.colors["card"], highlightthickness=0)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_list = tk.Frame(canvas, background=self.colors["card"])
            
            # Crear ventana de canvas expandible
            window_id = canvas.create_window((0, 0), window=scrollable_list, anchor="nw")
            
            scrollable_list.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )
            
            # Auto-redimensionar el ancho interior al cambiar el tamaño del canvas
            canvas.bind(
                "<Configure>",
                lambda e, c=canvas, w=window_id: c.itemconfig(w, width=e.width)
            )
            
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            self.columns_ui[col_enum] = scrollable_list
            self.column_canvases.append(canvas)
            
        kanban_frame.rowconfigure(0, weight=1)

        # --- BARRA INFERIOR DE ESTADO Y VERSIÓN ---
        footer_frame = tk.Frame(self.root, bg=self.colors["bg"])
        footer_frame.pack(side="bottom", fill="x", padx=18, pady=(2, 6))

        self.lbl_sync_status = tk.Label(
            footer_frame,
            text="🟢 Modo Local-First Activo",
            font=("Segoe UI", 8),
            bg=self.colors["bg"],
            fg="#27AE60"
        )
        self.lbl_sync_status.pack(side="left")

        lbl_version = tk.Label(
            footer_frame,
            text=f"Versión {self.VERSION}   |   {self.COPYRIGHT}",
            font=("Segoe UI", 8),
            bg=self.colors["bg"],
            fg="gray"
        )
        lbl_version.pack(side="right")

    def _add_item_event(self):
        title = self.ent_task_title.get().strip()
        if not title:
            return

        selected_text = self.cmb_symbol.get()
        symbol = BuJoSymbol.TASK_PENDING

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
        """Redibuja de forma limpia e instantánea las tarjetas en cada columna."""
        for col_enum, container_frame in self.columns_ui.items():
            for widget in container_frame.winfo_children():
                widget.destroy()
                
            tasks = self.controller.get_column_content(col_enum)
            for task in tasks:
                card_widget = KanbanCard(container_frame, task, self.controller, self.colors)
                card_widget.pack(fill="x", pady=4, padx=2)

        # Actualizar indicador de conectividad
        online = self.controller.is_online()
        if online:
            self.lbl_sync_status.configure(text="🟢 Sincronizado con la Nube", fg="#27AE60")
        else:
            self.lbl_sync_status.configure(text="🟡 Modo Local (Sin bloqueo en red corporativa)", fg="#D35400")

    def refresh_pomodoro(self, phase, seconds_left):
        """Actualiza los textos y colores del reloj reactivamente."""
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        self.lbl_timer.configure(text=f"{minutes:02d}:{seconds:02d}")
        
        if phase == "Descanso":
            self.lbl_timer.configure(foreground=self.colors["break_phase"])
            self.lbl_phase.configure(
                text="Fase: ¡Descanso Activo Feynman! 🗣️",
                font=("Segoe UI", 10, "bold"),
                foreground="#D35400"
            )
            if minutes == 10 and seconds == 0:
                messagebox.showinfo(
                    "🧠 Cierre Feynman", 
                    "¡Momento de desconectar! Resume lo que avanzaste "
                    "con palabras ultra-simples antes de levantarte."
                )
        elif phase == "Enfoque":
            self.lbl_timer.configure(foreground=self.colors["accent_ac"])
            self.lbl_phase.configure(text="Fase: Enfoque Absoluto 🎯", font=("Segoe UI", 10, "bold"), foreground=self.colors["text"])
        elif phase == "Arranque":
            self.lbl_timer.configure(foreground=self.colors["primary"])
            self.lbl_phase.configure(text="Fase: Arranque / Preparación 🚀", font=("Segoe UI", 10, "normal"), foreground=self.colors["text"])
        else:
            self.lbl_timer.configure(foreground=self.colors["primary"])
            self.lbl_phase.configure(text=f"Fase: {phase}", font=("Segoe UI", 10, "normal"), foreground=self.colors["text"])

    def _start_ui_timer_loop(self):
        """Ciclo asíncrono controlado por Tkinter para actualizar el reloj cada segundo."""
        self.controller.update_timer()
        self.root.after(1000, self._start_ui_timer_loop)

    def _handle_archive_desktop(self):
        """Archiva las tareas en 'Hecho' y muestra confirmación."""
        self.controller.archive_completed_tasks()
        metrics = self.controller.get_local_metrics()
        tot = metrics.get("tareas_completadas", 0)
        ac = metrics.get("actividades_clave_completadas", 0)
        messagebox.showinfo("🧹 Mesa Limpia", f"Mesa despejada con éxito.\nTotal acumulado: {tot} tareas ({ac} Actividades Clave ✓).")

    def _handle_manual_sync(self):
        """Fuerza un intento de sincronización en segundo plano."""
        self.controller.trigger_sync()
        self.lbl_sync_status.configure(text="🔄 Sincronizando en segundo plano...", fg="#2980B9")
        self.root.after(1500, self.refresh_kanban)

    def _show_metrics_desktop(self):
        """Muestra el panel de métricas acumuladas."""
        metrics = self.controller.get_local_metrics()
        tot = metrics.get("tareas_completadas", 0)
        ac = metrics.get("actividades_clave_completadas", 0)
        
        mensaje = (
            f"📈 MÉTRICAS DE RENDIMIENTO ACUMULADAS:\n\n"
            f"• Histórico Total: {tot} tareas finalizadas.\n"
            f"• Actividades Clave (✓): {ac} completadas con éxito.\n\n"
            f"💡 Este panel es efímero. Al limpiar la mesa se enfoca en "
            f"refrescar tu perspectiva sin sobrecarga visual."
        )
        messagebox.showinfo("Enfoque y Rendimiento", mensaje)

    def run(self):
        self.root.mainloop()