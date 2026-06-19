"""验证离开/重来轮询脚本的公开结构。"""

from game_automation.portable.domain import Click, If, ImageExists, ImageRef, ImageTarget, Repeat, Wait
from game_automation.portable.scripts_manager.leave_retry_loop import (
    LEAVE_IMAGE_TEMPLATE,
    LEAVE_RETRY_LOOP_TIMES,
    RETRY_IMAGE_TEMPLATE,
    build_leave_retry_loop_script,
)


def test_leave_retry_loop_uses_named_image_templates() -> None:
    """验证脚本把离开和重来图片注册成可读别名。"""
    script = build_leave_retry_loop_script()

    assert script.resources.resolve_image(ImageRef("离开")).path == LEAVE_IMAGE_TEMPLATE
    assert script.resources.resolve_image(ImageRef("重来")).path == RETRY_IMAGE_TEMPLATE


def test_leave_retry_loop_checks_leave_then_retry_once_per_second() -> None:
    """验证脚本每轮优先点击离开，否则点击重来，并等待一秒。"""
    script = build_leave_retry_loop_script()

    loop = script.steps[0]
    assert isinstance(loop, Repeat)
    assert loop.times == LEAVE_RETRY_LOOP_TIMES
    assert len(loop.steps) == 2

    leave_branch = loop.steps[0]
    assert isinstance(leave_branch, If)
    assert leave_branch.condition == ImageExists(ImageRef("离开"), min_confidence=0.8)
    assert leave_branch.then_steps == (
        Click(ImageTarget(ImageRef("离开"), min_confidence=0.8)),
    )

    retry_branch = leave_branch.else_steps[0]
    assert isinstance(retry_branch, If)
    assert retry_branch.condition == ImageExists(ImageRef("重来"), min_confidence=0.8)
    assert retry_branch.then_steps == (
        Click(ImageTarget(ImageRef("重来"), min_confidence=0.8)),
    )
    assert retry_branch.else_steps == ()
    assert loop.steps[1] == Wait(1)
