from __future__ import annotations

import csv
import logging
import time
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from .config import ScanConfig
from .ni_trigger import DryRunTrigger, NIDigitalTrigger, NITimingSnapshot
from .pi_stage import DryRunStage, PIStage
from .scan_plan import assert_within_limits, describe_positions, format_um, make_z_positions, to_decimal

LOG = logging.getLogger(__name__)


def positions_from_config(config: ScanConfig) -> tuple[Decimal, ...]:
    positions = make_z_positions(
        config.positions.z_start_um,
        config.positions.z_end_um,
        config.positions.z_step_um,
    )
    assert_within_limits(
        positions,
        config.positions.safe_z_min_um,
        config.positions.safe_z_max_um,
    )
    return positions


def describe_config(config: ScanConfig) -> str:
    positions = positions_from_config(config)
    return (
        f"{describe_positions(positions)}; "
        f"step={config.positions.z_step_um} um; "
        f"settle={config.timing.settle_time_s} s; "
        f"pulse={config.timing.trigger_pulse_s} s; "
        f"trigger={config.daq.trigger_line}; "
        f"dry_run={config.dry_run}"
    )


def force_dry_run(config: ScanConfig) -> ScanConfig:
    return replace(config, dry_run=True)


def run_scan(config: ScanConfig) -> Path:
    positions = positions_from_config(config)
    log_path = Path(config.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    LOG.info("Scan plan: %s", describe_config(config))
    stage = DryRunStage() if config.dry_run else PIStage(config.pi, config.axes)
    trigger = (
        DryRunTrigger(config.timing)
        if config.dry_run
        else NIDigitalTrigger(config.daq, config.timing)
    )

    with log_path.open("w", newline="", encoding="utf-8") as handle:
        writer = _make_writer(handle)
        with stage as stage_controller, trigger as trigger_controller, NITimingSnapshot(config.daq) as timing:
            _move_to_home(config, stage_controller)
            t0 = time.perf_counter()
            for index, z_um in enumerate(positions):
                stage_controller.move_axis(config.axes.z, z_um)
                time.sleep(config.timing.settle_time_s)

                timing_before = timing.read()
                trigger_perf_counter = trigger_controller.pulse()
                timing_after = timing.read()

                elapsed_s = trigger_perf_counter - t0
                writer.writerow(
                    {
                        "index": index,
                        "z_um": format_um(z_um),
                        "trigger_elapsed_s": f"{elapsed_s:.6f}",
                        "trigger_epoch_utc": datetime.now(timezone.utc).isoformat(),
                        "trigger_line": config.daq.trigger_line,
                        "timing_before": timing_before,
                        "timing_after": timing_after,
                    }
                )
                LOG.info(
                    "%04d Z=%s um trigger @ %.6f s",
                    index,
                    format_um(z_um),
                    elapsed_s,
                )

    LOG.info("Scan log written: %s", log_path)
    return log_path


def _make_writer(handle: TextIO) -> csv.DictWriter:
    fieldnames = [
        "index",
        "z_um",
        "trigger_elapsed_s",
        "trigger_epoch_utc",
        "trigger_line",
        "timing_before",
        "timing_after",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    return writer


def _move_to_home(config: ScanConfig, stage_controller) -> None:  # type: ignore[no-untyped-def]
    home = {
        config.axes.x: to_decimal(config.positions.x_um),
        config.axes.y: to_decimal(config.positions.y_um),
        config.axes.z: to_decimal(config.positions.z_home_um),
    }
    stage_controller.move_many(home)
