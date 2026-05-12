import json

import pytest

from ni_ctrl_py.config import load_config


def test_load_config_rejects_unknown_keys(tmp_path) -> None:
    cfg = {
        "positions": {"z_start_um": "48.00", "unknown_field": 123},
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown keys for PositionsConfig"):
        load_config(path)
