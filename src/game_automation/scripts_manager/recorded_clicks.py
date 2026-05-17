"""保存基于已记录坐标的命名点击脚本。"""

from __future__ import annotations

from game_automation.domain import Click, Point, ScreenWindow, Script, Wait


RECORDED_CLICKS_SCRIPT = Script(
    name="recorded-clicks",
    window=ScreenWindow(),
    actions=(
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
