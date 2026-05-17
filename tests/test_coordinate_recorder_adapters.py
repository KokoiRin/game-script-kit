"""验证坐标记录工具的真实 adapter 包装行为。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from game_automation.adapters.desktop import (
    PyAutoGuiPointerPositionReader,
    TerminalKeyStateReader,
)
from game_automation.coordinate_recorder_cli import main
from game_automation.core import AdapterSetupError
from game_automation.domain import Point


def test_pyautogui_pointer_reader_returns_point_from_tuple() -> None:
    """验证 pyautogui tuple 坐标会转换为 Point。"""
    backend = SimpleNamespace(position=lambda: (12, 34))

    assert PyAutoGuiPointerPositionReader(backend=backend).current_position() == Point(12, 34)


def test_pyautogui_pointer_reader_wraps_errors() -> None:
    """验证鼠标坐标读取错误会被包装成 setup 错误。"""
    backend = SimpleNamespace(
        position=lambda: (_ for _ in ()).throw(RuntimeError("blocked"))
    )

    with pytest.raises(AdapterSetupError, match="pointer position"):
        PyAutoGuiPointerPositionReader(backend=backend).current_position()


def test_terminal_key_reader_requires_interactive_terminal() -> None:
    """验证终端按键 adapter 会报告非交互终端限制。"""
    stream = SimpleNamespace(isatty=lambda: False)

    with pytest.raises(AdapterSetupError, match="interactive terminal"):
        TerminalKeyStateReader(stream=stream)


def test_coordinate_recorder_cli_help_does_not_load_platform_dependencies(capsys) -> None:
    """验证 CLI help 不会加载真实鼠标或键盘依赖。"""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    assert "Record screen coordinates" in capsys.readouterr().out
