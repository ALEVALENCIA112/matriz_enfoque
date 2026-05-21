# main.py
import sys
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from views.desktop_gui import DesktopGUI
# En tus puntos de entrada (main.py y main_mobile.py):
from infrastructure.cloud_storage import LocalFirstTaskRepository

def main():
    print("Iniciando la Matriz de Enfoque Elástico con Sincronización en la Nube...")

    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"


    # 2. Inyectamos la Infraestructura de la Nube en lugar de la Local
    repository = LocalFirstTaskRepository(database_url=FIREBASE_URL,
                                        user_id="ALEVALENCIA112", 
                                        local_filepath="matriz_datos.json"
    )

    # 3. Inicializar el Core de Negocio inyectando su dependencia (SOLID - DIP)
    kanban_manager = KanbanManager(repository)

    # 4. Inicializar el Controlador y entregarle el control del motor de negocio
    controller = MainController(kanban_manager)

    # 5. Lanzamiento de la interfaz de usuario (MVC)
    try:
        # Aquí importaremos la vista de escritorio en el siguiente paso
        from views.desktop_gui import DesktopGUI
        
        app = DesktopGUI(controller)
        app.run()
        
    except ImportError:
        print("\n[Estructura OK] El Core, Controlador e Infraestructura están perfectamente acoplados.")
        print("Modo de depuración por consola activo (Falta la interfaz gráfica en views/).")
        # Demostración rápida de alta cohesión en consola si no existe la vista
        print(f"Tareas actuales en 'Por Hacer': {controller.get_column_content(controller.get_column_content.__self__.kanban_manager.repository.get_all_tasks())}")

if __name__ == "__main__":
    main()