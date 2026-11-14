"""演示等待命名界面状态，有限等待到期向运行入口报告超时。"""

from game_automation.task import Point

TASK = {"name": "wait-until-screen-state-demo", "requires": {"states": ["主页"]}}


def run(ctx):
    """主页状态出现后点击示例点位，有限等待失败报告超时。"""
    ctx.wait_state("主页", timeout=1, interval=0.5)
    ctx.click(Point(100, 200))
