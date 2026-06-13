"""保存基于已记录坐标的命名点击脚本。

本 module 只声明一份内置脚本数据；它不执行脚本，也不包含坐标记录流程。
"""

from __future__ import annotations

from game_automation.domain import Click, Point, ScreenWindow, Script, Wait


RECORDED_CLICKS_SCRIPT = Script(
    name="recorded-clicks",
    window=ScreenWindow(),
    steps=(
        Wait(3),
        Click(Point(242, 92)),
        Wait(3),
        Click(Point(736, 323)),
        Wait(10),
        Click(Point(741, 400)),
    ),
)


def build_recorded_clicks_script() -> Script:
    """返回按已记录坐标顺序点击的命名脚本。"""
    return RECORDED_CLICKS_SCRIPT
