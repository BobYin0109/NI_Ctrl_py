from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation

MICROMETER_QUANT = Decimal("0.000001")


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc


def format_um(value: Decimal) -> str:
    fixed = format(value.quantize(MICROMETER_QUANT), "f")
    return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed


def make_z_positions(
    start_um: Decimal | float | int | str,
    end_um: Decimal | float | int | str,
    step_um: Decimal | float | int | str,
) -> tuple[Decimal, ...]:
    start = to_decimal(start_um)
    end = to_decimal(end_um)
    step = to_decimal(step_um)

    if step == 0:
        raise ValueError("z_step_um must not be zero.")

    span = end - start
    if span == 0:
        return (start.quantize(MICROMETER_QUANT),)

    if (span > 0 and step < 0) or (span < 0 and step > 0):
        raise ValueError("z_step_um sign must point from z_start_um toward z_end_um.")

    intervals = span / step
    if intervals != intervals.to_integral_value():
        raise ValueError(
            "Z range must be exactly divisible by z_step_um. "
            f"Got start={start}, end={end}, step={step}."
        )

    count = int(intervals.copy_abs()) + 1
    return tuple((start + step * i).quantize(MICROMETER_QUANT) for i in range(count))


def describe_positions(positions: Sequence[Decimal]) -> str:
    if not positions:
        return "0 positions"
    return (
        f"{len(positions)} positions, "
        f"start={format_um(positions[0])} um, "
        f"end={format_um(positions[-1])} um"
    )


def assert_within_limits(
    positions: Iterable[Decimal],
    min_um: Decimal | float | int | str | None,
    max_um: Decimal | float | int | str | None,
) -> None:
    minimum = to_decimal(min_um) if min_um is not None else None
    maximum = to_decimal(max_um) if max_um is not None else None
    for position in positions:
        if minimum is not None and position < minimum:
            raise ValueError(f"Z position {format_um(position)} um is below safe minimum.")
        if maximum is not None and position > maximum:
            raise ValueError(f"Z position {format_um(position)} um is above safe maximum.")
