"""演示按实时颜色选择 Python 分支，颜色读取通过任务上下文完成。"""

from game_automation.portable.domain import Color
from game_automation.task import Point

TASK = {"name": "conditional-color-demo", "requires": {"colors": True}}


def run(ctx):
    """按示例点位颜色选择点击位置及等待时长。"""
    if ctx.color(Point(50, 60)) == Color.from_hex("#102030"):
        ctx.click(Point(100, 200))
        ctx.wait(0.25)
    else:
        ctx.click(Point(300, 400))
        ctx.wait(0.5)
