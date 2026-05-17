"""验证已记录坐标点击脚本的 CLI。"""

from game_automation.recorded_click_cli import main


def test_recorded_click_cli_dry_run_prints_clicks_and_waits(capsys) -> None:
    """验证 dry-run 会按顺序打印点击和等待，不真实休眠。"""
    assert main(["--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "Point(x=242, y=92)" in output
    assert "duration_seconds=3" in output
    assert "Point(x=736, y=323)" in output
    assert "Point(x=741, y=400)" in output
    assert "duration_seconds=10" in output
