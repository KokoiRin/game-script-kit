"""演示通过命名图片定位并提交点击，定位由任务上下文完成。"""

TASK = {
    "name": "click-image-demo",
    "resources": {"images": {"开始": "start.png"}},
}


def run(ctx):
    """在图片匹配的矩形中心点击一次。"""
    ctx.click_image("开始")
