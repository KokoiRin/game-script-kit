"""演示按实时界面状态选择 Python 分支，状态端口由运行会话提供。"""

from game_automation.task import Point

TASK = {"name": "conditional-screen-state-demo", "requires": {"states": ["主页"]}}


def run(ctx):
    """主页状态下点击示例点位，其他状态等待。"""
    if ctx.state() == "主页":
        ctx.click(Point(100, 200))
    else:
        ctx.wait(0.5)
