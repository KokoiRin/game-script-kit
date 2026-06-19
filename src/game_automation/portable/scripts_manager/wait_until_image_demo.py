"""保存用于验证图片条件等待行为的命名脚本。

本 module 只声明一份内置脚本数据；它不执行图像匹配、不推进等待时间，
也不处理超时错误。
"""

from __future__ import annotations

from game_automation.portable.domain import Click, ImageExists, ImageTemplate, Point, ScreenWindow, Script, WaitUntil


WAIT_UNTIL_IMAGE_DEMO_TEMPLATE = "assets/start.png"


WAIT_UNTIL_IMAGE_DEMO_SCRIPT = Script(
    name="wait-until-image-demo",
    window=ScreenWindow(),
    steps=(
        WaitUntil(
            condition=ImageExists(ImageTemplate(WAIT_UNTIL_IMAGE_DEMO_TEMPLATE)),
            timeout_seconds=1,
            interval_seconds=0.5,
        ),
        Click(Point(100, 200)),
    ),
)


def build_wait_until_image_demo_script() -> Script:
    """返回用于 dry-run 验证图片条件等待的命名脚本。"""
    return WAIT_UNTIL_IMAGE_DEMO_SCRIPT
