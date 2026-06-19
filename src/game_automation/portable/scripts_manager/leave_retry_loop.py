"""保存“离开/重来”图片轮询点击脚本。

本 module 只声明一份内置脚本数据；它不执行图片识别、不决定终止方式，
也不创建任何平台 adapter。
"""

from __future__ import annotations

from game_automation.portable.domain import (
    Click,
    If,
    ImageExists,
    ImageRef,
    ImageTarget,
    ImageTemplate,
    NamedImage,
    Repeat,
    ScreenWindow,
    Script,
    TargetCatalog,
    Wait,
)


LEAVE_RETRY_LOOP_TIMES = 86400
LEAVE_IMAGE_TEMPLATE = "assets/离开.png"
RETRY_IMAGE_TEMPLATE = "assets/重来.png"


LEAVE_RETRY_LOOP_SCRIPT = Script(
    name="click-leave-or-retry-loop",
    window=ScreenWindow(),
    resources=TargetCatalog(
        images=(
            NamedImage("离开", ImageTemplate(LEAVE_IMAGE_TEMPLATE)),
            NamedImage("重来", ImageTemplate(RETRY_IMAGE_TEMPLATE)),
        ),
    ),
    steps=(
        Repeat(
            times=LEAVE_RETRY_LOOP_TIMES,
            steps=(
                If(
                    condition=ImageExists(ImageRef("离开"), min_confidence=0.8),
                    then_steps=(
                        Click(ImageTarget(ImageRef("离开"), min_confidence=0.8)),
                    ),
                    else_steps=(
                        If(
                            condition=ImageExists(ImageRef("重来"), min_confidence=0.8),
                            then_steps=(
                                Click(ImageTarget(ImageRef("重来"), min_confidence=0.8)),
                            ),
                        ),
                    ),
                ),
                Wait(1),
            ),
        ),
    ),
)


def build_leave_retry_loop_script() -> Script:
    """返回用于持续轮询“离开/重来”图片并点击的命名脚本。"""
    return LEAVE_RETRY_LOOP_SCRIPT
