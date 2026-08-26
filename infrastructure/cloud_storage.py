# infrastructure/cloud_storage.py
import urllib.request
import urllib.error
import json
import ssl
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable
from core.entities import KanbanTask, KanbanColumn, BuJoSymbol
from core.interfaces import ITaskRepository
from infrastructure.local_storage import JSONTaskRepository


class LocalFirstTaskRepository(ITaskRepository):
    """
    Repositorio Local-First Autónomo con Sincronización Asíncrona Bidireccional en Segundo Plano.
    
    Características clave:
    - 0 ms de latencia en la UI: Lecturas y escrituras son 100% locales e instantáneas.
    - Sincronización en segundo plano (hilo daemon no bloqueante): La UI nunca se congela,
      incluso si la red corporativa bloquea Firebase, causa timeouts o altera certificados SSL.
    - Detección inteligente de red: Sincroniza automáticamente en redes libres/datos móviles
      y reintenta periódicamente.
    - Protección contra pérdida de datos: Nunca elimina datos locales ante caídas o respuestas vacías.
    """

    def __init__(self, database_url: str, user_id: str = "usuario_unico", local_filepath: str = "matriz_datos.json"):
        self.local_repo = JSONTaskRepository(filepath=local_filepath)
        self.database_url = database_url.rstrip('/')
        self.user_id = user_id
        self.base_url = f"{self.database_url}/users/{user_id}/tasks.json"
        
        # Contexto SSL que no rechaza certificados de inspección corporativa (Zscaler, Fortinet, etc.)
        self.ssl_context = ssl._create_unverified_context()
        
        # Callback opcional cuando la sincronización remota trae cambios
        self.on_sync_completed: Optional[Callable[[], None]] = None
        
        # Control del hilo de sincronización en segundo plano
        self._sync_lock = threading.Lock()
        self._sync_event = threading.Event()
        self._is_running = True
        self._last_sync_success: Optional[datetime] = None
        self._is_online = False
        
        # Iniciar hilo de sincronización en background
        self._sync_thread = threading.Thread(target=self._background_sync_loop, daemon=True, name="SyncWorker")
        self._sync_thread.start()
        
        # Disparar sincronización inicial
        self.trigger_sync()

    # --- API PÚBLICA (ITaskRepository) - 100% LOCAL E INSTANTÁNEA ---

    def get_all_tasks(self) -> List[KanbanTask]:
        """Lectura instantánea desde almacenamiento local (0 ms)."""
        return self.local_repo.get_all_tasks()

    def save_task(self, task: KanbanTask) -> None:
        """Guarda inmediatamente en local y encola la subida a Firebase."""
        self.local_repo.save_task(task)
        self.local_repo.add_pending_op("save", task.id)
        self.trigger_sync()

    def delete_task(self, task_id: str) -> None:
        """Marca como eliminada en local y encola el borrado en Firebase."""
        self.local_repo.delete_task(task_id)
        self.local_repo.add_pending_op("delete", task_id)
        self.trigger_sync()

    def get_metrics(self) -> Dict[str, int]:
        return self.local_repo.get_metrics()

    def increment_metrics(self, completed_tasks: int = 0, completed_key_activities: int = 0) -> None:
        self.local_repo.increment_metrics(completed_tasks, completed_key_activities)

    # --- CONTROL DE SINCRONIZACIÓN ASÍNCRONA ---

    def trigger_sync(self) -> None:
        """Notifica al hilo de fondo que intente sincronizar."""
        self._sync_event.set()

    def set_sync_callback(self, callback: Callable[[], None]) -> None:
        """Registra el callback para notificar a la UI cuando lleguen datos nuevos de la nube."""
        self.on_sync_completed = callback

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def last_sync_time(self) -> Optional[datetime]:
        return self._last_sync_success

    # --- COMUNICACIÓN HTTP SEGURA CONTRA BLOQUEOS CORPORATIVOS ---

    def _net_request(self, url: str, data: Optional[bytes] = None, method: str = 'GET') -> Tuple[bool, Optional[Any]]:
        """
        Ejecuta una petición HTTP con timeout estricto, headers estándar y tolerancia a proxies.
        Retorna (éxito: bool, respuesta_parseada: Any).
        """
        req = urllib.request.Request(url=url, method=method)
        if data is not None:
            req.data = data
            req.add_header('Content-Type', 'application/json')
        
        # Headers para evitar bloqueos por agentes genéricos de Python en firewalls corporativos
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MatrizEnfoque/1.0.4')
        req.add_header('Accept', 'application/json')

        try:
            # Timeout corto de 2.5s para no retener recursos del hilo de fondo
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=2.5) as response:
                content = response.read().decode('utf-8')
                if not content or content == "null":
                    return True, None
                return True, json.loads(content)
        except urllib.error.HTTPError as e:
            # Errores HTTP del servidor (404, 403, 500, etc.)
            return False, None
        except Exception:
            # Timeouts, DNS fallidos, firewall bloqueando puerto o alterando paquetes
            return False, None

    # --- BUCLE DE FONDO DE SINCRONIZACIÓN ---

    def _background_sync_loop(self) -> None:
        """Bucle daemon que maneja sincronizaciones activas y periódicas cada 20 segundos."""
        while self._is_running:
            # Espera evento de sincronización o timeout de 20s para reintento periódico
            self._sync_event.wait(timeout=20.0)
            self._sync_event.clear()

            if not self._is_running:
                break

            with self._sync_lock:
                has_changes = self._execute_full_sync()
                if has_changes and self.on_sync_completed:
                    try:
                        self.on_sync_completed()
                    except Exception:
                        pass

    def _execute_full_sync(self) -> bool:
        """
        Ejecuta la sincronización bidireccional completa.
        Retorna True si hubo cambios que requieran refrescar la UI.
        """
        # 1. PUSH: Enviar operaciones locales pendientes
        push_ok = self._push_pending_ops()
        if not push_ok:
            self._is_online = False
            return False  # Sin conexión o red bloqueada

        # 2. PULL: Traer estado remoto y fusionar
        pull_ok, changes_found = self._pull_remote_state()
        if pull_ok:
            self._is_online = True
            self._last_sync_success = datetime.now()
        else:
            self._is_online = False

        return changes_found

    def _push_pending_ops(self) -> bool:
        """Envía todas las operaciones locales acumuladas hacia Firebase."""
        pending_ops = self.local_repo.get_pending_ops()
        if not pending_ops:
            return True

        all_raw = self.local_repo.get_all_raw_tasks_including_deleted()
        local_dict = {t["id"]: t for t in all_raw}

        for op in list(pending_ops):
            action = op.get("action")
            tid = op.get("task_id")
            if not tid:
                continue

            task_url = self.base_url.replace(".json", f"/{tid}.json")

            if action == "save":
                raw_task = local_dict.get(tid)
                if not raw_task:
                    self.local_repo.remove_pending_op("save", tid)
                    continue

                if raw_task.get("is_deleted_locally", False):
                    # Si fue borrada después de editarse offline, no la subimos
                    self.local_repo.remove_pending_op("save", tid)
                    continue

                # Preparar payload limpio
                payload = {
                    "id": raw_task["id"],
                    "title": raw_task["title"],
                    "symbol": raw_task["symbol"],
                    "column": raw_task["column"],
                    "is_starred": raw_task.get("is_starred", False),
                    "is_inspired": raw_task.get("is_inspired", False),
                    "created_at": raw_task.get("created_at", datetime.now().isoformat()),
                    "is_archived": raw_task.get("is_archived", False)
                }
                data_bytes = json.dumps(payload).encode('utf-8')
                ok, _ = self._net_request(url=task_url, data=data_bytes, method='PUT')
                if ok:
                    self.local_repo.remove_pending_op("save", tid)
                else:
                    return False  # Falló la red

            elif action == "delete":
                ok, _ = self._net_request(url=task_url, method='DELETE')
                if ok:
                    self.local_repo.remove_pending_op("delete", tid)
                    self.local_repo.hard_delete_task(tid)
                else:
                    return False  # Falló la red

        return True

    def _pull_remote_state(self) -> Tuple[bool, bool]:
        """
        Descarga el estado de Firebase y lo fusiona con el almacenamiento local.
        Retorna (éxito_de_red: bool, hubo_cambios_locales: bool).
        """
        ok, cloud_data = self._net_request(self.base_url, method='GET')
        if not ok:
            return False, False

        has_changes = False
        local_raw = self.local_repo.get_all_raw_tasks_including_deleted()
        local_dict = {t["id"]: t for t in local_raw}
        pending_ops = self.local_repo.get_pending_ops()
        pending_tids = {op.get("task_id") for op in pending_ops}

        # Caso A: Firebase está vacío / null
        if cloud_data is None or not isinstance(cloud_data, dict) or len(cloud_data) == 0:
            # Si en local tenemos tareas activas y Firebase está vacío, inicializamos Firebase
            active_locals = [t for t in local_raw if not t.get("is_deleted_locally", False)]
            if active_locals:
                for t in active_locals:
                    self.local_repo.add_pending_op("save", t["id"])
                # Disparar subida inmediata
                self._push_pending_ops()
            return True, False

        # Caso B: Firebase tiene datos
        # 1. Procesar tareas remotas hacia local
        for tid, remote_task in cloud_data.items():
            if not remote_task or not isinstance(remote_task, dict):
                continue

            # Si la tarea tiene operaciones pendientes locales, priorizar el estado local
            if tid in pending_tids:
                continue

            if tid not in local_dict:
                # Tarea creada en otro dispositivo -> agregar localmente
                created_dt = None
                if "created_at" in remote_task and remote_task["created_at"]:
                    try:
                        created_dt = datetime.fromisoformat(remote_task["created_at"])
                    except Exception:
                        created_dt = None

                sym_val = remote_task.get("symbol", BuJoSymbol.TASK_PENDING.value)
                symbol = BuJoSymbol.TASK_PENDING
                for s in BuJoSymbol:
                    if s.value == sym_val:
                        symbol = s
                        break

                col_val = remote_task.get("column", KanbanColumn.TO_DO.value)
                column = KanbanColumn.TO_DO
                for c in KanbanColumn:
                    if c.value == col_val:
                        column = c
                        break

                new_task = KanbanTask(task_id=tid, title=remote_task.get("title", ""), symbol=symbol, created_at=created_dt)
                new_task.column = column
                new_task.is_starred = bool(remote_task.get("is_starred", False))
                new_task.is_inspired = bool(remote_task.get("is_inspired", False))
                new_task.is_archived = bool(remote_task.get("is_archived", False))
                self.local_repo.save_task(new_task)
                has_changes = True

            else:
                # Tarea existe en ambos lados -> verificar si hubo cambios remotos
                local_t = local_dict[tid]
                if local_t.get("is_deleted_locally", False):
                    # Si fue borrada localmente pero no tiene pending op, reconciliar
                    continue

                # Comprobar diferencias
                differs = (
                    local_t.get("title") != remote_task.get("title") or
                    local_t.get("column") != remote_task.get("column") or
                    local_t.get("symbol") != remote_task.get("symbol") or
                    local_t.get("is_starred") != remote_task.get("is_starred", False) or
                    local_t.get("is_inspired") != remote_task.get("is_inspired", False) or
                    local_t.get("is_archived") != remote_task.get("is_archived", False)
                )
                if differs:
                    sym_val = remote_task.get("symbol", BuJoSymbol.TASK_PENDING.value)
                    symbol = BuJoSymbol.TASK_PENDING
                    for s in BuJoSymbol:
                        if s.value == sym_val:
                            symbol = s
                            break

                    col_val = remote_task.get("column", KanbanColumn.TO_DO.value)
                    column = KanbanColumn.TO_DO
                    for c in KanbanColumn:
                        if c.value == col_val:
                            column = c
                            break

                    updated = KanbanTask(task_id=tid, title=remote_task.get("title", ""), symbol=symbol)
                    updated.column = column
                    updated.is_starred = bool(remote_task.get("is_starred", False))
                    updated.is_inspired = bool(remote_task.get("is_inspired", False))
                    updated.is_archived = bool(remote_task.get("is_archived", False))
                    self.local_repo.save_task(updated)
                    has_changes = True

        # 2. Comprobar tareas borradas en el otro dispositivo
        for tid, local_t in local_dict.items():
            if local_t.get("is_deleted_locally", False):
                continue
            if tid in pending_tids:
                continue

            # Si no está en cloud y no tiene operaciones pendientes locales,
            # fue borrada desde otro dispositivo
            if tid not in cloud_data:
                self.local_repo.hard_delete_task(tid)
                has_changes = True

        return True, has_changes