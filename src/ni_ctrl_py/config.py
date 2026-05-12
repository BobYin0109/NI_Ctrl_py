from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar


@dataclass(frozen=True)
class PIConfig:
    controller: str = "E-727"
    connection: str = "dialog"
    usb_serial: str | None = None
    rs232_port: str | None = None
    rs232_baudrate: int = 115200
    tcpip_host: str | None = None
    tcpip_port: int | None = None
    enable_servo: bool = True


@dataclass(frozen=True)
class AxesConfig:
    x: str = "1"
    y: str = "2"
    z: str = "3"


@dataclass(frozen=True)
class PositionsConfig:
    x_um: str = "100.00"
    y_um: str = "100.00"
    z_home_um: str = "50.00"
    z_start_um: str = "48.00"
    z_end_um: str = "52.00"
    z_step_um: str = "0.05"
    safe_z_min_um: str | None = None
    safe_z_max_um: str | None = None


@dataclass(frozen=True)
class DAQConfig:
    trigger_line: str = "Dev1/port2/line5"
    timing_lines: list[str] | None = None
    read_timing_snapshots: bool = False

    def __post_init__(self) -> None:
        if self.timing_lines is None:
            object.__setattr__(self, "timing_lines", [])


@dataclass(frozen=True)
class TimingConfig:
    settle_time_s: float = 0.03
    trigger_pulse_s: float = 0.005
    pre_trigger_low_s: float = 0.001


@dataclass(frozen=True)
class ScanConfig:
    dry_run: bool = False
    log_path: str = "logs/z_scan.csv"
    pi: PIConfig = PIConfig()
    axes: AxesConfig = AxesConfig()
    positions: PositionsConfig = PositionsConfig()
    daq: DAQConfig = DAQConfig()
    timing: TimingConfig = TimingConfig()


T = TypeVar("T")


def _coerce_dataclass(cls: type[T], data: dict[str, Any]) -> T:
    allowed = {field.name for field in fields(cls)}
    unknown = set(data) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown keys for {cls.__name__}: {names}")
    return cls(**data)


def load_config(path: str | Path) -> ScanConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a JSON object.")

    return ScanConfig(
        dry_run=bool(data.get("dry_run", False)),
        log_path=str(data.get("log_path", "logs/z_scan.csv")),
        pi=_coerce_dataclass(PIConfig, data.get("pi", {})),
        axes=_coerce_dataclass(AxesConfig, data.get("axes", {})),
        positions=_coerce_dataclass(PositionsConfig, data.get("positions", {})),
        daq=_coerce_dataclass(DAQConfig, data.get("daq", {})),
        timing=_coerce_dataclass(TimingConfig, data.get("timing", {})),
    )
