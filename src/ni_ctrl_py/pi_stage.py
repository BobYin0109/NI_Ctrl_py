from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Iterable, Protocol

from .config import AxesConfig, PIConfig
from .scan_plan import format_um

LOG = logging.getLogger(__name__)


class StageController(Protocol):
    def move_many(self, positions_um: dict[str, Decimal]) -> None:
        ...

    def move_axis(self, axis: str, position_um: Decimal) -> None:
        ...


class DryRunStage:
    def __init__(self, delay_s: float = 0.001) -> None:
        self.delay_s = delay_s

    def __enter__(self) -> "DryRunStage":
        LOG.info("DRY RUN: PI stage connection skipped.")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        LOG.info("DRY RUN: PI stage closed.")

    def move_many(self, positions_um: dict[str, Decimal]) -> None:
        formatted = {axis: format_um(position) for axis, position in positions_um.items()}
        LOG.info("DRY RUN: move axes to %s um", formatted)
        time.sleep(self.delay_s)

    def move_axis(self, axis: str, position_um: Decimal) -> None:
        LOG.info("DRY RUN: move axis %s to %s um", axis, format_um(position_um))
        time.sleep(self.delay_s)


class PIStage:
    def __init__(self, config: PIConfig, axes: AxesConfig) -> None:
        self.config = config
        self.axes = axes
        self._device = None
        self._pitools = None

    def __enter__(self) -> "PIStage":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._device is not None:
            try:
                self._device.CloseConnection()
            except Exception:  # pragma: no cover - hardware cleanup best effort
                LOG.exception("Failed to close PI connection cleanly.")

    def connect(self) -> None:
        try:
            from pipython import GCSDevice, pitools
        except ImportError as exc:  # pragma: no cover - depends on hardware environment
            raise RuntimeError(
                "PIPython is not installed. Run: python -m pip install -e \".[hardware]\""
            ) from exc

        self._pitools = pitools
        self._device = GCSDevice(self.config.controller)
        connection = self.config.connection.lower()

        if connection == "dialog":
            self._device.InterfaceSetupDlg()
        elif connection == "usb":
            if not self.config.usb_serial:
                raise ValueError("pi.usb_serial is required when pi.connection is 'usb'.")
            self._device.ConnectUSB(self.config.usb_serial)
        elif connection == "rs232":
            if not self.config.rs232_port:
                raise ValueError("pi.rs232_port is required when pi.connection is 'rs232'.")
            self._device.ConnectRS232(
                comport=self.config.rs232_port,
                baudrate=self.config.rs232_baudrate,
            )
        elif connection == "tcpip":
            if not self.config.tcpip_host:
                raise ValueError("pi.tcpip_host is required when pi.connection is 'tcpip'.")
            kwargs = {"ipaddress": self.config.tcpip_host}
            if self.config.tcpip_port is not None:
                kwargs["port"] = self.config.tcpip_port
            self._device.ConnectTCPIP(**kwargs)
        else:
            raise ValueError(f"Unsupported PI connection mode: {self.config.connection!r}")

        LOG.info("Connected PI controller: %s", self._device.qIDN().strip())
        if self.config.enable_servo:
            self._enable_servo([self.axes.x, self.axes.y, self.axes.z])

    def _enable_servo(self, axes: Iterable[str]) -> None:
        assert self._device is not None
        axis_list = [str(axis) for axis in axes]
        try:
            self._device.SVO(axis_list, [True] * len(axis_list))
            LOG.info("PI servo enabled for axes: %s", ", ".join(axis_list))
        except Exception:  # pragma: no cover - controller-specific behavior
            LOG.exception("Could not enable PI servo. Check controller/stage configuration.")
            raise

    def move_many(self, positions_um: dict[str, Decimal]) -> None:
        assert self._device is not None
        assert self._pitools is not None
        command = {str(axis): float(position) for axis, position in positions_um.items()}
        self._device.MOV(command)
        self._pitools.waitontarget(self._device, axes=list(command))

    def move_axis(self, axis: str, position_um: Decimal) -> None:
        assert self._device is not None
        assert self._pitools is not None
        axis_name = str(axis)
        self._device.MOV(axis_name, float(position_um))
        self._pitools.waitontarget(self._device, axes=[axis_name])
