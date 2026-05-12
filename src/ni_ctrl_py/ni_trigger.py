from __future__ import annotations

import logging
import time
from typing import Any, Optional, Protocol

from .config import DAQConfig, TimingConfig

LOG = logging.getLogger(__name__)


class TriggerController(Protocol):
    def pulse(self) -> float:
        ...


class DryRunTrigger:
    def __init__(self, timing: TimingConfig) -> None:
        self.timing = timing

    def __enter__(self) -> "DryRunTrigger":
        LOG.info("DRY RUN: NI trigger task connection skipped.")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        LOG.info("DRY RUN: NI trigger task closed.")

    def pulse(self) -> float:
        time.sleep(self.timing.pre_trigger_low_s)
        trigger_time = time.perf_counter()
        LOG.info("DRY RUN: TTL high for %.6f s", self.timing.trigger_pulse_s)
        time.sleep(self.timing.trigger_pulse_s)
        return trigger_time


class NIDigitalTrigger:
    def __init__(self, daq: DAQConfig, timing: TimingConfig) -> None:
        self.daq = daq
        self.timing = timing
        self._task: Optional[Any] = None

    def __enter__(self) -> "NIDigitalTrigger":
        try:
            import nidaqmx
            from nidaqmx.constants import LineGrouping
        except ImportError as exc:  # pragma: no cover - depends on hardware environment
            raise RuntimeError(
                "nidaqmx is not installed. Run: python -m pip install -e \".[hardware]\""
            ) from exc

        self._task = nidaqmx.Task()
        self._task.do_channels.add_do_chan(
            self.daq.trigger_line,
            line_grouping=LineGrouping.CHAN_PER_LINE,
        )
        self._task.write(False)
        LOG.info("NI trigger line initialized low: %s", self.daq.trigger_line)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._task is not None:
            try:
                self._task.write(False)
            finally:
                self._task.close()
                LOG.info("NI trigger line closed low: %s", self.daq.trigger_line)

    def pulse(self) -> float:
        if self._task is None:
            raise RuntimeError("NI trigger task is not open.")
        self._task.write(False)
        time.sleep(self.timing.pre_trigger_low_s)
        trigger_time = time.perf_counter()
        self._task.write(True)
        time.sleep(self.timing.trigger_pulse_s)
        self._task.write(False)
        return trigger_time


class NITimingSnapshot:
    """Software snapshot of timing pins for diagnostics, not pulse-accurate acquisition."""

    def __init__(self, daq: DAQConfig) -> None:
        self.daq = daq
        self._task: Optional[Any] = None

    def __enter__(self) -> "NITimingSnapshot":
        if not self.daq.timing_lines or not self.daq.read_timing_snapshots:
            return self

        try:
            import nidaqmx
            from nidaqmx.constants import LineGrouping
        except ImportError as exc:  # pragma: no cover - depends on hardware environment
            raise RuntimeError(
                "nidaqmx is not installed. Run: python -m pip install -e \".[hardware]\""
            ) from exc

        self._task = nidaqmx.Task()
        physical_lines = ",".join(self.daq.timing_lines)
        self._task.di_channels.add_di_chan(
            physical_lines,
            line_grouping=LineGrouping.CHAN_PER_LINE,
        )
        LOG.info("NI timing snapshot lines initialized: %s", physical_lines)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if self._task is not None:
            self._task.close()

    def read(self) -> str:
        if self._task is None:
            return ""
        value = self._task.read()
        return repr(value)
