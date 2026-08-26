# scratch/test_suite.py
import os
import sys
import time
import unittest
from datetime import datetime

# Añadir raíz al sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.entities import KanbanTask, KanbanColumn, BuJoSymbol, PomodoroInverse
from core.use_cases import KanbanManager
from controllers.main_controller import MainController
from infrastructure.local_storage import JSONTaskRepository, resolve_storage_path
from infrastructure.cloud_storage import LocalFirstTaskRepository


class TestMatrizEnfoque(unittest.TestCase):
    
    def setUp(self):
        self.test_json = "scratch/test_matriz.json"
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_local_storage_crud(self):
        repo = JSONTaskRepository(self.test_json)
        
        # 1. Crear tarea
        task1 = KanbanTask("t1", "Tarea de Prueba 1", BuJoSymbol.TASK_PENDING)
        repo.save_task(task1)
        
        tasks = repo.get_all_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, "t1")
        self.assertEqual(tasks[0].title, "Tarea de Prueba 1")
        
        # 2. Modificar tarea
        tasks[0].column = KanbanColumn.IN_PROGRESS
        tasks[0].is_starred = True
        repo.save_task(tasks[0])
        
        tasks_updated = repo.get_all_tasks()
        self.assertEqual(tasks_updated[0].column, KanbanColumn.IN_PROGRESS)
        self.assertTrue(tasks_updated[0].is_starred)
        
        # 3. Soft delete
        repo.delete_task("t1")
        self.assertEqual(len(repo.get_all_tasks()), 0)
        raw_tasks = repo.get_all_raw_tasks_including_deleted()
        self.assertEqual(len(raw_tasks), 1)
        self.assertTrue(raw_tasks[0]["is_deleted_locally"])
        
        # 4. Hard delete
        repo.hard_delete_task("t1")
        self.assertEqual(len(repo.get_all_raw_tasks_including_deleted()), 0)

    def test_pending_ops_queue(self):
        repo = JSONTaskRepository(self.test_json)
        repo.add_pending_op("save", "task_abc")
        repo.add_pending_op("save", "task_abc") # Duplicado no debe repetirse
        
        ops = repo.get_pending_ops()
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["action"], "save")
        
        repo.add_pending_op("delete", "task_abc")
        ops = repo.get_pending_ops()
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0]["action"], "delete") # Delete reemplaza save previo
        
        repo.remove_pending_op("delete", "task_abc")
        self.assertEqual(len(repo.get_pending_ops()), 0)

    def test_metrics_persistence(self):
        repo = JSONTaskRepository(self.test_json)
        metrics = repo.get_metrics()
        self.assertEqual(metrics["tareas_completadas"], 0)
        self.assertEqual(metrics["actividades_clave_completadas"], 0)
        
        repo.increment_metrics(completed_tasks=3, completed_key_activities=1)
        metrics = repo.get_metrics()
        self.assertEqual(metrics["tareas_completadas"], 3)
        self.assertEqual(metrics["actividades_clave_completadas"], 1)

    def test_kanban_manager_and_controller(self):
        repo = JSONTaskRepository(self.test_json)
        manager = KanbanManager(repo)
        controller = MainController(manager)
        
        # Agregar tarea regular
        err = controller.add_bujo_item("Revisar correos", BuJoSymbol.TASK_PENDING)
        self.assertIsNone(err)
        
        # Agregar actividad clave
        err = controller.add_bujo_item("Entregar informe clave", BuJoSymbol.KEY_ACTIVITY)
        self.assertIsNone(err)
        
        # Intentar agregar segunda actividad clave (debe ser rechazada por regla de negocio)
        err = controller.add_bujo_item("Otra actividad clave", BuJoSymbol.KEY_ACTIVITY)
        self.assertIsNotNone(err)
        self.assertIn("Actividad Clave", err)
        
        # Verificar contenido de columnas y orden (Actividad clave primero en Por Hacer)
        todo_items = controller.get_column_content(KanbanColumn.TO_DO)
        self.assertEqual(len(todo_items), 2)
        self.assertEqual(todo_items[0].symbol, BuJoSymbol.KEY_ACTIVITY)
        
        # Mover a En Proceso y luego a Hecho
        item_id = todo_items[0].id
        controller.move_bujo_item(item_id, KanbanColumn.IN_PROGRESS)
        controller.move_bujo_item(item_id, KanbanColumn.DONE)
        
        done_items = controller.get_column_content(KanbanColumn.DONE)
        self.assertEqual(len(done_items), 1)
        
        # Archivar completadas
        controller.archive_completed_tasks()
        done_items_after = controller.get_column_content(KanbanColumn.DONE)
        self.assertEqual(len(done_items_after), 0)
        
        # Verificar métricas
        metrics = controller.get_local_metrics()
        self.assertEqual(metrics["tareas_completadas"], 1)
        self.assertEqual(metrics["actividades_clave_completadas"], 1)

    def test_cloud_storage_offline_resilience(self):
        # Repositorio apuntando a URL inaccesible simulando bloqueo de red corporativa
        repo = LocalFirstTaskRepository(
            database_url="https://non-existent-corporate-blocked-firebase-domain-12345.com",
            user_id="TEST_USER",
            local_filepath=self.test_json
        )
        
        # Las operaciones deben responder instantáneamente sin bloquear
        start = time.time()
        task = KanbanTask("off_1", "Tarea en Modo Offline", BuJoSymbol.TASK_PENDING)
        repo.save_task(task)
        elapsed = time.time() - start
        
        # Tiempo de guardado debe ser menor a 50 milisegundos (no bloqueado por timeout de 3s)
        self.assertLess(elapsed, 0.05)
        
        all_tasks = repo.get_all_tasks()
        self.assertEqual(len(all_tasks), 1)
        self.assertEqual(all_tasks[0].title, "Tarea en Modo Offline")
        
        # La tarea debe seguir existiendo en disco local
        repo_reload = JSONTaskRepository(self.test_json)
        self.assertEqual(len(repo_reload.get_all_tasks()), 1)


if __name__ == "__main__":
    unittest.main()
