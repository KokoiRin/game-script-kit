"""验证文件脚本目标绑定与原生同步/后台路径，不访问真实桌面。"""

from dataclasses import replace

import pytest

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.ports import FocusedApplicationWindow
from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain import Point, Rect, ScreenWindow
from game_automation.portable.domain.task import ScriptTarget
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
from tests.support.function_tasks import function_task


def target():
    """给出通用测试应用的预期逻辑尺寸。"""
    return ScriptTarget("Example", "Target window", 80, 60)


@pytest.mark.parametrize(
    "bad",
    [
        {"application": ""},
        {"window_title": " "},
        {"width": True},
        {"height": 0},
        {"width": 80.0},
    ],
)
def test_target_rejects_incomplete_or_ambiguous_values(bad):
    """字段必须完整且尺寸是正整数。"""
    with pytest.raises(ValueError):
        replace(target(), **bad)


def test_python_metadata_loads_target_and_defaults_to_screen_coordinates(tmp_path):
    """目标声明复用 Python 文件元信息，省略声明时使用屏幕坐标。"""
    from game_automation.portable.application.function_task_loader import (
        parse_function_task_source,
    )

    metadata = {
        "name": "sample",
        "target": {
            "application": "Example",
            "window_title": "Target window",
            "width": 80,
            "height": 60,
        },
    }

    def parse():
        """按当前字面量构造静态任务。"""
        return parse_function_task_source(
            f"TASK = {metadata!r}\ndef run(ctx): pass\n",
            path=tmp_path / "sample.py",
            asset_root=tmp_path,
        )

    assert parse().target == target()
    del metadata["target"]
    assert parse().target is None
    metadata["target"] = {"application": "Example"}
    with pytest.raises(ValueError):
        parse()


class Environment:
    """记录激活、选窗和输入设备事件。"""

    def __init__(self, size=(80, 60)):
        """提供有屏幕偏移的假窗口。"""
        self.events = []
        self.size = size

    def activate(self, application):
        """记录激活，保持无设备副作用。"""
        self.events.append(("activate", application))

    def focus_window(self, application, title):
        """返回移动后的窗口位置。"""
        self.events.append(("focus", application, title))
        return FocusedApplicationWindow(title, Rect(120, 220, *self.size))

    def click(self, point):
        """记录最终屏幕坐标。"""
        self.events.append(("click", point))

    def wait(self, seconds):
        """不进行真实等待。"""


def sample():
    """构造含目标声明的最小脚本。"""
    return function_task(
        "sample", "ctx.click(Point(5, 6))", window=ScreenWindow(), target=target()
    )


def test_declared_window_maps_relative_clicks_after_activation():
    """每次运行根据窗口当前原点换算，而非缓存旧屏幕坐标。"""
    env = Environment()
    result = run_script(
        sample(),
        dry_run=False,
        real_application_activator_factory=lambda: env,
        real_application_window_controller_factory=lambda: env,
        real_device_factory=lambda: env,
    )
    assert result.finish_reason == "completed"
    assert env.events == [
        ("activate", "Example"),
        ("focus", "Example", "Target window"),
        ("click", Point(125, 226)),
    ]


def test_wrong_size_never_creates_input_device():
    """不适配的布局在创建设备或点击前失败。"""
    env = Environment((81, 60))

    def forbidden():
        """尺寸不符时不允许初始化输入。"""
        raise AssertionError("device initialized")

    result = run_script(
        sample(),
        dry_run=False,
        real_application_activator_factory=lambda: env,
        real_application_window_controller_factory=lambda: env,
        real_device_factory=forbidden,
    )
    assert (
        result.finish_reason == "configuration_failed"
        and "尺寸" in result.error_message
    )


def test_dry_run_never_uses_declared_target_desktop():
    """模拟运行保留无桌面副作用。"""

    def forbidden():
        """模拟时不允许调用真实环境工厂。"""
        raise AssertionError("desktop touched")

    result = run_script(
        sample(),
        dry_run=True,
        real_application_activator_factory=forbidden,
        real_application_window_controller_factory=forbidden,
    )
    assert result.finish_reason == "completed"


@pytest.mark.parametrize("background", [False, True])
def test_control_paths_honor_declared_target(tmp_path, background):
    """原生所用后台路径与同步入口都传递现有选窗工厂。"""
    env = Environment()
    app = LocalControlApplication(
        catalog=ScriptCatalog((sample(),)),
        project_root=tmp_path,
        real_application_activator_factory=lambda: env,
        real_application_window_controller_factory=lambda: env,
        real_device_factory=lambda: env,
    )
    if background:
        app.start_named_script("sample", dry_run=False)
        assert app.wait_for_script_stop(2)
        result = app.current_script_run()
    else:
        result = app.run_named_script("sample", dry_run=False)
    assert result.finish_reason == "completed" and env.events[-1] == (
        "click",
        Point(125, 226),
    )
