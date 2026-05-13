import json

import pytest

from ni_ctrl_py.config import load_config
from ni_ctrl_py.scan import run_scan


def test_load_config_rejects_unknown_keys(tmp_path) -> None:
    cfg = {
        "positions": {"z_start_um": "48.00", "unknown_field": 123},
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown keys for PositionsConfig"):
        load_config(path)


def test_scan_rejects_zero_triggers_per_position(tmp_path) -> None:
    cfg = {
        "dry_run": True,
        "log_path": str(tmp_path / "scan.csv"),
        "positions": {
            "z_start_um": "50.00",
            "z_end_um": "50.00",
            "z_step_um": "0.01",
        },
        "timing": {"triggers_per_position": 0},
    }
    path = tmp_path / "bad_triggers.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="triggers_per_position"):
        run_scan(load_config(path))
