"""统一解析任务声明的唯一系统窗口，供运行和控制台关联复用。

只负责选窗及身份绑定，不创建截图源或发送输入。
"""

from game_automation.platform.macos.adapters.window_identity import BoundWindow
from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.preparation.models import DesktopWindow


def resolve_task_window(target, *, backend=None, binding_factory=BoundWindow):
    """按任务声明校验唯一标题与固定尺寸并绑定同一系统窗口。"""
    if backend is None:
        from game_automation.platform.macos.adapters.accessibility_window_backend import (
            MacOSAccessibilityWindowBackend,
        )

        backend = MacOSAccessibilityWindowBackend()
    matches = [
        w
        for w in backend.list_windows(target.application)
        if w.title == target.window_title
    ]
    if len(matches) != 1:
        raise WindowCaptureError("目标窗口标题必须唯一且可见，请打开指定游戏窗口")
    selected = matches[0]
    if (selected.rect.width, selected.rect.height) != (target.width, target.height):
        raise ValueError("目标窗口尺寸与脚本素材不符，请恢复窗口尺寸后重试")
    window = DesktopWindow(
        f"{selected.pid}:{selected.window_number}",
        target.application,
        selected.title,
        selected.rect,
    )
    return window, binding_factory(window)


def resolve_companion_window(target):
    """复用实际运行选窗规则，返回控制台关联所需的具体系统身份。"""
    from game_automation.portable.application.runtime_ports import RuntimeWindowIdentity

    window, binding = resolve_task_window(target)
    return RuntimeWindowIdentity(int(window.id.split(":", 1)[0]), binding.number)
