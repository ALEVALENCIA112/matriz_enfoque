# main_mobile.py
import flet as ft
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from views_mobile.mobile_app import MatrizEnfoqueMobileApp
from infrastructure.cloud_storage import LocalFirstTaskRepository


def main(page: ft.Page):
    # Configuración del lienzo de la app móvil
    page.title = "Matriz de Enfoque - Móvil v1.0.4"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 390   # Proporción estándar de teléfono
    page.window_height = 844
    page.padding = 0

    # URL central de sincronización Firebase
    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"

    # 1. Inyección del Repositorio Local-First Autónomo para el APK
    repository = LocalFirstTaskRepository(
        database_url=FIREBASE_URL,
        user_id="ALEVALENCIA112",
        local_filepath="matriz_movil.json"
    )

    # 2. Inyección del Core y Controlador
    kanban_manager = KanbanManager(repository)
    controller = MainController(kanban_manager)

    # 3. Lanzar la Vista Móvil
    print("[Móvil] Inicializando componentes nativos y bucle asíncrono...")
    app = MatrizEnfoqueMobileApp(page, controller)
    
    # 4. Vinculación Reactiva
    controller.register_view_callbacks(
        on_kanban_changed=app.refresh_ui,
        on_pomodoro_tick=app.refresh_pomodoro
    )

    # 5. Renderizado inicial
    app.refresh_ui() 


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)