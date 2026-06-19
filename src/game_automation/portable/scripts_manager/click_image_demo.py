"""保存用于验证图片目标点击行为的命名脚本。

本 module 只声明一份内置脚本数据；它不执行图像匹配、不解析点击坐标，
也不创建平台 adapter。
"""

from __future__ import annotations

from game_automation.portable.domain import (
    Click,
    ImageTarget,
    ImageTemplate,
    ScreenWindow,
    Script,
)


CLICK_IMAGE_DEMO_TEMPLATE = "assets/start.png"


CLICK_IMAGE_DEMO_SCRIPT = Script(
    name="click-image-demo",
    window=ScreenWindow(),
    steps=(Click(ImageTarget(ImageTemplate(CLICK_IMAGE_DEMO_TEMPLATE))),),
)


def build_click_image_demo_script() -> Script:
    """返回用于 dry-run 验证图片目标点击的命名脚本。"""
    return CLICK_IMAGE_DEMO_SCRIPT
