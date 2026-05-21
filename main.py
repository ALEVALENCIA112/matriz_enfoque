# main.py
import sys
from infrastructure.local_storage import JSONTaskRepository
from core.use_cases import KanbanManager
from controllers.main_controller import MainController

def main():
    print("Iniciando la Matriz de Enfoque Elástico...")

    # 1. Inicializar la infraestructura (Persistencia en disco)
    repository = JSONTaskRepository(filepath="bujo_kanban_data.json")

    # 2. Inicializar el Core de Negocio inyectando su dependencia (SOLID - DIP)
    kanban_manager = KanbanManager(repository=repository)

    # 3. Inicializar el Controlador y entregarle el control del motor de negocio
    controller = MainController(kanban_manager=kanban_manager)

    # 4. Lanzamiento de la interfaz de usuario (MVC)
    try:
        # Aquí importaremos la vista de escritorio en el siguiente paso
        from views.desktop_gui import DesktopGUI
        
        app = DesktopGUI(controller=controller)
        app.run()
        
    except ImportError:
        print("\n[Estructura OK] El Core, Controlador e Infraestructura están perfectamente acoplados.")
        print("Modo de depuración por consola activo (Falta la interfaz gráfica en views/).")
        # Demostración rápida de alta cohesión en consola si no existe la vista
        print(f"Tareas actuales en 'Por Hacer': {controller.get_column_content(controller.get_column_content.__self__.kanban_manager.repository.get_all_tasks())}")

if __name__ == "__main__":
    main()