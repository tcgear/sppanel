from __future__ import annotations

import argparse
import logging
import queue
import signal
import sys
import threading
import time
from collections.abc import Iterator

try:
    from . import __version__
    from .config import load_config
    from .grpc_client import AuthInterceptor, Credentials, GrpcClient
    from .monitor import SystemMonitor
    from .tasks import TaskDispatcher
except ImportError:
    __version__ = "0.1.0"
    from config import load_config
    from grpc_client import AuthInterceptor, Credentials, GrpcClient
    from monitor import SystemMonitor
    from tasks import TaskDispatcher

log = logging.getLogger(__name__)


class AgentApplication:
    def __init__(self, config_path: str | None) -> None:
        self.config_path = config_path
        self.running = threading.Event()
        self.running.set()
        self.initialized = False
        self.prev_dashboard_boot_time = 0
        self.geoip_reported = False
        self.task_results: queue.Queue[object | None] = queue.Queue()
        self.grpc_client: GrpcClient | None = None
        self.monitor: SystemMonitor | None = None
        self.dispatcher: TaskDispatcher | None = None

    def run(self) -> int:
        try:
            config = load_config(self.config_path)
            logging.getLogger().setLevel(logging.DEBUG if config.debug else logging.INFO)
            log.info("Config loaded from: %s", config.file_path)

            self.monitor = SystemMonitor(config)
            auth = AuthInterceptor(Credentials(config.client_secret, config.uuid))
            self.grpc_client = GrpcClient(auth)
            self.dispatcher = TaskDispatcher(config, self.grpc_client)

            self._install_signals()
            while self.running.is_set():
                if not self.grpc_client.connect(config):
                    log.warning("Connection failed, retrying in 10 seconds...")
                    self._sleep(10)
                    continue

                try:
                    host = self.monitor.host_to_proto(self.monitor.get_host_info())
                    receipt = self.grpc_client.stub.ReportSystemInfo2(host, timeout=20)
                    dashboard_boot_time = int(receipt.data)
                    self.geoip_reported = (
                        self.geoip_reported
                        and self.prev_dashboard_boot_time > 0
                        and dashboard_boot_time == self.prev_dashboard_boot_time
                    )
                    self.prev_dashboard_boot_time = dashboard_boot_time
                    self.initialized = True

                    self._run_workers(config)
                except Exception as exc:
                    log.error("Agent loop error: %s", exc, exc_info=config.debug)
                finally:
                    self.grpc_client.disconnect()
                    if self.running.is_set():
                        log.warning("Worker error, retrying in 10 seconds...")
                        self._sleep(10)
        except Exception as exc:
            log.error("Agent initialization failed: %s", exc, exc_info=True)
            return 1
        finally:
            if self.dispatcher:
                self.dispatcher.shutdown()
            if self.grpc_client:
                self.grpc_client.disconnect()
        return 0

    def _run_workers(self, config) -> None:
        errors: queue.Queue[BaseException] = queue.Queue(maxsize=1)
        threads = [
            threading.Thread(target=self._worker_guard, args=(self._report_state_loop, config, errors), daemon=True),
            threading.Thread(target=self._worker_guard, args=(self._receive_tasks_loop, config, errors), daemon=True),
        ]
        for thread in threads:
            thread.start()
        while self.running.is_set():
            try:
                error = errors.get(timeout=1)
                raise error
            except queue.Empty:
                pass

    def _worker_guard(self, func, config, errors: queue.Queue[BaseException]) -> None:
        try:
            func(config)
        except BaseException as exc:
            if errors.empty():
                errors.put(exc)

    def _state_iterator(self, config) -> Iterator[object]:
        last_host_report = 0.0
        last_ip_report = 0.0
        while self.running.is_set():
            if self.initialized and self.monitor:
                state = self.monitor.state_to_proto(self.monitor.get_state())
                yield state
                now = time.time()
                if now - last_host_report > 10 * 60:
                    self._report_host_info()
                    last_host_report = now
                if now - last_ip_report > config.ip_report_period or not self.geoip_reported:
                    self._report_geoip(config)
                    last_ip_report = now
            self._sleep(config.report_delay)

    def _report_state_loop(self, config) -> None:
        assert self.grpc_client and self.grpc_client.stub
        for _ in self.grpc_client.stub.ReportSystemState(self._state_iterator(config)):
            if not self.running.is_set():
                break

    def _task_result_iterator(self) -> Iterator[object]:
        while self.running.is_set():
            try:
                item = self.task_results.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                break
            yield item

    def _receive_tasks_loop(self, config) -> None:
        assert self.grpc_client and self.grpc_client.stub and self.dispatcher
        for task in self.grpc_client.stub.RequestTask(self._task_result_iterator()):
            self.dispatcher.dispatch(task, self.task_results.put, self.running.clear)
            if not self.running.is_set():
                break

    def _report_host_info(self) -> None:
        try:
            assert self.grpc_client and self.grpc_client.stub and self.monitor
            receipt = self.grpc_client.stub.ReportSystemInfo2(self.monitor.host_to_proto(self.monitor.get_host_info()), timeout=20)
            dashboard_boot_time = int(receipt.data)
            self.geoip_reported = (
                self.geoip_reported
                and self.prev_dashboard_boot_time > 0
                and dashboard_boot_time == self.prev_dashboard_boot_time
            )
            self.prev_dashboard_boot_time = dashboard_boot_time
        except Exception as exc:
            log.error("ReportSystemInfo2 error: %s", exc)

    def _report_geoip(self, config) -> None:
        try:
            assert self.grpc_client and self.grpc_client.stub and self.monitor
            geoip = self.monitor.fetch_ip()
            if geoip is None:
                return
            if not self.monitor.geo_query_ip_changed and self.geoip_reported:
                return
            response = self.grpc_client.stub.ReportGeoIP(geoip, timeout=20)
            self.prev_dashboard_boot_time = int(response.dashboard_boot_time)
            self.monitor.cached_country_code = response.country_code
            self.monitor.geo_query_ip_changed = False
            self.geoip_reported = True
        except Exception as exc:
            log.error("ReportGeoIP error: %s", exc)

    def _sleep(self, seconds: float) -> None:
        deadline = time.time() + seconds
        while self.running.is_set() and time.time() < deadline:
            time.sleep(min(0.25, deadline - time.time()))

    def _install_signals(self) -> None:
        def stop(_signum, _frame) -> None:
            self.running.clear()
            self.task_results.put(None)

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python-nezha-agent", description="Nezha monitor agent in Python")
    parser.add_argument("-c", "--config", dest="config_path", help="config file path")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return AgentApplication(args.config_path).run()


if __name__ == "__main__":
    sys.exit(main())
