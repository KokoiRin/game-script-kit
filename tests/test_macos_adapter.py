"""验证 macOS pointer adapter 的平台转换和错误包装。"""

import platform
from types import SimpleNamespace

import pytest

from game_automation.adapters.macos import MacOSPointerDevice
from game_automation.domain import Point


class Backend:
    def __init__(self) -> None:
        """初始化用于测试的 backend 调用记录。"""
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.FAILSAFE = False
        self.PAUSE = 0.0

    def moveTo(self, *args: object, **kwargs: object) -> None:
        """记录一次 moveTo 调用。"""
        self.calls.append(("moveTo", args, kwargs))

    def click(self, *args: object, **kwargs: object) -> None:
        """记录一次 click 调用。"""
        self.calls.append(("click", args, kwargs))

    def dragTo(self, *args: object, **kwargs: object) -> None:
        """记录一次 dragTo 调用。"""
        self.calls.append(("dragTo", args, kwargs))


def test_macos_adapter_translates_click_and_drag_with_left_button() -> None:
    """验证 macOS adapter 内部把点击和拖拽映射为左键行为。"""
    backend = Backend()
    device = MacOSPointerDevice(backend=backend)  # type: ignore[arg-type]

    device.click(Point(3, 4))
    device.drag_to(Point(5, 6), Point(7, 8), duration_seconds=0.5)

    assert backend.FAILSAFE is True
    assert backend.PAUSE == 0.05
    assert backend.calls == [
        ("click", (3, 4), {"button": "left"}),
        ("moveTo", (5, 6), {"duration": 0.0}),
        ("dragTo", (7, 8), {"duration": 0.5, "button": "left"}),
    ]


def test_macos_adapter_rejects_non_darwin_without_injected_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证未注入 backend 时，非 macOS 环境会被拒绝。"""
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    with pytest.raises(RuntimeError, match="requires Darwin"):
        MacOSPointerDevice()


def test_macos_adapter_wraps_backend_errors() -> None:
    """验证底层 backend 异常会被包装成 adapter setup 错误。"""
    backend = SimpleNamespace(
        FAILSAFE=False,
        PAUSE=0.0,
        click=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    device = MacOSPointerDevice(backend=backend)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="Accessibility permissions"):
        device.click(Point(1, 2))
