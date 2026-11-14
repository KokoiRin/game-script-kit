"""演示通过上下文轮询颜色，有限等待到期向运行入口报告超时。"""

from game_automation.portable.domain import Color
from game_automation.task import Point

TASK = {"name": "wait-until-color-demo", "requires": {"colors": True}}


def run(ctx):
    """等待示例颜色出现，有限等待失败报告超时。"""
    ctx.wait_for(
        lambda: ctx.color(Point(50, 60)) == Color.from_hex("#102030"),
        timeout=1,
        interval=0.5,
    )
    ctx.click(Point(100, 200))
