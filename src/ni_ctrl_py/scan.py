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
from .scan_plan import (
    assert_within_limits,
    describe_positions,
    format_um,
    make_z_positions,
    to_decimal,
)

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
        f"triggers_per_position={config.timing.triggers_per_position}; "
        f"inter_trigger={config.timing.inter_trigger_interval_s} s; "
        f"trigger={config.daq.trigger_line}; "
        f"dry_run={config.dry_run}"
    )


def force_dry_run(config: ScanConfig) -> ScanConfig:
    return replace(config, dry_run=True)


def run_scan(config: ScanConfig) -> Path:
    positions = positions_from_config(config)
    if config.timing.triggers_per_position < 1:
        raise ValueError("timing.triggers_per_position must be at least 1.")
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
        with (
            stage as stage_controller,
            trigger as trigger_controller,
            NITimingSnapshot(config.daq) as timing,
        ):
            z_return_um = to_decimal(config.positions.z_home_um)
            if config.positions.use_current_z_as_center:
                current_z_um = stage_controller.get_axis_position(config.axes.z)
                configured_center_um = to_decimal(config.positions.z_home_um)
                positions = tuple(
                    (current_z_um + (position - configured_center_um))
                    for position in positions
                )
                assert_within_limits(
                    positions,
                    config.positions.safe_z_min_um,
                    config.positions.safe_z_max_um,
                )
                z_return_um = current_z_um
                LOG.info(
                    "Using current Z as scan center: current=%s um; configured center=%s um",
                    format_um(current_z_um),
                    format_um(configured_center_um),
                )
                LOG.info("Resolved scan plan: %s", describe_positions(positions))

            initial_z_um = None if config.positions.use_current_z_as_center else z_return_um
            _move_to_home(config, stage_controller, initial_z_um)
            t0 = time.perf_counter()
            try:
                for index, z_um in enumerate(positions):
                    stage_controller.move_axis(config.axes.z, z_um)
                    time.sleep(config.timing.settle_time_s)

                    timing_before = timing.read()
                    trigger_perf_counters = []
                    for trigger_index in range(config.timing.triggers_per_position):
                        trigger_perf_counters.append(trigger_controller.pulse())
                        if trigger_index < config.timing.triggers_per_position - 1:
                            time.sleep(config.timing.inter_trigger_interval_s)
                    timing_after = timing.read()

                    elapsed_s = trigger_perf_counters[0] - t0
                    writer.writerow(
                        {
                            "index": index,
                            "z_um": format_um(z_um),
                            "trigger_elapsed_s": f"{elapsed_s:.6f}",
                            "trigger_count": config.timing.triggers_per_position,
                            "trigger_elapsed_all_s": ";".join(
                                f"{trigger_time - t0:.6f}"
                                for trigger_time in trigger_perf_counters
                            ),
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
            finally:
                stage_controller.move_axis(config.axes.z, z_return_um)
                LOG.info("Returned Z axis to center/home: %s um", format_um(z_return_um))

    LOG.info("Scan log written: %s", log_path)
    return log_path


def _make_writer(handle: TextIO) -> csv.DictWriter:
    fieldnames = [
        "index",
        "z_um",
        "trigger_elapsed_s",
        "trigger_count",
        "trigger_elapsed_all_s",
        "trigger_epoch_utc",
        "trigger_line",
        "timing_before",
        "timing_after",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    return writer


def _move_to_home(
    config: ScanConfig,
    stage_controller,  # type: ignore[no-untyped-def]
    z_um: Decimal | None,
) -> None:
    home = {
        config.axes.x: to_decimal(config.positions.x_um),
        config.axes.y: to_decimal(config.positions.y_um),
    }
    if z_um is not None:
        home[config.axes.z] = z_um
    stage_controller.move_many(home)


