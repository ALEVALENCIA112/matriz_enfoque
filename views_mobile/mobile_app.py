import flet as ft
import asyncio
from core.entities import KanbanColumn, BuJoSymbol


class MatrizEnfoqueMobileApp:

    VERSION = "1.0.4"
    COPYRIGHT = "© 2026 CRAV - Todos los derechos reservados"

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
        self.done_list_view = ft.ListView(expand=True, spacing=10, padding=10)

        # Botón para limpiar mesa en lote desde el celular
        self.btn_clear_done_mobile = ft.ElevatedButton(
            content=ft.Text("🧹 Limpiar Mesa", color="white"),
            icon=ft.Icons.CLEANING_SERVICES,
            bgcolor="#E74C3C",
            on_click=self._handle_clear_mesa_mobile
        )

        # Empaquetamos el botón arriba y las tarjetas abajo
        self.done_list = ft.Column(
            expand=True,
            controls=[
                ft.Container(content=self.btn_clear_done_mobile, padding=ft.Padding(top=10, left=10, right=10, bottom=0)),
                self.done_list_view
            ]
        )

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
                ft.dropdown.Option(BuJoSymbol.SCHEDULED_TASK.value, "< Programada"),
                ft.dropdown.Option(BuJoSymbol.TASK_MIGRATED.value, "> Migrada"),
                ft.dropdown.Option(BuJoSymbol.TASK_COMPLETED.value, "X Hecho"),
                ft.dropdown.Option(BuJoSymbol.PRIORITY.value, "* Prioridad Alta"),
                ft.dropdown.Option(BuJoSymbol.INSPIRATION.value, "! Inspiración / Idea"),
                # Extensiones Neurodivergentes
                ft.dropdown.Option(BuJoSymbol.KEY_ACTIVITY.value, "✓ Clave"),
                ft.dropdown.Option(BuJoSymbol.AVOIDED_ACTIVITY.value, "// Evitado"),
                ft.dropdown.Option(BuJoSymbol.DECISION.value, "D Decisión"),
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

        # Construir y montar la UI físicamente en la página
        self.build_ui()

    def build_ui(self):
        """Dibuja de forma nativa los componentes móviles en pantalla."""
        self.app_bar = ft.AppBar(
            title=ft.Text("🎯 Matriz de Enfoque", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=self.colors["primary"],
            center_title=True,
            # 📊 INTEGRACIÓN DEL PUNTO 3: Botón de analíticas corregido
            actions=[
                ft.IconButton(
                    icon=ft.Icons.BAR_CHART, # <-- CAMBIADO AQUÍ (Universal y seguro)
                    icon_color=ft.Colors.WHITE,
                    tooltip="Ver Rendimiento Semanal",
                    on_click=lambda _: self._show_weekly_dashboard_mobile()
                )
            ]
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
                self.column_container,
                # --- BARRA DE CRÉDITOS Y VERSIÓN GLOBAL MÓVIL ---
                ft.Container(
                    content=ft.Text(
                        value=f"Versión {self.VERSION}  •  {self.COPYRIGHT}",
                        size=10,
                        color=ft.Colors.GREY_500,
                        weight=ft.FontWeight.W_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=ft.Padding(left=10, top=4, right=10, bottom=4)
                )
            ], expand=True)
        )
        
        self.refresh_ui()

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.column_container.content = self.todo_list
        elif idx == 1:
            self.column_container.content = self.progress_list
        elif idx == 2:
            self.column_container.content = self.done_list
        self.page.update()

    def _add_task_from_mobile(self, e):
        title = self.txt_new_task.value.strip()
        if not title:
            return
        
        try:
            chosen_sym = BuJoSymbol(self.dropdown_symbol.value)
            self.controller.add_bujo_item(title, chosen_sym)
            self.txt_new_task.value = ""
            self.page.update()
        except ValueError as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(str(ex)), bgcolor="#E74C3C")
            self.page.snack_bar.open = True
            self.page.update()

    async def _mobile_clock_loop(self):
        """Bucle asíncrono no bloqueante coordinado con el renderizador de Flet."""
        while self.clock_running:
            self.controller.update_timer()
            await asyncio.sleep(1)

    def refresh_ui(self):
        # 1. Vaciado absoluto de los buffers de listas de Flet
        self.todo_list.controls.clear()
        self.progress_list.controls.clear()
        self.done_list_view.controls.clear()

        # 2. Re-inyección limpia desde el controlador compartido
        for task in self.controller.get_column_content(KanbanColumn.TO_DO):
            self.todo_list.controls.append(self._render_task_item(task))
            
        for task in self.controller.get_column_content(KanbanColumn.IN_PROGRESS):
            self.progress_list.controls.append(self._render_task_item(task))
            
        for task in self.controller.get_column_content(KanbanColumn.DONE):
            self.done_list_view.controls.append(self._render_task_item(task))

        # 3. Forzar actualización del árbol de componentes en la pantalla
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
            self.lbl_pomo_phase.value = "Fase: ¡Descanso! (Aplica Cierre Feynman 🗣️)"
        elif phase == "Enfoque":
            self.lbl_pomo_timer.color = self.colors["accent_ac"]
        else:
            self.lbl_pomo_timer.color = self.colors["primary"]
            
        try:
            self.page.update()
        except Exception:
            pass

    def _render_task_item(self, task):
        """Genera dinámicamente las tarjetas adaptativas en Flet Móvil."""
        # Configuración visual adaptativa de la Actividad Clave
        is_key = (task.symbol == BuJoSymbol.KEY_ACTIVITY)
        bg_card = "#FFF5F5" if is_key else self.colors["card"]
        border_side = ft.BorderSide(2, self.colors["accent_ac"]) if is_key else None

        # Construcción de strings de estado
        extra_badges = ""
        if task.is_starred: extra_badges += " ⭐"
        if task.is_inspired: extra_badges += " 💡"

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            f"{task.symbol.value} {task.title}{extra_badges}", 
                            weight=ft.FontWeight.BOLD if is_key else ft.FontWeight.NORMAL,
                            color=self.colors["accent_ac"] if is_key else "black",
                            expand=True
                        )
                    ]),
                    ft.Row([
                        # Botones de Modificadores Contextuales
                        # Botón de Estrella (Prioridad)
                        ft.IconButton(
                            icon=ft.Icons.STAR if task.is_starred else ft.Icons.STAR_BORDER,
                            icon_color="amber" if task.is_starred else "grey",
                            icon_size=18,
                            tooltip="Prioridad",
                            on_click=lambda e, tid=task.id: self.controller.toggle_item_priority(tid)
                        ),
                        # Botón de Idea (Inspiración)
                        ft.IconButton(
                            icon=ft.Icons.LIGHTBULB if task.is_inspired else ft.Icons.LIGHTBULB_OUTLINE,
                            icon_color="orange" if task.is_inspired else "grey",
                            icon_size=18,
                            tooltip="Inspiración",
                            on_click=lambda e, tid=task.id: self.controller.toggle_item_inspiration(tid)
                        ),
                        
                        # 🗑️ LLAMADA SEGURA AL MÉTODO DE BORRADO INDIVIDUAL
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            icon_size=18,
                            tooltip="Eliminar tarea",
                            on_click=lambda _, tid=task.id: self._handle_delete_task_mobile(tid)
                        ),
                                                                     
                        ft.VerticalDivider(),
                        # Flechas de navegación espacial
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK, 
                            icon_size=16, 
                            disabled=(task.column == KanbanColumn.TO_DO),
                            on_click=lambda _: self._move_task_left(task)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARROW_FORWARD, 
                            icon_size=16, 
                            disabled=(task.column == KanbanColumn.DONE),
                            on_click=lambda _: self._move_task_right(task)
                        ),
                    ], alignment=ft.MainAxisAlignment.END, spacing=0)
                ]),
                padding=10,
                bgcolor=bg_card,
                border=ft.border.all(color=self.colors["accent_ac"], width=1) if is_key else None,
                border_radius=8
            )
        )

    def _toggle_priority(self, tid):
        self.controller.toggle_item_priority(tid)

    def _toggle_inspiration(self, tid):
        self.controller.toggle_item_inspiration(tid)

    def _move_task_left(self, task):
        prev_col = KanbanColumn.TO_DO if task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(task.id, prev_col)
        self.refresh_ui()

    def _move_task_right(self, task):
        next_col = KanbanColumn.DONE if task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(task.id, next_col)
        self.refresh_ui()

    def _handle_delete_task_mobile(self, task_id: str):
        """Elimina la tarea en el repositorio local y fuerza el redibujado instantáneo de Flet."""
        try:
            self.controller.delete_task(task_id)
            self.refresh_ui()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("🗑️ Tarea eliminada correctamente."),
                bgcolor="#34495E",
                duration=2000
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"⚠️ Error al borrar: {str(ex)}"), 
                bgcolor="red"
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _handle_clear_mesa_mobile(self, e):
        """Manejador de evento móvil para vaciar 'Hecho' y disparar el chispazo analítico."""
        try:
            self.controller.archive_completed_tasks() 
            
            metrics = self.controller.get_local_metrics()
            tot = metrics.get("tareas_completadas", 0)
            ac = metrics.get("actividades_clave_completadas", 0)
            
            mensaje = f"¡Mesa limpia! Total histórico: {tot} completadas (✓ {ac} Actividades Clave)."
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(mensaje, color="white"),
                duration=4000,
                bgcolor="#2ECC71"
            )
            self.page.snack_bar.open = True
            
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"⚠️ Error al limpiar: {str(ex)}"), bgcolor="red")
            self.page.snack_bar.open = True

    # 📊 MÓDULO DEL PUNTO 3: Dashboard Analítico Semanal Efímero
    def _show_weekly_dashboard_mobile(self):
        """Despliega un diálogo flotante efímero consultando de forma limpia al controlador."""
        try:
            # Consumimos de forma segura el diccionario de métricas crudas desde la lógica de negocio
            metrics = self.controller.get_local_metrics()
            
            # Mapeamos con total correspondencia con los campos usados en _handle_clear_mesa_mobile
            tot = metrics.get("tareas_completadas", 0)
            ac = metrics.get("actividades_clave_completadas", 0)
            
            # Puedes usar contadores de tareas pendientes si los tienes mapeados, o inferirlos de los controles activos
            dashboard_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color="amber"),
                    ft.Text("Enfoque Semanal", size=18, weight=ft.FontWeight.BOLD)
                ], spacing=10),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Métricas de rendimiento acumuladas:", size=13, color="grey_600"),
                        ft.Divider(),
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color="green_400", size=20),
                            ft.Text("Histórico Total: ", weight=ft.FontWeight.BOLD),
                            ft.Text(f"{tot}", size=15, weight=ft.FontWeight.BOLD, color="green")
                        ]),
                        ft.Row([
                            ft.Icon(ft.Icons.GPP_GOOD, color=self.colors["accent_ac"], size=20),
                            ft.Text("Actividades Clave ✓: ", weight=ft.FontWeight.BOLD),
                            ft.Text(f"{ac}", size=15, weight=ft.FontWeight.BOLD, color=self.colors["accent_ac"])
                        ]),
                        ft.Divider(),
                        ft.Text(
                            "💡 Este panel es efímero. Al limpiar la mesa se enfoca en refrescar tu perspectiva sin sobrecarga visual.",
                            size=11,
                            italic=True,
                            color="grey_500"
                        )
                    ], tight=True, spacing=12),
                    width=280,
                    padding=5
                ),
                actions=[
                    ft.TextButton("Entendido", on_click=lambda e: self.page.close(dashboard_dialog))
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            self.page.open(dashboard_dialog)
            
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"⚠️ No se pudieron cargar las métricas: {str(ex)}"),
                bgcolor="red"
            )
            self.page.snack_bar.open = True
            self.page.update()