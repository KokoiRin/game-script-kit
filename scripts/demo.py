"""演示点击、拖拽与等待，动作通过本次任务上下文执行。"""

from game_automation.task import Point

TASK = {"name": "demo"}


def run(ctx):
    """以任务窗口为基准演示一次点击和四百毫秒拖拽，最后等待一百毫秒。"""
    ctx.click(Point(300, 300))
    ctx.drag(Point(300, 300), Point(460, 360), duration=0.4)
    ctx.wait(0.1)
