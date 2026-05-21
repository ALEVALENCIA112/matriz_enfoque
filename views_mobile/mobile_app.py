# views_mobile/mobile_app.py
import flet as ft
import asyncio
from core.entities import KanbanColumn, BuJoSymbol


class MatrizEnfoqueMobileApp:
    def __init__(self, page: ft.Page, controller):
        self.page = page
        self.controller = controller
        
        self.colors = {
            "primary": "#3498DB",
            "bg": "#F4F6F9",
            "card": "#FFFFFF",
            "accent_ac": "#E74C3C",  
            "accent_ae": "#F39C12",  
            "accent_d": "#9B59B6",   
            "scheduled": "#3498DB"   
        }

        self.todo_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.progress_list = ft.ListView(expand=True, spacing=10, padding=10)
        self.done_list = ft.ListView(expand=True, spacing=10, padding=10)

        # Campo de entrada de texto
        self.txt_new_task = ft.TextField(
            label="Nueva Entrada Rápida...",
            expand=True,
            border_color=self.colors["primary"],
            text_size=14
        )

        # 🎯 DROPDOWN INTEGRAL CON TODOS LOS SÍMBOLOS DISPONIBLES EN DOMINIO
        self.dropdown_symbol = ft.Dropdown(
            width=100,
            hint_text="Tipo",
            border_color=self.colors["primary"],
            options=[
                # Clásicos
                ft.dropdown.Option(BuJoSymbol.TASK_PENDING.value, "• Tarea"),
                ft.dropdown.Option(BuJoSymbol.NOTE.value, "— Nota"),
                ft.dropdown.Option(BuJoSymbol.EVENT.value, "○ Evento"),
                ft.dropdown.Option(BuJoSymbol.SCHEDULED_TASK.value, "< Prog"),
                ft.dropdown.Option(BuJoSymbol.TASK_MIGRATED.value, "> Migr"),
                ft.dropdown.Option(BuJoSymbol.TASK_COMPLETED.value, "X Hech"),
                # Extensiones Neurodivergentes
                ft.dropdown.Option(BuJoSymbol.KEY_ACTIVITY.value, "✓ Clave"),
                ft.dropdown.Option(BuJoSymbol.AVOIDED_ACTIVITY.value, "// Evit"),
                ft.dropdown.Option(BuJoSymbol.DECISION.value, "D Decis"),
            ],
            value=BuJoSymbol.TASK_PENDING.value  
        )

        # Registro de Callbacks reactivos
        self.controller.register_view_callbacks(
            on_kanban_changed=self.refresh_ui,
            on_pomodoro_tick=self.refresh_pomodoro
        )

        # ⏰ HILO DE FONDO CONTROLADO PARA EL RELOJ POMODORO
        self.clock_running = True
        self.page.run_task(self._mobile_clock_loop)

    def build_ui(self):
        """Dibuja de forma nativa los componentes móviles en pantalla."""
        self.app_bar = ft.AppBar(
            title=ft.Text("🎯 Matriz de Enfoque", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=self.colors["primary"],
            center_title=True,
        )
        self.page.appbar = self.app_bar

        # --- SECCIÓN POMODORO ---
        self.lbl_pomo_phase = ft.Text("Fase: Arranque", italic=True, size=14)
        
        mins = self.controller.pomodoro.current_time_left // 60
        secs = self.controller.pomodoro.current_time_left % 60
        self.lbl_pomo_timer = ft.Text(f"{mins:02d}:{secs:02d}", size=32, weight=ft.FontWeight.BOLD, color=self.colors["primary"])

        pomodoro_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([self.lbl_pomo_phase, self.lbl_pomo_timer], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.PLAY_ARROW, on_click=lambda _: self.controller.start_pomodoro()),
                        ft.IconButton(icon=ft.Icons.PAUSE, on_click=lambda _: self.controller.pause_pomodoro()),
                        ft.IconButton(icon=ft.Icons.REFRESH, on_click=lambda _: self.controller.reset_pomodoro()),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ]),
                padding=15
            ),
            margin=10
        )

        # --- SECCIÓN ADICIÓN ---
        input_row = ft.Container(
            content=ft.Row([
                self.dropdown_symbol,
                self.txt_new_task,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE,
                    icon_color=self.colors["primary"],
                    icon_size=36,
                    on_click=self._add_task_from_mobile
                )
            ]),
            padding=10
        )

        # Layout dinámico
        self.column_container = ft.Container(content=self.todo_list, expand=True)

        # Barra inferior de pestañas
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.INBOX, label="Por Hacer"),
                ft.NavigationBarDestination(icon=ft.Icons.FLASH_ON, label="En Proceso"),
                ft.NavigationBarDestination(icon=ft.Icons.CHECK_CIRCLE, label="Hecho"),
            ]
        )

        self.page.add(
            ft.Column([
                pomodoro_card,
                input_row,          
                self.column_container  
            ], expand=True)
        )
        
        self.refresh_ui()

    async def _mobile_clock_loop(self):
        """Bucle asíncrono no bloqueante coordinado con el renderizador de Flet."""
        while True:
            try:
                # Ejecuta el avance síncrono del modelo
                self.controller.update_timer()
                # Pausa la corrutina por 1 segundo de manera asíncrona sin congelar la UI
                await asyncio.sleep(1)
            except Exception:
                pass

    def _add_task_from_mobile(self, e):
        title = self.txt_new_task.value.strip()
        if not title:
            return
        
        # Obtener el Enum puro basándonos en la selección en crudo del string del Dropdown
        selected_symbol_str = self.dropdown_symbol.value
        chosen_symbol = BuJoSymbol(selected_symbol_str)
        
        self.controller.add_bujo_item(title, chosen_symbol)
        self.txt_new_task.value = ""  
        self.page.update()

    def _on_nav_change(self, e):
        index = int(e.data)
        if index == 0:
            self.column_container.content = self.todo_list
        elif index == 1:
            self.column_container.content = self.progress_list
        elif index == 2:
            self.column_container.content = self.done_list
        self.page.update()

    def _render_task_item(self, task):
        text_color = ft.Colors.BLACK
        weight = ft.FontWeight.NORMAL
        
        if task.symbol == BuJoSymbol.KEY_ACTIVITY:
            text_color = self.colors["accent_ac"]
            weight = ft.FontWeight.BOLD
        elif task.symbol == BuJoSymbol.AVOIDED_ACTIVITY:
            text_color = self.colors["accent_ae"]
        elif task.symbol == BuJoSymbol.DECISION:
            text_color = self.colors["accent_d"]
            weight = ft.FontWeight.BOLD
        elif task.symbol == BuJoSymbol.SCHEDULED_TASK:
            text_color = self.colors["scheduled"]

        prefix = f"{task.symbol.value} "
        if task.is_starred: prefix = "⭐ " + prefix
        if task.is_inspired: prefix = "💡 " + prefix

        actions = []
        
        # 🗑️ LLAMADA SEGURA AL MÉTODO DE BORRADO INDIVIDUAL EN EL CONTROLADOR
        actions.append(ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=ft.Colors.RED_400,
            icon_size=18,
            on_click=lambda _: self.controller.delete_bujo_item(task.id)
        ))

        if task.column != KanbanColumn.TO_DO:
            actions.append(ft.IconButton(
                icon=ft.Icons.ARROW_BACK, 
                icon_size=18,
                on_click=lambda _: self.controller.move_bujo_item(task.id, KanbanColumn.TO_DO if task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS)
            ))
        if task.column != KanbanColumn.DONE:
            actions.append(ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD, 
                icon_size=18,
                on_click=lambda _: self.controller.move_bujo_item(task.id, KanbanColumn.IN_PROGRESS if task.column == KanbanColumn.TO_DO else KanbanColumn.DONE)
            ))

        return ft.Container(
            content=ft.Row([
                ft.Text(f"{prefix}{task.title}", color=text_color, weight=weight, expand=True, size=15),
                ft.Row(actions, spacing=0)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=self.colors["card"],
            padding=12,
            border_radius=8,
            border=ft.Border.all(0.5, ft.Colors.BLACK26)  # 💡 CORREGIDO: 'ft.Border.all' con 'B' mayúscula
        )

    def refresh_ui(self):
        self.todo_list.controls.clear()
        self.progress_list.controls.clear()
        self.done_list.controls.clear()

        for task in self.controller.get_column_content(KanbanColumn.TO_DO):
            self.todo_list.controls.append(self._render_task_item(task))
        for task in self.controller.get_column_content(KanbanColumn.IN_PROGRESS):
            self.progress_list.controls.append(self._render_task_item(task))
        for task in self.controller.get_column_content(KanbanColumn.DONE):
            self.done_list.controls.append(self._render_task_item(task))

        try:
            self.page.update()
        except Exception:
            pass

    def refresh_pomodoro(self, phase, seconds_left):
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        self.lbl_pomo_timer.value = f"{minutes:02d}:{seconds:02d}"
        self.lbl_pomo_phase.value = f"Fase: {phase}"
        
        if phase == "Descanso":
            self.lbl_pomo_timer.color = ft.Colors.GREEN
        elif phase == "Enfoque":
            self.lbl_pomo_timer.color = self.colors["accent_ac"]
        else:
            self.lbl_pomo_timer.color = self.colors["primary"]
            
        try:
            self.page.update()
        except Exception:
            pass