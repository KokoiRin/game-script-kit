"""演示用 Python 有限循环重复动作，上下文负责输入及取消。"""

from game_automation.task import Point

TASK = {"name": "repeat-demo"}


def run(ctx):
    """等待后重复五次点击与等待。"""
    ctx.wait(2)
    for _ in range(5):
        ctx.click(Point(120, 180))
        ctx.wait(1)
