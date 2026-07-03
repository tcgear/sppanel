from __future__ import annotations

import os
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
    report_delay: int = 3
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
    path = Path(config_path or default_config_path()).expanduser()
    data = _read_yaml_mapping(path)
    _apply_env_overrides(data)

    config = _from_mapping(data)
    config.file_path = str(path)

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
