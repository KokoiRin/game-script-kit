"""验证坐标记录工具的真实 adapter 包装行为。"""

from __future__ import annotations

from collections import namedtuple
from types import SimpleNamespace

import pytest

from game_automation.platform.desktop.adapters import (
    PyAutoGuiPointerPositionReader,
    TerminalKeyStateReader,
)
from game_automation.platform.local_desktop.entrypoints.cli import main
from game_automation.portable.domain import Point


@pytest.mark.parametrize(
    "position",
    [(12, 34), namedtuple("Position", "x y")(12, 34), (12.9, 34.8)],
    ids=["tuple", "pyautogui-namedtuple", "integer-conversion"],
)
def test_pyautogui_pointer_reader_returns_point_from_tuple(position) -> None:
    """验证普通元组与 PyAutoGUI 的具名元组共用解包，并保持整数转换。"""
    backend = SimpleNamespace(position=lambda: position)

    assert PyAutoGuiPointerPositionReader(backend=backend).current_position() == Point(
        12, 34
    )


def test_pyautogui_pointer_reader_wraps_errors() -> None:
    """验证鼠标坐标读取错误会被包装成 setup 错误。"""
    backend = SimpleNamespace(
        position=lambda: (_ for _ in ()).throw(RuntimeError("blocked"))
    )

    with pytest.raises(RuntimeError, match="pointer position"):
        PyAutoGuiPointerPositionReader(backend=backend).current_position()


def test_terminal_key_reader_requires_interactive_terminal() -> None:
    """验证终端按键 adapter 会报告非交互终端限制。"""
    stream = SimpleNamespace(isatty=lambda: False)

    with pytest.raises(RuntimeError, match="interactive terminal"):
        TerminalKeyStateReader(stream=stream)


def test_coordinate_recorder_cli_help_does_not_load_platform_dependencies(
    capsys,
) -> None:
    """验证 CLI help 不会加载真实鼠标或键盘依赖。"""
    with pytest.raises(SystemExit) as exc:
        main(["recorder", "--help"])

    assert exc.value.code == 0
    assert "Seconds between coordinate prints" in capsys.readouterr().out
