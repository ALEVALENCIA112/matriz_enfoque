# views_mobile/mobile_app.py
import flet as ft
import asyncio
from core.entities import KanbanColumn, BuJoSymbol


def get_center_alignment():
    """Retorna alineación central universal para todas las versiones de Flet."""
    return ft.Alignment(0, 0)


def create_card_border(color: str = "#E74C3C", width: float = 1.5):
    """Genera un borde adaptativo compatible con Flet moderno y clásico."""
    try:
        if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
            return ft.Border.all(width=width, color=color)
        if hasattr(ft, "border") and hasattr(ft.border, "all"):
            return ft.border.all(color=color, width=width)
    except Exception:
        pass
    try:
        return ft.Border(
            top=ft.BorderSide(width, color),
            right=ft.BorderSide(width, color),
            bottom=ft.BorderSide(width, color),
            left=ft.BorderSide(width, color)
        )
    except Exception:
        return None


class MatrizEnfoqueMobileApp:
    """
    Vista Móvil (Flet APK - Android / Multiplataforma).
    Diseño adaptativo táctil con soporte 100% Local-First y tolerancia a desconexión.
    """

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
            "scheduled": "#2980B9"   
        }

        # Contenedores de listas para cada columna
        self.todo_list = ft.ListView(expand=True, spacing=8, padding=10)
        self.progress_list = ft.ListView(expand=True, spacing=8, padding=10)
        self.done_list_view = ft.ListView(expand=True, spacing=8, padding=10)

        # Botón para limpiar mesa en columna Hecho
        self.btn_clear_done_mobile = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CLEANING_SERVICES, size=18, color=ft.Colors.WHITE),
                    ft.Text("Limpiar Mesa", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True
            ),
            bgcolor="#E74C3C",
            on_click=self._handle_clear_mesa_mobile
        )

        self.done_list = ft.Column(
            expand=True,
            controls=[
                ft.Container(
                    content=self.btn_clear_done_mobile, 
                    padding=ft.Padding(top=10, left=12, right=12, bottom=4),
                    alignment=get_center_alignment()
                ),
                self.done_list_view
            ]
        )

        # Campo de entrada de texto con soporte para Enter / Teclado móvil
        self.txt_new_task = ft.TextField(
            hint_text="Nueva tarea / nota rápida...",
            expand=True,
            border_color=self.colors["primary"],
            text_size=13,
            dense=True,
            on_submit=self._add_task_from_mobile
        )

        # Dropdown con la nomenclatura BuJo completa
        self.dropdown_symbol = ft.Dropdown(
            width=115,
            hint_text="Tipo",
            border_color=self.colors["primary"],
            dense=True,
            text_size=12,
            options=[
                ft.dropdown.Option(BuJoSymbol.TASK_PENDING.value, "• Tarea"),
                ft.dropdown.Option(BuJoSymbol.KEY_ACTIVITY.value, "✓ Clave"),
                ft.dropdown.Option(BuJoSymbol.AVOIDED_ACTIVITY.value, "// Evitado"),
                ft.dropdown.Option(BuJoSymbol.DECISION.value, "D Decisión"),
                ft.dropdown.Option(BuJoSymbol.NOTE.value, "— Nota"),
                ft.dropdown.Option(BuJoSymbol.EVENT.value, "○ Evento"),
                ft.dropdown.Option(BuJoSymbol.SCHEDULED_TASK.value, "< Programada"),
                ft.dropdown.Option(BuJoSymbol.TASK_MIGRATED.value, "> Migrada"),
                ft.dropdown.Option(BuJoSymbol.TASK_COMPLETED.value, "X Hecho"),
                ft.dropdown.Option(BuJoSymbol.PRIORITY.value, "* Prioridad"),
                ft.dropdown.Option(BuJoSymbol.INSPIRATION.value, "! Idea"),
            ],
            value=BuJoSymbol.TASK_PENDING.value  
        )

        # Registro de Callbacks reactivos
        self.controller.register_view_callbacks(
            on_kanban_changed=self.refresh_ui,
            on_pomodoro_tick=self.refresh_pomodoro
        )

        # Hilo de fondo del reloj
        self.clock_running = True
        self.page.run_task(self._mobile_clock_loop)

        # Construir UI
        self.build_ui()

    def _show_snackbar(self, message: str, color: str = "#2ECC71"):
        """Muestra un SnackBar compatible con todas las versiones de Flet."""
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE, size=13),
            bgcolor=color,
            duration=3500
        )
        if hasattr(self.page, "open"):
            self.page.open(snack)
        else:
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

    def build_ui(self):
        """Monta los componentes móviles de la interfaz."""
        self.app_bar = ft.AppBar(
            title=ft.Text("🎯 Matriz de Enfoque", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=18),
            bgcolor=self.colors["primary"],
            center_title=True,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.SYNC,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Sincronizar",
                    on_click=lambda _: self._handle_manual_sync_mobile()
                ),
                ft.IconButton(
                    icon=ft.Icons.BAR_CHART,
                    icon_color=ft.Colors.WHITE,
                    tooltip="Rendimiento Semanal",
                    on_click=lambda _: self._show_weekly_dashboard_mobile()
                )
            ]
        )
        self.page.appbar = self.app_bar

        # --- SECCIÓN POMODORO ---
        self.lbl_pomo_phase = ft.Text("Fase: Arranque", italic=True, size=13)
        
        mins = self.controller.pomodoro.current_time_left // 60
        secs = self.controller.pomodoro.current_time_left % 60
        self.lbl_pomo_timer = ft.Text(
            f"{mins:02d}:{secs:02d}", 
            size=28, 
            weight=ft.FontWeight.BOLD, 
            color=self.colors["primary"]
        )

        pomodoro_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([self.lbl_pomo_phase, self.lbl_pomo_timer], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_color=self.colors["primary"], on_click=lambda _: self.controller.start_pomodoro()),
                        ft.IconButton(icon=ft.Icons.PAUSE, icon_color="#E67E22", on_click=lambda _: self.controller.pause_pomodoro()),
                        ft.IconButton(icon=ft.Icons.REFRESH, icon_color="grey", on_click=lambda _: self.controller.reset_pomodoro()),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=15)
                ], spacing=4),
                padding=12
            ),
            margin=ft.Margin(left=10, top=6, right=10, bottom=4)
        )

        # --- SECCIÓN ENTRADA RÁPIDA ---
        input_row = ft.Container(
            content=ft.Row([
                self.dropdown_symbol,
                self.txt_new_task,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE,
                    icon_color=self.colors["primary"],
                    icon_size=32,
                    tooltip="Agregar entrada",
                    on_click=self._add_task_from_mobile
                )
            ], spacing=6),
            padding=ft.Padding(left=10, top=4, right=10, bottom=4)
        )

        # Layout dinámico para navegación de columnas
        self.column_container = ft.Container(content=self.todo_list, expand=True)

        # Barra inferior de pestañas (NavigationBar)
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
                # Pie de versión
                ft.Container(
                    content=ft.Text(
                        value=f"Versión {self.VERSION}  •  {self.COPYRIGHT}",
                        size=9,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=ft.Padding(left=10, top=2, right=10, bottom=4),
                    alignment=get_center_alignment()
                )
            ], expand=True, spacing=2)
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
            chosen_sym = BuJoSymbol.TASK_PENDING
            for s in BuJoSymbol:
                if s.value == self.dropdown_symbol.value:
                    chosen_sym = s
                    break

            error_msg = self.controller.add_bujo_item(title, chosen_sym)
            if error_msg:
                self._show_snackbar(error_msg, color="#E74C3C")
            else:
                self.txt_new_task.value = ""
                self.page.update()
        except Exception as ex:
            self._show_snackbar(str(ex), color="#E74C3C")

    async def _mobile_clock_loop(self):
        """Bucle asíncrono no bloqueante coordinado con Flet."""
        while self.clock_running:
            self.controller.update_timer()
            await asyncio.sleep(1)

    def refresh_ui(self):
        """Redibuja de forma limpia e instantánea las tarjetas en la pantalla móvil."""
        self.todo_list.controls.clear()
        self.progress_list.controls.clear()
        self.done_list_view.controls.clear()

        for task in self.controller.get_column_content(KanbanColumn.TO_DO):
            self.todo_list.controls.append(self._render_task_item(task))
            
        for task in self.controller.get_column_content(KanbanColumn.IN_PROGRESS):
            self.progress_list.controls.append(self._render_task_item(task))
            
        for task in self.controller.get_column_content(KanbanColumn.DONE):
            self.done_list_view.controls.append(self._render_task_item(task))

        try:
            self.page.update()
        except Exception:
            pass

    def refresh_pomodoro(self, phase, seconds_left):
        """Actualiza reactivamente el reloj en el APK."""
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        
        self.lbl_pomo_timer.value = f"{minutes:02d}:{seconds:02d}"
        self.lbl_pomo_phase.value = f"Fase: {phase}"
        
        if phase == "Descanso":
            self.lbl_pomo_timer.color = "#E67E22"
            self.lbl_pomo_phase.value = "Fase: ¡Descanso Feynman! 🗣️"
            self.lbl_pomo_phase.color = "#D35400"
            
            if minutes == 10 and seconds == 0:
                self._show_snackbar(
                    "🧠 Cierre Feynman: Resume lo avanzado con palabras ultra-simples antes de descansar.",
                    color="#D35400"
                )
        elif phase == "Enfoque":
            self.lbl_pomo_timer.color = self.colors["accent_ac"]
            self.lbl_pomo_phase.color = "black"
            self.lbl_pomo_phase.value = "Fase: Enfoque Absoluto 🎯"
        elif phase == "Arranque":
            self.lbl_pomo_timer.color = self.colors["primary"]
            self.lbl_pomo_phase.color = "black"
            self.lbl_pomo_phase.value = "Fase: Arranque / Preparación 🚀"
        else:
            self.lbl_pomo_timer.color = self.colors["primary"]
            self.lbl_pomo_phase.color = "black"

        try:
            self.page.update()
        except Exception:
            pass

    def _render_task_item(self, task):
        """Genera dinámicamente las tarjetas táctiles."""
        is_key = (task.symbol == BuJoSymbol.KEY_ACTIVITY)
        bg_card = "#FFF5F5" if is_key else self.colors["card"]

        extra_badges = ""
        if getattr(task, 'is_starred', False): extra_badges += " ⭐"
        if getattr(task, 'is_inspired', False): extra_badges += " 💡"

        border_val = create_card_border(self.colors["accent_ac"], 1.5) if is_key else None

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            f"{task.symbol.value} {task.title}{extra_badges}", 
                            weight=ft.FontWeight.BOLD if is_key else ft.FontWeight.NORMAL,
                            color=self.colors["accent_ac"] if is_key else ft.Colors.BLACK87,
                            size=14,
                            expand=True
                        )
                    ]),
                    ft.Row([
                        # Estrella (Prioridad)
                        ft.IconButton(
                            icon=ft.Icons.STAR if getattr(task, 'is_starred', False) else ft.Icons.STAR_BORDER,
                            icon_color="amber" if getattr(task, 'is_starred', False) else "grey",
                            icon_size=18,
                            tooltip="Prioridad",
                            on_click=lambda e, tid=task.id: self.controller.toggle_item_priority(tid)
                        ),
                        # Bombillo (Inspiración)
                        ft.IconButton(
                            icon=ft.Icons.LIGHTBULB if getattr(task, 'is_inspired', False) else ft.Icons.LIGHTBULB_OUTLINE,
                            icon_color="orange" if getattr(task, 'is_inspired', False) else "grey",
                            icon_size=18,
                            tooltip="Inspiración",
                            on_click=lambda e, tid=task.id: self.controller.toggle_item_inspiration(tid)
                        ),
                        # Borrar
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            icon_size=18,
                            tooltip="Eliminar",
                            on_click=lambda _, tid=task.id: self._handle_delete_task_mobile(tid)
                        ),
                        ft.Container(width=10),
                        # Flechas de navegación espacial
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK, 
                            icon_size=18, 
                            disabled=(task.column == KanbanColumn.TO_DO),
                            on_click=lambda _, t=task: self._move_task_left(t)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.ARROW_FORWARD, 
                            icon_size=18, 
                            disabled=(task.column == KanbanColumn.DONE),
                            on_click=lambda _, t=task: self._move_task_right(t)
                        ),
                    ], alignment=ft.MainAxisAlignment.END, spacing=0)
                ], spacing=4),
                padding=10,
                bgcolor=bg_card,
                border=border_val,
                border_radius=8
            ),
            margin=ft.Margin(left=4, top=2, right=4, bottom=4)
        )

    def _move_task_left(self, task):
        prev_col = KanbanColumn.TO_DO if task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(task.id, prev_col)

    def _move_task_right(self, task):
        next_col = KanbanColumn.DONE if task.column == KanbanColumn.IN_PROGRESS else KanbanColumn.IN_PROGRESS
        self.controller.move_bujo_item(task.id, next_col)

    def _handle_delete_task_mobile(self, task_id: str):
        try:
            self.controller.delete_bujo_item(task_id)
            self._show_snackbar("🗑️ Tarea eliminada.", color="#34495E")
        except Exception as ex:
            self._show_snackbar(f"⚠️ Error al borrar: {str(ex)}", color="#E74C3C")

    def _handle_clear_mesa_mobile(self, e):
        try:
            self.controller.archive_completed_tasks()
            metrics = self.controller.get_local_metrics()
            tot = metrics.get("tareas_completadas", 0)
            ac = metrics.get("actividades_clave_completadas", 0)
            
            mensaje = f"¡Mesa limpia! Total histórico: {tot} ({ac} Actividades Clave ✓)."
            self._show_snackbar(mensaje, color="#2ECC71")
        except Exception as ex:
            self._show_snackbar(f"⚠️ Error al limpiar: {str(ex)}", color="#E74C3C")

    def _handle_manual_sync_mobile(self):
        self.controller.trigger_sync()
        self._show_snackbar("🔄 Sincronizando con Firebase en segundo plano...", color="#2980B9")

    def _show_weekly_dashboard_mobile(self):
        """Despliega un diálogo con las métricas acumuladas."""
        try:
            metrics = self.controller.get_local_metrics()
            tot = metrics.get("tareas_completadas", 0)
            ac = metrics.get("actividades_clave_completadas", 0)
            
            dashboard_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.AUTO_AWESOME, color="amber"),
                    ft.Text("Enfoque y Métricas", size=17, weight=ft.FontWeight.BOLD)
                ], spacing=8),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Rendimiento acumulado en este dispositivo:", size=12, color=ft.Colors.GREY_700),
                        ft.Divider(),
                        ft.Row([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=18),
                            ft.Text("Histórico Total: ", weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"{tot}", size=14, weight=ft.FontWeight.BOLD, color="green")
                        ]),
                        ft.Row([
                            ft.Icon(ft.Icons.VERIFIED, color=self.colors["accent_ac"], size=18),
                            ft.Text("Actividades Clave ✓: ", weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"{ac}", size=14, weight=ft.FontWeight.BOLD, color=self.colors["accent_ac"])
                        ]),
                        ft.Divider(),
                        ft.Text(
                            "💡 Este panel te ayuda a revisar el progreso sin sobrecarga visual en el tablero.",
                            size=10,
                            italic=True,
                            color=ft.Colors.GREY_600
                        )
                    ], tight=True, spacing=10),
                    width=280,
                    padding=5
                ),
                actions=[
                    ft.TextButton("Cerrar", on_click=lambda e: self._close_dialog_mobile(dashboard_dialog))
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            if hasattr(self.page, "open"):
                self.page.open(dashboard_dialog)
            else:
                self.page.dialog = dashboard_dialog
                dashboard_dialog.open = True
                self.page.update()
            
        except Exception as ex:
            self._show_snackbar(f"⚠️ Error al abrir métricas: {str(ex)}", color="#E74C3C")

    def _close_dialog_mobile(self, dialog):
        if hasattr(self.page, "close"):
            self.page.close(dialog)
        else:
            dialog.open = False
            self.page.update()