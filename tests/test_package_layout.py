"""验证 portable/platform 目录布局。

这些测试保护迁移平台时的导航约定：跨平台核心看 portable，平台入口看 platform。
"""

from game_automation.portable.domain.task import FunctionTask
from game_automation.task import TaskContext


def test_portable_core_imports_are_available() -> None:
    """验证核心类型从 portable 路径导出。"""
    assert FunctionTask.__name__ == "FunctionTask"
    assert TaskContext.__name__ == "TaskContext"


def test_platform_entrypoint_is_importable_from_new_location() -> None:
    """验证本机桌面入口位于 platform 目录。"""
    from game_automation.platform.local_desktop.entrypoints.cli import main

    assert callable(main)
