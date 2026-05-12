from __future__ import annotations

import argparse
import logging
import sys
import time
from decimal import Decimal

from .config import DAQConfig, TimingConfig, load_config
from .ni_trigger import NIDigitalTrigger
from .pi_stage import PIStage
from .scan import describe_config, force_dry_run, run_scan
from .scan_plan import format_um, to_decimal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ni-ctrl")
    parser.add_argument("--log-level", default="INFO", help="Python logging level.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Print the scan plan without hardware.")
    plan_parser.add_argument("--config", required=True)

    dry_parser = subparsers.add_parser("dry-run", help="Run the scan sequence without hardware.")
    dry_parser.add_argument("--config", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run the scan on real hardware.")
    scan_parser.add_argument("--config", required=True)
    scan_parser.add_argument(
        "--confirm-hardware",
        action="store_true",
        help="Required for non-dry real hardware execution.",
    )

    pulse_parser = subparsers.add_parser("test-pulse", help="Output repeated NI TTL pulses.")
    pulse_parser.add_argument("--line", required=True, help="Example: Dev1/port2/line5")
    pulse_parser.add_argument("--count", type=int, default=10)
    pulse_parser.add_argument("--pulse-width-s", type=float, default=0.005)
    pulse_parser.add_argument("--period-s", type=float, default=0.5)

    pi_parser = subparsers.add_parser("test-pi", help="Move one PI axis to one position.")
    pi_parser.add_argument("--config", required=True)
    pi_parser.add_argument("--axis", choices=["x", "y", "z"], default="z")
    pi_parser.add_argument("--position-um", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    if args.command == "plan":
        config = load_config(args.config)
        print(describe_config(config))
        return 0

    if args.command == "dry-run":
        config = force_dry_run(load_config(args.config))
        run_scan(config)
        return 0

    if args.command == "scan":
        config = load_config(args.config)
        if config.dry_run:
            run_scan(config)
            return 0
        if not args.confirm_hardware:
            parser.error("Real hardware scans require --confirm-hardware.")
        run_scan(config)
        return 0

    if args.command == "test-pulse":
        _test_pulse(args.line, args.count, args.pulse_width_s, args.period_s)
        return 0

    if args.command == "test-pi":
        _test_pi(args.config, args.axis, args.position_um)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _test_pulse(line: str, count: int, pulse_width_s: float, period_s: float) -> None:
    daq = DAQConfig(trigger_line=line)
    timing = TimingConfig(trigger_pulse_s=pulse_width_s)
    with NIDigitalTrigger(daq, timing) as trigger:
        for index in range(count):
            trigger.pulse()
            logging.info("Pulse %d/%d on %s", index + 1, count, line)
            time.sleep(period_s)


def _test_pi(config_path: str, axis_name: str, position_um: str) -> None:
    config = load_config(config_path)
    axis = getattr(config.axes, axis_name)
    position = to_decimal(position_um)
    _assert_test_position_safe(config, position)
    with PIStage(config.pi, config.axes) as stage:
        stage.move_axis(axis, position)
    logging.info("Moved axis %s to %s um", axis, format_um(position))


def _assert_test_position_safe(config, position: Decimal) -> None:  # type: ignore[no-untyped-def]
    minimum = config.positions.safe_z_min_um
    maximum = config.positions.safe_z_max_um
    if minimum is not None and position < to_decimal(minimum):
        raise ValueError(f"Requested position is below safe_z_min_um={minimum}.")
    if maximum is not None and position > to_decimal(maximum):
        raise ValueError(f"Requested position is above safe_z_max_um={maximum}.")


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    sys.exit(main())
