"""演示等待命名图片出现，有限等待到期向运行入口报告超时。"""

from game_automation.task import Point

TASK = {
    "name": "wait-until-image-demo",
    "resources": {"images": {"开始": "start.png"}},
}


def run(ctx):
    """等待开始图片后点击示例点位，有限等待失败报告超时。"""
    ctx.wait_image("开始", timeout=1, interval=0.5)
    ctx.click(Point(100, 200))
