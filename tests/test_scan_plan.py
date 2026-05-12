from decimal import Decimal

import pytest

from ni_ctrl_py.scan_plan import format_um, make_z_positions


def test_full_48_52_50nm_plan_has_81_positions() -> None:
    positions = make_z_positions("48.00", "52.00", "0.05")

    assert len(positions) == 81
    assert positions[0] == Decimal("48.000000")
    assert positions[-1] == Decimal("52.000000")


def test_small_test_plan_has_three_positions() -> None:
    positions = make_z_positions("49.95", "50.05", "0.05")

    assert [format_um(position) for position in positions] == ["49.95", "50", "50.05"]


def test_step_must_point_toward_end() -> None:
    with pytest.raises(ValueError, match="sign"):
        make_z_positions("48.00", "52.00", "-0.05")


def test_range_must_be_divisible_by_step() -> None:
    with pytest.raises(ValueError, match="exactly divisible"):
        make_z_positions("48.00", "52.00", "0.03")
