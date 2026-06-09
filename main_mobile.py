# main_mobile.py
import flet as ft
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from views_mobile.mobile_app import MatrizEnfoqueMobileApp
# En tus puntos de entrada (main.py y main_mobile.py):
from infrastructure.cloud_storage import LocalFirstTaskRepository

def main(page: ft.Page):
    # Configuración del lienzo de la app móvil
    page.title = "Matriz de Enfoque - Móvil v1.0.4"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 390   # Proporción aproximada de un teléfono estándar
    page.window_height = 844
    page.padding = 0

    # URL central de sincronización Firebase (idéntica a la versión de escritorio)
    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"

    # 1. Inyección del Repositorio Local-First Autónomo para el APK
    # Utiliza un archivo JSON independiente ('matriz_movil.json') para evitar colisiones en entornos de prueba cruzados
    repository = LocalFirstTaskRepository(
        database_url=FIREBASE_URL,
        user_id="ALEVALENCIA112",
        local_filepath="matriz_movil.json"
    )

    # 2. INYECCIÓN DEL CORE Y CONTROLADOR REUTILIZADOS
    kanban_manager = KanbanManager(repository)
    controller = MainController(kanban_manager)

    # 3. LANZAR LA VISTA MÓVIL
    print("[Móvil] Inicializando componentes nativos y bucle asíncrono...")
    app = MatrizEnfoqueMobileApp(page, controller)
    
    # 4. Vinculación Reactiva (Callbacks de actualización automática)
    # Aquí mapeamos el evento del controlador directamente al método real 'refresh_ui'
    controller.register_view_callbacks(
        on_kanban_changed=app.refresh_ui,
        on_pomodoro_tick=app.refresh_pomodoro
    )

    # 5. Disparar el renderizado inicial JIT usando el método correcto
    app.refresh_ui() 

# 5. INICIALIZACIÓN DEL MOTOR DE FLET (Actualizado para evitar DeprecationWarning)
if __name__ == "__main__":
    ft.run(main)