#!/usr/bin/env python3
from __future__ import annotations

# Single-file clear-text Python Nezha Agent.
# This file is generated from the original split modules without obfuscation.

__version__ = "0.1.0"

import os

# Built-in config. Environment variables override these defaults.
SERVER = os.environ.get("SERVER", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
TLS = os.environ.get("TLS", "true").lower() == "true"
UUID = os.environ.get("UUID", "")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
REPORT_DELAY = int(os.environ.get("REPORT_DELAY", "4"))
IP_REPORT_PERIOD = int(os.environ.get("IP_REPORT_PERIOD", "1800"))


# ==================== config.py ====================
import stat
import uuid as uuid_lib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


@dataclass
class AgentConfig:
    # Official config.yml fields used by Nezha Agent v2.
    client_secret: str = ""
    debug: bool = False
    disable_auto_update: bool = False
    disable_command_execute: bool = False
    disable_force_update: bool = False
    disable_nat: bool = False
    disable_send_query: bool = False
    gpu: bool = False
    insecure_tls: bool = False
    ip_report_period: int = 1800
    report_delay: int = 4
    server: str = ""
    skip_connection_count: bool = False
    skip_procs_count: bool = False
    temperature: bool = False
    tls: bool = False
    use_gitee_to_upgrade: bool = False
    use_ipv6_country_code: bool = False
    uuid: str = ""

    # Extra optional fields accepted by the official agent when present.
    use_atomgit_to_upgrade: bool = False
    self_update_period: int = 0
    hard_drive_partition_allowlist: list[str] | None = None
    nic_allowlist: dict[str, bool] | None = None
    dns: list[str] | None = None
    custom_ip_api: list[str] | None = None

    # Runtime-only path, not written as a config key.
    file_path: str = "config.yml"


def default_config_path() -> str:
    return str(Path(__file__).resolve().parent / "config.yml")


def load_config(config_path: str | None = None) -> AgentConfig:
    path = Path(config_path).expanduser() if config_path else None
    data = _builtin_config_mapping()
    if path is not None:
        data.update(_read_yaml_mapping(path))
    _apply_env_overrides(data)

    config = _from_mapping(data)
    config.file_path = str(path or "<built-in>")

    if not config.uuid:
        config.uuid = str(uuid_lib.uuid4())
        save_config(config)

    validate_config(config)
    return config


def save_config(config: AgentConfig) -> None:
    path = Path(config.file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    for item in fields(config):
        if item.name == "file_path":
            continue
        value = getattr(config, item.name)
        if value is None:
            continue
        data[item.name] = value

    with path.open("w", encoding="utf-8") as fh:
        if yaml is not None:
            yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
        else:
            fh.write(_dump_simple_yaml(data))
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def validate_config(config: AgentConfig, remote_edit: bool = False) -> None:
    if config.report_delay == 0:
        config.report_delay = 3
    if config.ip_report_period == 0:
        config.ip_report_period = 1800
    elif config.ip_report_period < 30:
        config.ip_report_period = 30

    if config.report_delay < 1 or config.report_delay > 4:
        raise ValueError("report_delay ranges from 1-4")
    if not remote_edit:
        if not config.server:
            raise ValueError("server address should not be empty")
        if not config.client_secret:
            raise ValueError("client_secret must be specified")
        if not config.uuid:
            raise ValueError("uuid must be specified")


def _builtin_config_mapping() -> dict[str, Any]:
    return {
        "client_secret": CLIENT_SECRET,
        "debug": DEBUG,
        "disable_auto_update": False,
        "disable_command_execute": False,
        "disable_force_update": False,
        "disable_nat": False,
        "disable_send_query": False,
        "gpu": False,
        "insecure_tls": False,
        "ip_report_period": IP_REPORT_PERIOD,
        "report_delay": REPORT_DELAY,
        "server": SERVER,
        "skip_connection_count": False,
        "skip_procs_count": False,
        "temperature": False,
        "tls": TLS,
        "use_gitee_to_upgrade": False,
        "use_ipv6_country_code": False,
        "uuid": UUID,
    }


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        text = fh.read()
    if yaml is None:
        return _parse_simple_yaml(text)
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("config.yml must contain a YAML mapping")
    return {str(key): value for key, value in loaded.items()}


def _apply_env_overrides(data: dict[str, Any]) -> None:
    for env_key, value in os.environ.items():
        if env_key.startswith("NZ_"):
            data[env_key[3:].lower()] = value


def _from_mapping(data: dict[str, Any]) -> AgentConfig:
    known = {item.name for item in fields(AgentConfig)} - {"file_path"}
    cfg = AgentConfig()
    for key, value in data.items():
        if key not in known or value is None:
            continue
        if key in _BOOL_KEYS:
            setattr(cfg, key, _parse_bool(value))
        elif key in _INT_KEYS:
            setattr(cfg, key, int(value))
        elif key in _LIST_KEYS:
            setattr(cfg, key, _parse_list(value))
        elif key == "nic_allowlist":
            setattr(cfg, key, _parse_nic_allowlist(value))
        else:
            setattr(cfg, key, str(value))
    return cfg


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _parse_nic_allowlist(value: Any) -> dict[str, bool]:
    if isinstance(value, dict):
        return {str(key): _parse_bool(val) for key, val in value.items()}
    return {name: True for name in _parse_list(value)}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if current_list and stripped.startswith("-"):
            data.setdefault(current_list, []).append(_parse_scalar(stripped[1:].strip()))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_list = key
        else:
            data[key] = _parse_scalar(value)
    return data


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _dump_simple_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for item_key, item_value in value.items():
                if isinstance(item_value, bool):
                    item_value = str(item_value).lower()
                lines.append(f"  {item_key}: {item_value}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


_BOOL_KEYS = {
    "debug",
    "disable_auto_update",
    "disable_command_execute",
    "disable_force_update",
    "disable_nat",
    "disable_send_query",
    "gpu",
    "insecure_tls",
    "skip_connection_count",
    "skip_procs_count",
    "temperature",
    "tls",
    "use_gitee_to_upgrade",
    "use_ipv6_country_code",
    "use_atomgit_to_upgrade",
}
_INT_KEYS = {"ip_report_period", "report_delay", "self_update_period"}
_LIST_KEYS = {"hard_drive_partition_allowlist", "dns", "custom_ip_api"}


# ==================== proto/nezha_pb2.py ====================

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory


def _field(name, number, field_type, label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL, type_name=None):
    item = descriptor_pb2.FieldDescriptorProto(
        name=name,
        number=number,
        label=label,
        type=field_type,
    )
    if type_name:
        item.type_name = type_name
    return item


def _message(name, fields):
    msg = descriptor_pb2.DescriptorProto(name=name)
    msg.field.extend(fields)
    return msg


_file = descriptor_pb2.FileDescriptorProto(
    name="nezha.proto",
    package="proto",
    syntax="proto3",
)

_file.message_type.extend(
    [
        _message(
            "Host",
            [
                _field("platform", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("platform_version", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("cpu", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
                _field("mem_total", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("disk_total", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("swap_total", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("arch", 7, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("virtualization", 8, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("boot_time", 9, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("version", 10, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("gpu", 11, descriptor_pb2.FieldDescriptorProto.TYPE_STRING, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
            ],
        ),
        _message(
            "State",
            [
                _field("cpu", 1, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("mem_used", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("swap_used", 3, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("disk_used", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_in_transfer", 5, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_out_transfer", 6, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_in_speed", 7, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("net_out_speed", 8, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("uptime", 9, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("load1", 10, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("load5", 11, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("load15", 12, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
                _field("tcp_conn_count", 13, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("udp_conn_count", 14, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("process_count", 15, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("temperatures", 16, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, ".proto.State_SensorTemperature"),
                _field("gpu", 17, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE, descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED),
            ],
        ),
        _message(
            "State_SensorTemperature",
            [
                _field("name", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("temperature", 2, descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE),
            ],
        ),
        _message(
            "Task",
            [
                _field("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("type", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("data", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ],
        ),
        _message(
            "TaskResult",
            [
                _field("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("type", 2, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
                _field("delay", 3, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
                _field("data", 4, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("successful", 5, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL),
            ],
        ),
        _message("Receipt", [_field("proced", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL)]),
        _message("Uint64Receipt", [_field("data", 1, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64)]),
        _message("IOStreamData", [_field("data", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)]),
        _message(
            "GeoIP",
            [
                _field("use6", 1, descriptor_pb2.FieldDescriptorProto.TYPE_BOOL),
                _field("ip", 2, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, type_name=".proto.IP"),
                _field("country_code", 3, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("dashboard_boot_time", 4, descriptor_pb2.FieldDescriptorProto.TYPE_UINT64),
            ],
        ),
        _message(
            "IP",
            [
                _field("ipv4", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
                _field("ipv6", 2, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ],
        ),
    ]
)

_pool = descriptor_pool.Default()
try:
    DESCRIPTOR = _pool.AddSerializedFile(_file.SerializeToString())
except TypeError:
    DESCRIPTOR = _pool.FindFileByName("nezha.proto")

Host = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Host"))
State = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.State"))
State_SensorTemperature = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.State_SensorTemperature"))
Task = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Task"))
TaskResult = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.TaskResult"))
Receipt = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Receipt"))
Uint64Receipt = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.Uint64Receipt"))
IOStreamData = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.IOStreamData"))
GeoIP = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.GeoIP"))
IP = message_factory.GetMessageClass(_pool.FindMessageTypeByName("proto.IP"))

__all__ = [
    "Host",
    "State",
    "State_SensorTemperature",
    "Task",
    "TaskResult",
    "Receipt",
    "Uint64Receipt",
    "IOStreamData",
    "GeoIP",
    "IP",
]


# ==================== proto/nezha_pb2_grpc.py ====================

import grpc

class NezhaServiceStub(object):
    def __init__(self, channel):
        self.ReportSystemState = channel.stream_stream(
            "/proto.NezhaService/ReportSystemState",
            request_serializer=State.SerializeToString,
            response_deserializer=Receipt.FromString,
        )
        self.ReportSystemInfo = channel.unary_unary(
            "/proto.NezhaService/ReportSystemInfo",
            request_serializer=Host.SerializeToString,
            response_deserializer=Receipt.FromString,
        )
        self.RequestTask = channel.stream_stream(
            "/proto.NezhaService/RequestTask",
            request_serializer=TaskResult.SerializeToString,
            response_deserializer=Task.FromString,
        )
        self.IOStream = channel.stream_stream(
            "/proto.NezhaService/IOStream",
            request_serializer=IOStreamData.SerializeToString,
            response_deserializer=IOStreamData.FromString,
        )
        self.ReportGeoIP = channel.unary_unary(
            "/proto.NezhaService/ReportGeoIP",
            request_serializer=GeoIP.SerializeToString,
            response_deserializer=GeoIP.FromString,
        )
        self.ReportSystemInfo2 = channel.unary_unary(
            "/proto.NezhaService/ReportSystemInfo2",
            request_serializer=Host.SerializeToString,
            response_deserializer=Uint64Receipt.FromString,
        )


class NezhaServiceServicer(object):
    def ReportSystemState(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportSystemInfo(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def RequestTask(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def IOStream(self, request_iterator, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportGeoIP(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def ReportSystemInfo2(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


# ==================== grpc_client.py ====================

import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

import grpc

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Credentials:
    client_secret: str
    client_uuid: str


class AuthInterceptor(grpc.UnaryUnaryClientInterceptor, grpc.UnaryStreamClientInterceptor, grpc.StreamStreamClientInterceptor):
    def __init__(self, credentials: Credentials) -> None:
        self.credentials = credentials

    def _metadata(self, metadata: Sequence[tuple[str, str]] | None) -> list[tuple[str, str]]:
        merged = list(metadata or [])
        merged.append(("client-secret", self.credentials.client_secret))
        merged.append(("client-uuid", self.credentials.client_uuid))
        return merged

    def intercept_unary_unary(self, continuation, client_call_details, request):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        details = _ClientCallDetails(client_call_details, self._metadata(client_call_details.metadata))
        return continuation(details, request_iterator)


class _ClientCallDetails(grpc.ClientCallDetails):
    def __init__(self, source: grpc.ClientCallDetails, metadata: Iterable[tuple[str, str]]) -> None:
        self.method = source.method
        self.timeout = source.timeout
        self.metadata = list(metadata)
        self.credentials = source.credentials
        self.wait_for_ready = source.wait_for_ready
        self.compression = source.compression


class GrpcClient:
    def __init__(self, auth: AuthInterceptor) -> None:
        self.auth = auth
        self.channel: grpc.Channel | None = None
        self.stub: NezhaServiceStub | None = None

    def connect(self, config: AgentConfig) -> bool:
        self.disconnect()
        target = self._normalize_server(config.server)
        options = (
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
        )
        try:
            if config.tls:
                if config.insecure_tls:
                    # Python gRPC cannot disable verification per channel cleanly; use default TLS and rely on system trust.
                    log.warning("insecure_tls requested, but Python gRPC uses default certificate verification")
                credentials = grpc.ssl_channel_credentials(root_certificates=None)
                base_channel = grpc.secure_channel(target, credentials, options=options)
            else:
                base_channel = grpc.insecure_channel(target, options=options)

            self.channel = grpc.intercept_channel(base_channel, self.auth)
            self.stub = NezhaServiceStub(self.channel)
            grpc.channel_ready_future(base_channel).result(timeout=10)
            log.info("Connection to %s established", target)
            return True
        except Exception as exc:
            log.error("Failed to connect to dashboard: %s", exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        if self.channel is not None:
            close = getattr(self.channel, "close", None)
            if close is not None:
                close()
        self.channel = None
        self.stub = None

    @staticmethod
    def _normalize_server(server: str) -> str:
        if server.startswith("http://"):
            return server[7:]
        if server.startswith("https://"):
            return server[8:]
        return server


# ==================== monitor.py ====================

import ipaddress
import os
import platform
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path

import psutil
import requests


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
    VERSION = "6.6.6"

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
        return GeoIP(
            use6=self.config.use_ipv6_country_code,
            ip=IP(ipv4=public_ipv4, ipv6=public_ipv6),
        )

    def host_to_proto(self, host: HostInfo):
        return Host(
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
        return State(
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
                State_SensorTemperature(name=t.name, temperature=t.temperature)
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


# ==================== terminal.py ====================

import fcntl
import json
import logging
import os
import pty
import queue
import select
import shutil
import signal
import struct
import termios
import threading
import time
from collections.abc import Iterator

log = logging.getLogger(__name__)

STREAM_ID_HEADER = b"\xff\x05\xff\x05"


class TerminalHandler:
    def __init__(self, config: AgentConfig, grpc_client: GrpcClient) -> None:
        self.config = config
        self.grpc_client = grpc_client

    def handle(self, task) -> None:
        if self.config.disable_command_execute:
            log.info("Command execution is disabled for this agent")
            return

        stream_id = self._parse_stream_id(task.data)
        if not stream_id:
            log.error("Terminal task missing StreamID")
            return

        log.info("Terminal init %s", stream_id)
        session = TerminalSession(stream_id, self.grpc_client)
        thread = threading.Thread(target=session.run, name=f"terminal-{stream_id}", daemon=True)
        thread.start()

    @staticmethod
    def _parse_stream_id(data: str) -> str:
        try:
            payload = json.loads(data or "{}")
        except json.JSONDecodeError as exc:
            log.error("Terminal task parse error: %s", exc)
            return ""
        return str(payload.get("StreamID") or payload.get("stream_id") or payload.get("streamId") or "")


class TerminalSession:
    def __init__(self, stream_id: str, grpc_client: GrpcClient) -> None:
        self.stream_id = stream_id
        self.grpc_client = grpc_client
        self.outgoing: queue.Queue[bytes | None] = queue.Queue()
        self.stop = threading.Event()
        self.master_fd: int | None = None
        self.child_pid: int | None = None

    def run(self) -> None:
        try:
            self.child_pid, self.master_fd = pty.fork()
            if self.child_pid == 0:
                self._exec_shell()
                raise SystemExit(127)

            self.outgoing.put(STREAM_ID_HEADER + self.stream_id.encode("utf-8"))
            threads = [
                threading.Thread(target=self._read_pty_output, name=f"terminal-output-{self.stream_id}", daemon=True),
                threading.Thread(target=self._keepalive, name=f"terminal-keepalive-{self.stream_id}", daemon=True),
            ]
            for thread in threads:
                thread.start()

            assert self.grpc_client.stub is not None
            for item in self.grpc_client.stub.IOStream(self._request_iterator()):
                if self.stop.is_set():
                    break
                self._handle_input(bytes(item.data))
        except Exception as exc:
            log.error("Terminal IOStream failed for %s: %s", self.stream_id, exc)
        finally:
            self.close()
            log.info("Terminal session closed for %s", self.stream_id)

    def _exec_shell(self) -> None:
        env = os.environ.copy()
        env["TERM"] = "xterm"
        shell = self._select_shell()
        os.execvpe(shell, [shell], env)

    def _request_iterator(self) -> Iterator[object]:
        while not self.stop.is_set():
            try:
                data = self.outgoing.get(timeout=1)
            except queue.Empty:
                continue
            if data is None:
                break
            yield IOStreamData(data=data)

    def _read_pty_output(self) -> None:
        fd = self.master_fd
        if fd is None:
            return
        try:
            while not self.stop.is_set():
                try:
                    ready, _, _ = select.select([fd], [], [], 0.5)
                except OSError:
                    break
                if not ready:
                    continue
                try:
                    data = os.read(fd, 10240)
                except OSError:
                    break
                if not data:
                    break
                self.outgoing.put(data)
        finally:
            self.stop.set()
            self.outgoing.put(None)

    def _keepalive(self) -> None:
        while not self.stop.wait(30):
            self.outgoing.put(b"")

    def _handle_input(self, raw: bytes) -> None:
        fd = self.master_fd
        if not raw or fd is None:
            return
        data = self._strip_control_prefix(raw)
        data = self._handle_resize_prefix(data)
        if data:
            try:
                os.write(fd, data)
            except OSError:
                self.stop.set()

    def _handle_resize_prefix(self, raw: bytes) -> bytes:
        text = self._decode_control_text(raw)
        start = text.find("{")
        if start == -1 or ('"Rows"' not in text and '"rows"' not in text):
            return raw

        end = self._find_json_end(text, start)
        if end <= start:
            return raw

        try:
            size = json.loads(text[start : end + 1])
            rows = int(size.get("Rows", size.get("rows", 24)))
            cols = int(size.get("Cols", size.get("cols", 80)))
            self._resize(cols, rows)
            log.debug("Terminal resize for %s: %sx%s", self.stream_id, cols, rows)
            remaining = text[:start] + text[end + 1 :]
            return remaining.encode("utf-8")
        except Exception:
            return raw

    def _resize(self, cols: int, rows: int) -> None:
        if self.master_fd is None:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        if self.child_pid:
            try:
                os.kill(self.child_pid, signal.SIGWINCH)
            except OSError:
                pass

    def close(self) -> None:
        self.stop.set()
        self.outgoing.put(None)
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self.child_pid is not None:
            try:
                os.kill(self.child_pid, signal.SIGHUP)
            except OSError:
                pass
            try:
                os.waitpid(self.child_pid, os.WNOHANG)
            except ChildProcessError:
                pass
            self.child_pid = None

    @staticmethod
    def _select_shell() -> str:
        for shell in (os.environ.get("SHELL"), "zsh", "fish", "bash", "sh"):
            if shell and shutil.which(shell):
                return shell
        return "/bin/sh"

    @staticmethod
    def _strip_control_prefix(raw: bytes) -> bytes:
        if len(raw) > 1 and raw[0] == 0x01:
            rest = raw[1:]
            if all(byte in (9, 10, 13) or 32 <= byte <= 126 for byte in rest):
                return rest
        return raw

    @staticmethod
    def _decode_control_text(raw: bytes) -> str:
        if len(raw) >= 4 and len(raw) % 2 == 0:
            odd_nulls = sum(1 for idx in range(1, len(raw), 2) if raw[idx] == 0)
            even_nulls = sum(1 for idx in range(0, len(raw), 2) if raw[idx] == 0)
            if odd_nulls >= len(raw) // 4:
                return raw.decode("utf-16le", errors="ignore")
            if even_nulls >= len(raw) // 4:
                return raw.decode("utf-16be", errors="ignore")
        return raw.decode("utf-8", errors="ignore")

    @staticmethod
    def _find_json_end(text: str, start: int) -> int:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index
        return -1


# ==================== tasks.py ====================

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

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
        return TaskResult(id=task.id, type=task.type, successful=False, data="unsupported task type")

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)


# ==================== main.py ====================

import argparse
import logging
import queue
import signal
import sys
import threading
import time
from collections.abc import Iterator

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
