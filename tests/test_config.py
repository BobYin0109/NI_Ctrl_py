from ni_ctrl_py.config import load_config
from ni_ctrl_py.scan import describe_config


def test_load_full_config() -> None:
    config = load_config("configs/full_48_52_50nm.json")

    assert config.positions.z_start_um == "48.00"
    assert config.positions.z_end_um == "52.00"
    assert config.positions.z_step_um == "0.05"
    assert "81 positions" in describe_config(config)
