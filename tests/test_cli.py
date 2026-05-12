from __future__ import annotations

from ni_ctrl_py import cli
from ni_ctrl_py.config import ScanConfig


def test_scan_requires_confirm_hardware(monkeypatch) -> None:
    monkeypatch.setattr(cli, "load_config", lambda _path: ScanConfig(dry_run=False))

    try:
        cli.main(["scan", "--config", "configs/full_48_52_50nm.json"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected parser to exit when --confirm-hardware is missing")


def test_dry_run_forces_dry_mode(monkeypatch) -> None:
    captured: dict[str, bool] = {}

    monkeypatch.setattr(cli, "load_config", lambda _path: ScanConfig(dry_run=False))

    def fake_run_scan(config: ScanConfig):
        captured["dry_run"] = config.dry_run
        return None

    monkeypatch.setattr(cli, "run_scan", fake_run_scan)

    exit_code = cli.main(["dry-run", "--config", "configs/full_48_52_50nm.json"])

    assert exit_code == 0
    assert captured["dry_run"] is True
