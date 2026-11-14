"""验证任务准备的按需配置读取与各入口错误映射。

使用临时工作区和模拟运行，不访问真实窗口、画面或输入。
"""

import time

import pytest

from game_automation.platform.local_desktop.entrypoints.cli import main
from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
    DesktopBackend,
)


@pytest.mark.parametrize("requires", ({}, {"states": ["主页"]}))
def test_unreadable_state_config_does_not_block_independent_dry_run(tmp_path, requires):
    """无依赖任务跳过配置，状态依赖未知时仍可使用固定模拟状态。"""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "assets" / "window-states.json").mkdir(parents=True)
    metadata = {"name": "independent", "requires": requires}
    (tmp_path / "scripts" / "task.py").write_text(
        f'TASK = {metadata!r}\ndef run(ctx):\n    """模拟等待。"""\n    ctx.wait(0)\n'
    )
    args = ["--workspace", str(tmp_path)]
    assert main([*args, "details", "independent"]) == 0
    assert main([*args, "run", "independent", "--dry-run"]) == 0
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        details = backend.dispatch("script.details", {"name": "independent"})
        assert details["exit_code"] == 0
        expected = (
            (("状态: 主页", "unknown", "状态配置不可用，无法确认"),) if requires else ()
        )
        assert details["readiness"] == expected
        backend.dispatch("script.start", {"name": "independent", "dry_run": True})
        deadline = time.monotonic() + 2
        status = backend.dispatch("script.status", {})
        while status["running"] and time.monotonic() < deadline:
            time.sleep(0.01)
            status = backend.dispatch("script.status", {})
        assert status["finish_reason"] == "completed"
    finally:
        backend.close()


def test_required_shared_config_read_failure_is_a_configuration_result(tmp_path):
    """实际依赖共享搜索时各入口返回配置失败并保留错误说明。"""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "assets" / "window-states.json").mkdir(parents=True)
    (tmp_path / "scripts" / "task.py").write_text(
        'TASK = {"name": "shared", "requires": {"searches": ["入口"]}}\n'
        'def run(ctx):\n    """模拟查找。"""\n    ctx.find("入口")\n'
    )
    args = ["--workspace", str(tmp_path)]
    assert main([*args, "details", "shared"]) == 2
    assert main([*args, "run", "shared", "--dry-run"]) == 2
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        assert backend.dispatch("script.details", {"name": "shared"})["exit_code"] == 2
        result = backend.dispatch("script.start", {"name": "shared", "dry_run": True})
        assert result["finish_reason"] == "configuration_failed"
        assert result["stderr"]
    finally:
        backend.close()
