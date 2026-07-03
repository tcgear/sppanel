from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

try:
    from .config import AgentConfig
    from .grpc_client import GrpcClient
    from .proto import nezha_pb2
    from .terminal import TerminalHandler
except ImportError:
    from config import AgentConfig
    from grpc_client import GrpcClient
    from proto import nezha_pb2
    from terminal import TerminalHandler

log = logging.getLogger(__name__)

HTTP_GET = 1
ICMP_PING = 2
TCP_PING = 3
COMMAND = 4
TERMINAL = 5
UPGRADE = 6
KEEPALIVE = 7
TERMINAL_GRPC = 8
NAT = 9
REPORT_HOST_INFO_DEPRECATED = 10
FM = 11
REPORT_CONFIG = 12
APPLY_CONFIG = 13
SERVER_TRANSFER_APPLY = 14
EXEC = 15
FS_LIST = 16
FS_READ = 17
FS_WRITE = 18
FS_DELETE = 19
FS_TRANSFER = 20


class TaskDispatcher:
    def __init__(self, config: AgentConfig, grpc_client: GrpcClient) -> None:
        self.config = config
        self.grpc_client = grpc_client
        self.terminal_handler = TerminalHandler(config, grpc_client)
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="task")

    def dispatch(self, task, result_sender: Callable[[object], None], cancel_callback: Callable[[], None]) -> None:
        self.executor.submit(self._run_task, task, result_sender, cancel_callback)

    def _run_task(self, task, result_sender: Callable[[object], None], cancel_callback: Callable[[], None]) -> None:
        try:
            result = self._do_task(task)
            if result is not None:
                result_sender(result)
        except Exception as exc:
            log.exception("Task execution error for task type=%s: %s", task.type, exc)
            cancel_callback()

    def _do_task(self, task):
        if task.type == KEEPALIVE:
            return None
        if task.type in (TERMINAL, TERMINAL_GRPC):
            self.terminal_handler.handle(task)
            return None
        log.warning("Unsupported task type: %s", task.type)
        return nezha_pb2.TaskResult(id=task.id, type=task.type, successful=False, data="unsupported task type")

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
