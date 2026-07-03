from __future__ import annotations

import ipaddress
import os
import platform
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path

import psutil
import requests

try:
    from . import __version__
    from .config import AgentConfig
    from .proto import nezha_pb2
except ImportError:
    __version__ = "0.1.0"
    from config import AgentConfig
    from proto import nezha_pb2


@dataclass
class HostInfo:
    platform: str = ""
    platform_version: str = ""
    cpu: list[str] = field(default_factory=list)
    mem_total: int = 0
    disk_total: int = 0
    swap_total: int = 0
    arch: str = ""
    virtualization: str = ""
    boot_time: int = 0
    version: str = __version__
    gpu: list[str] = field(default_factory=list)


@dataclass
class SensorTemperature:
    name: str
    temperature: float


@dataclass
class HostState:
    cpu: float = 0.0
    mem_used: int = 0
    swap_used: int = 0
    disk_used: int = 0
    net_in_transfer: int = 0
    net_out_transfer: int = 0
    net_in_speed: int = 0
    net_out_speed: int = 0
    uptime: int = 0
    load1: float = 0.0
    load5: float = 0.0
    load15: float = 0.0
    tcp_conn_count: int = 0
    udp_conn_count: int = 0
    process_count: int = 0
    temperatures: list[SensorTemperature] = field(default_factory=list)
    gpu: list[float] = field(default_factory=list)


class NetworkSpeedTracker:
    def __init__(self) -> None:
        self.last_time = time.monotonic()
        self.last_recv = 0
        self.last_sent = 0
        self.current_recv = 0
        self.current_sent = 0
        self.in_speed = 0
        self.out_speed = 0
        self.update(None)

    def update(self, allowlist: dict[str, bool] | None) -> None:
        recv = 0
        sent = 0
        counters = psutil.net_io_counters(pernic=True)
        for name, item in counters.items():
            if allowlist and not allowlist.get(name, False):
                continue
            recv += int(item.bytes_recv)
            sent += int(item.bytes_sent)

        now = time.monotonic()
        elapsed = max(now - self.last_time, 0.001)
        self.in_speed = max(0, int((recv - self.last_recv) / elapsed))
        self.out_speed = max(0, int((sent - self.last_sent) / elapsed))
        self.current_recv = recv
        self.current_sent = sent
        self.last_recv = recv
        self.last_sent = sent
        self.last_time = now


class SystemMonitor:
    VERSION = "2.2.2"

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.cached_host: HostInfo | None = None
        self.network = NetworkSpeedTracker()
        self.cached_country_code = ""
        self.geo_query_ip_changed = True
        self.cached_ipv4_addr = ""
        self.cached_ipv6_addr = ""

    def get_host_info(self) -> HostInfo:
        if self.cached_host is not None:
            return self.cached_host

        cpu_name = platform.processor() or platform.machine() or "CPU"
        host = HostInfo(
            platform=self._platform_name(),
            platform_version=platform.platform(),
            cpu=[cpu_name, f"{psutil.cpu_count(logical=True) or 0} core(s)"],
            mem_total=int(psutil.virtual_memory().total),
            disk_total=self._disk_total(),
            swap_total=int(psutil.swap_memory().total),
            arch=platform.machine(),
            virtualization=self._detect_virtualization(),
            boot_time=int(psutil.boot_time()),
            version=self.VERSION,
            gpu=[],
        )
        self.cached_host = host
        return host

    def get_state(self) -> HostState:
        self.network.update(self.config.nic_allowlist or {})
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load = self._load_average()
        state = HostState(
            cpu=round(float(psutil.cpu_percent(interval=1.0)), 2),
            mem_used=int(vm.total - vm.available),
            swap_used=int(swap.used),
            disk_used=self._disk_used(),
            net_in_transfer=self.network.current_recv,
            net_out_transfer=self.network.current_sent,
            net_in_speed=self.network.in_speed,
            net_out_speed=self.network.out_speed,
            uptime=max(0, int(time.time() - psutil.boot_time())),
            load1=load[0],
            load5=load[1],
            load15=load[2],
        )
        if not self.config.skip_connection_count:
            state.tcp_conn_count, state.udp_conn_count = self._connection_counts()
        if not self.config.skip_procs_count:
            state.process_count = len(psutil.pids())
        if self.config.temperature:
            state.temperatures = self._temperatures()
        if self.config.gpu:
            state.gpu = []
        return state

    def fetch_ip(self):
        public_ipv4 = ""
        public_ipv6 = ""
        apis = self.config.custom_ip_api or ["https://api64.ipify.org", "https://ip.sb", "https://api.ip.pb"]
        for api in apis:
            ip = self._fetch_external_ip(api)
            if not ip:
                continue
            if ":" in ip:
                public_ipv6 = ip
            else:
                public_ipv4 = ip
            if public_ipv4 or public_ipv6:
                break

        if not public_ipv4 and not public_ipv6:
            public_ipv4, public_ipv6 = self._local_ips()

        if not public_ipv4 and not public_ipv6:
            return None
        return nezha_pb2.GeoIP(
            use6=self.config.use_ipv6_country_code,
            ip=nezha_pb2.IP(ipv4=public_ipv4, ipv6=public_ipv6),
        )

    def host_to_proto(self, host: HostInfo):
        return nezha_pb2.Host(
            platform=host.platform,
            platform_version=host.platform_version,
            cpu=host.cpu,
            mem_total=host.mem_total,
            disk_total=host.disk_total,
            swap_total=host.swap_total,
            arch=host.arch,
            virtualization=host.virtualization,
            boot_time=host.boot_time,
            version=host.version,
            gpu=host.gpu,
        )

    def state_to_proto(self, state: HostState):
        return nezha_pb2.State(
            cpu=state.cpu,
            mem_used=state.mem_used,
            swap_used=state.swap_used,
            disk_used=state.disk_used,
            net_in_transfer=state.net_in_transfer,
            net_out_transfer=state.net_out_transfer,
            net_in_speed=state.net_in_speed,
            net_out_speed=state.net_out_speed,
            uptime=state.uptime,
            load1=state.load1,
            load5=state.load5,
            load15=state.load15,
            tcp_conn_count=state.tcp_conn_count,
            udp_conn_count=state.udp_conn_count,
            process_count=state.process_count,
            temperatures=[
                nezha_pb2.State_SensorTemperature(name=t.name, temperature=t.temperature)
                for t in state.temperatures
            ],
            gpu=state.gpu,
        )

    def _platform_name(self) -> str:
        if platform.system().lower() == "linux":
            os_release = Path("/etc/os-release")
            if os_release.exists():
                for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("ID="):
                        return line.split("=", 1)[1].strip().strip('"').lower()
        return platform.system().lower()

    def _disk_total(self) -> int:
        return sum(self._selected_partitions(lambda usage: int(usage.total)))

    def _disk_used(self) -> int:
        return sum(self._selected_partitions(lambda usage: int(usage.used)))

    def _selected_partitions(self, mapper) -> list[int]:
        values: list[int] = []
        allow = set(self.config.hard_drive_partition_allowlist or [])
        for part in psutil.disk_partitions(all=False):
            if allow and part.mountpoint not in allow:
                continue
            try:
                values.append(mapper(psutil.disk_usage(part.mountpoint)))
            except OSError:
                continue
        return values

    def _connection_counts(self) -> tuple[int, int]:
        tcp = 0
        udp = 0
        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.type == socket.SOCK_STREAM:
                    tcp += 1
                elif conn.type == socket.SOCK_DGRAM:
                    udp += 1
        except (psutil.AccessDenied, OSError):
            pass
        return tcp, udp

    def _temperatures(self) -> list[SensorTemperature]:
        result: list[SensorTemperature] = []
        try:
            for name, entries in psutil.sensors_temperatures(fahrenheit=False).items():
                for entry in entries:
                    if entry.current is not None:
                        label = entry.label or name
                        result.append(SensorTemperature(label, float(entry.current)))
        except (AttributeError, OSError):
            pass
        return result

    def _load_average(self) -> tuple[float, float, float]:
        try:
            return tuple(float(x) for x in os.getloadavg())
        except (AttributeError, OSError):
            return 0.0, 0.0, 0.0

    def _fetch_external_ip(self, url: str) -> str | None:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            ip = response.text.strip().split()[0]
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            return None

    def _local_ips(self) -> tuple[str, str]:
        ipv4 = ""
        ipv6 = ""
        for addrs in psutil.net_if_addrs().values():
            for addr in addrs:
                address = (addr.address or "").split("%", 1)[0]
                if not address or address.startswith("127.") or address == "::1":
                    continue
                if ":" in address and not ipv6:
                    ipv6 = address
                elif ":" not in address and not ipv4:
                    ipv4 = address
        changed = ipv4 != self.cached_ipv4_addr or ipv6 != self.cached_ipv6_addr
        self.geo_query_ip_changed = self.geo_query_ip_changed or changed
        self.cached_ipv4_addr = ipv4
        self.cached_ipv6_addr = ipv6
        return ipv4, ipv6

    def _detect_virtualization(self) -> str:
        product = Path("/sys/class/dmi/id/product_name")
        if product.exists():
            text = product.read_text(encoding="utf-8", errors="ignore").lower()
            for key in ("kvm", "virtualbox", "vmware", "hyper-v", "qemu", "xen"):
                if key in text:
                    return key
        if Path("/.dockerenv").exists():
            return "docker"
        return ""
