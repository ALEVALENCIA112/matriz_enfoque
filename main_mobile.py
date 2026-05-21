# main_mobile.py
import flet as ft
from infrastructure.cloud_storage import FirebaseTaskRepository
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from views_mobile.mobile_app import MatrizEnfoqueMobileApp

def main(page: ft.Page):
    # Configuración del lienzo de la app móvil
    page.title = "Matriz de Enfoque - Móvil"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 390   # Proporción aproximada de un teléfono estándar
    page.window_height = 844
    page.padding = 0

    # 1. CONEXIÓN A FIREBASE (Usa la misma URL y el mismo user_id de tu main.py)
    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"
    repository = FirebaseTaskRepository(database_url=FIREBASE_URL, user_id="ALEVALENCIA112")

    # 2. INYECCIÓN DEL CORE Y CONTROLADOR REUTILIZADOS
    kanban_manager = KanbanManager(repository=repository)
    controller = MainController(kanban_manager=kanban_manager)

    # 3. LANZAR LA VISTA MÓVIL
    app_view = MatrizEnfoqueMobileApp(page, controller)
    app_view.build_ui()

if __name__ == "__main__":
    # Arranca Flet en modo ventana de escritorio para pruebas de desarrollo
    ft.run(main)