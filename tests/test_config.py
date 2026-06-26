from ni_ctrl_py.config import load_config
from ni_ctrl_py.scan import describe_config


def test_load_full_config() -> None:
    config = load_config("configs/full_48_52_50nm.json")

    assert config.positions.z_start_um == "48.00"
    assert config.positions.z_end_um == "52.00"
    assert config.positions.z_step_um == "0.05"
    assert "81 positions" in describe_config(config)


def test_load_tested_201_image_config() -> None:
    config = load_config("configs/z_stack_201_49_51_10nm.json")

    assert config.positions.z_start_um == "49.000"
    assert config.positions.z_end_um == "51.000"
    assert config.positions.z_step_um == "0.010"
    assert config.positions.z_home_um == "50.00"
    assert config.positions.use_current_z_as_center is True
    assert config.timing.triggers_per_position == 1
    assert "201 positions" in describe_config(config)


