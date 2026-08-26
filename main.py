# main.py
import sys
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from infrastructure.cloud_storage import LocalFirstTaskRepository


def main():
    print("=====================================================================")
    print(" Iniciando: Matriz de Enfoque Elástico v1.0.4 (Suite de Escritorio)")
    print(" Arquitectura: Local-First con Sincronización Asíncrona Híbrida")
    print("=====================================================================\n")

    # URL base de la base de datos distribuida en Firebase Realtime
    FIREBASE_URL = "https://matriz-enfoque-default-rtdb.firebaseio.com/"

    # 1. Inyectamos la infraestructura híbrida (SOLID - DIP)
    # Almacena el estado transaccional localmente antes de sincronizar en segundo plano
    repository = LocalFirstTaskRepository(
        database_url=FIREBASE_URL,
        user_id="ALEVALENCIA112", 
        local_filepath="matriz_datos.json"
    )

    # 2. Inicializar el Core de Negocio inyectando su dependencia
    kanban_manager = KanbanManager(repository)

    # 3. Inicializar el Controlador
    controller = MainController(kanban_manager)

    # 4. Lanzamiento de la interfaz de usuario de escritorio
    try:
        from views.desktop_gui import DesktopGUI
        
        app = DesktopGUI(controller)
        app.run()
        
    except Exception as e:
        print(f"\n⚠️ Error al levantar la interfaz gráfica: {e}")
        print("[Estructura OK] El Core, Controlador e Infraestructura están activos.")
        

if __name__ == "__main__":
    main()