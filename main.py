# main.py
import sys
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from views.desktop_gui import DesktopGUI
# En tus puntos de entrada (main.py y main_mobile.py):
from infrastructure.cloud_storage import LocalFirstTaskRepository

def main():
    print("=====================================================================")
    print(" Iniciando: Matriz de Enfoque Elástico v1.0.4 (Suite de Escritorio)")
    print(" Arquitectura: Local-First con Sincronización Diferida Híbrida")
    print("=====================================================================\n")

    # URL base de la base de datos distribuida en Firebase Realtime
    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"

    # 1. Inyectamos la infraestructura híbrida (SOLID - DIP)
    # Almacena el estado transaccional en 'matriz_datos.json' antes de subirlo a la nube
    repository = LocalFirstTaskRepository(
        database_url=FIREBASE_URL,
        user_id="ALEVALENCIA112", 
        local_filepath="matriz_datos.json"
    )

    # 2. Inicializar el Core de Negocio inyectando su dependencia (SOLID - DIP)
    kanban_manager = KanbanManager(repository)

    # 3. Inicializar el Controlador y entregarle el control del motor de negocio
    controller = MainController(kanban_manager)

    # 4. Lanzamiento de la interfaz de usuario (MVC)
    try:
        # Aquí importaremos la vista de escritorio en el siguiente paso
        from views.desktop_gui import DesktopGUI
        
        app = DesktopGUI(controller)
        app.run()
        
    except ImportError as e:
        print(f"\n⚠️ Error de importación al levantar la interfaz gráfica: {e}")
        print("[Estructura OK] El Core, Controlador e Infraestructura están perfectamente acoplados.")
        print("Modo de depuración por consola activo.")
        print(f"Tareas actuales en 'Por Hacer': {len(controller.get_column_content('Por Hacer'))}")
        
if __name__ == "__main__":
    main()