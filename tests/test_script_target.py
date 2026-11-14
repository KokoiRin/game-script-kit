"""验证任务目标只接受原生窗口，真实运行不回退到屏幕坐标。"""

from dataclasses import replace

import pytest

from game_automation.portable.application.function_task_loader import (
    parse_function_task_source,
)
from game_automation.portable.application.task_run import run_task
from game_automation.portable.domain.task import TaskTarget
from tests.support.function_tasks import function_task


def target(**overrides):
    """给出带显式原生后端的目标。"""
    values = {
        "application": "Example",
        "window_title": "Target window",
        "width": 80,
        "height": 60,
        "backend": "macos-window",
    }
    values.update(overrides)
    return TaskTarget(**values)


@pytest.mark.parametrize(
    "bad",
    [
        {"application": ""},
        {"window_title": " "},
        {"width": True},
        {"height": 0},
        {"width": 80.0},
        {"backend": "desktop"},
    ],
)
def test_target_rejects_incomplete_or_non_native_values(bad):
    """字段必须完整，后端只能是原生窗口。"""
    with pytest.raises(ValueError):
        target(**bad)


def test_python_metadata_requires_explicit_native_backend(tmp_path):
    """省略 backend 的目标声明不能再默认成桌面坐标。"""
    source = """
TASK = {
    "name": "sample",
    "target": {
        "application": "Example",
        "window_title": "Target window",
        "width": 80,
        "height": 60,
    },
}
def run(ctx):
    pass
"""
    with pytest.raises(ValueError, match="backend"):
        parse_function_task_source(
            source, path=tmp_path / "sample.py", asset_root=tmp_path
        )


def test_real_run_without_target_does_not_touch_desktop():
    """未声明原生目标时，真实运行在打开任何设备前失败。"""
    task = function_task("plain", "ctx.click(Point(1, 2))")
    result = run_task(task, dry_run=False)
    assert result.exit_code == 2
    assert result.finish_reason == "configuration_failed"
    assert "macos-window" in result.error_message


def test_dry_run_ignores_missing_native_target():
    """dry-run 不需要活动窗口，也不读取桌面。"""
    task = function_task("plain", "ctx.click(Point(1, 2))")
    result = run_task(task, dry_run=True)
    assert result.finish_reason == "completed"


def test_declared_native_target_can_change_backend():
    """后台试验后端与前台原生后端都算显式窗口目标。"""
    foreground = target()
    background = replace(foreground, backend="macos-window-background")
    assert foreground.uses_native_window
    assert background.uses_native_window
