"""验证 macOS pointer adapter 的平台转换和错误包装。"""

import platform
from types import SimpleNamespace

import pytest

from game_automation.platform.macos.adapters import MacOSPointerDevice
from game_automation.portable.domain import Point


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

    def keyDown(self, key: str) -> None:
        """记录一次物理按键按下。"""
        self.calls.append(("keyDown", (key,), {}))

    def keyUp(self, key: str) -> None:
        """记录一次物理按键释放。"""
        self.calls.append(("keyUp", (key,), {}))


def test_macos_hotkey_presses_in_order_and_releases_in_reverse() -> None:
    """发送 Command+V 时，设备应先按 Command 再按 V，并反向释放两个键。"""
    backend = Backend()
    device = MacOSPointerDevice(backend=backend)  # type: ignore[arg-type]

    device.hotkey(("command", "v"))

    assert backend.calls == [
        ("keyDown", ("command",), {}),
        ("keyDown", ("v",), {}),
        ("keyUp", ("v",), {}),
        ("keyUp", ("command",), {}),
    ]


def test_macos_hotkey_releases_keys_after_backend_failsafe() -> None:
    """按 V 时触发安全中止，仍应释放可能按下的键，并恢复安全开关和报告失败。"""

    class InterruptedBackend(Backend):
        def keyDown(self, key: str) -> None:
            """模拟 V 已按下后发生桌面安全中止。"""
            super().keyDown(key)
            if key == "v":
                raise RuntimeError("failsafe triggered")

        def keyUp(self, key: str) -> None:
            """模拟安全开关仍打开时，普通 keyUp 也会被拒绝。"""
            if self.FAILSAFE:
                raise RuntimeError("failsafe triggered")
            super().keyUp(key)

    backend = InterruptedBackend()
    device = MacOSPointerDevice(backend=backend)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="operation failed"):
        device.hotkey(("command", "v"))

    assert backend.calls[-2:] == [
        ("keyUp", ("v",), {}),
        ("keyUp", ("command",), {}),
    ]
    assert backend.FAILSAFE is True


def test_macos_hotkey_attempts_remaining_releases_after_keyup_error() -> None:
    """释放 V 失败时仍应尝试释放 Command，并向调用方报告失败。"""

    class ReleaseFailureBackend(Backend):
        def keyUp(self, key: str) -> None:
            """模拟单个键的释放失败。"""
            super().keyUp(key)
            if key == "v":
                raise RuntimeError("release blocked")

    backend = ReleaseFailureBackend()
    device = MacOSPointerDevice(backend=backend)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="operation failed"):
        device.hotkey(("command", "v"))

    assert backend.calls[-1] == ("keyUp", ("command",), {})
    assert backend.FAILSAFE is True


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


def test_macos_adapter_rejects_non_darwin_without_injected_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
