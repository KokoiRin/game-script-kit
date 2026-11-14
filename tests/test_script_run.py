"""验证应用层函数任务运行装配及结果归一化。

这些测试直接覆盖 portable run_task 的 interface，真实平台 adapter 通过工厂注入。
"""

from pathlib import Path

import pytest

from game_automation.portable.application.project_tasks import (
    load_project_task_catalog,
)
from game_automation.portable.application.task_run import run_task
from game_automation.portable.domain import (
    ImageTarget,
    ImageTemplate,
    Point,
    UnboundWindow,
)
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from tests.support.function_tasks import function_task

_EXAMPLES = load_project_task_catalog(Path(__file__).resolve().parents[1])
CONDITIONAL_COLOR_DEMO_SCRIPT = _EXAMPLES.get("conditional-color-demo")
WAIT_UNTIL_COLOR_DEMO_SCRIPT = _EXAMPLES.get("wait-until-color-demo")


IMAGE_TEMPLATE_PATH = "assets/start.png"


class FakeRunLogger:
    """收集脚本运行测试中的运行日志。"""

    def __init__(self) -> None:
        """初始化日志列表。"""
        self.messages: list[str] = []
        self.events = []

    def log(self, message: str) -> None:
        """记录一条运行日志。"""
        self.messages.append(message)

    def log_event(self, event) -> None:
        """记录一条结构化运行事件。"""
        self.events.append(event)


def test_hotkey_run_logs_performed_keys() -> None:
    """组合键执行成功后，运行日志应给出实际执行的键组合，供 CLI/UI 展示。"""
    logger = FakeRunLogger()
    script = function_task(
        "paste", "ctx.hotkey(*('command', 'v'))", window=UnboundWindow()
    )

    result = run_task(script, dry_run=True, logger=logger, emit_step_events=True)

    assert result.finish_reason == "completed"
    performed = [
        event for event in logger.events if event.event_type == "hotkey_performed"
    ]
    assert len(performed) == 1
    assert performed[0].details == {"keys": "command+v"}


def build_plain_action_script() -> FunctionTask:
    """构造不依赖个人坐标和素材的通用动作测试脚本。"""
    return function_task(
        "plain-actions-test",
        "ctx.wait(0.25)\n"
        "ctx.click(Point(10, 20))\n"
        "ctx.wait(0.5)\n"
        "ctx.click(Point(30, 40))",
        window=UnboundWindow(),
    )


def build_wait_until_image_script() -> FunctionTask:
    """构造应用层测试用图片等待脚本。"""
    return function_task(
        "wait-until-image-test",
        f"ctx.wait_for(lambda: ctx.find({ImageTemplate(IMAGE_TEMPLATE_PATH)!r}, min_confidence={None!r}) is not None, timeout={1!r}, interval={0.5!r})\nctx.click({Point(100, 200)!r})",
        window=UnboundWindow(),
        templates=(ImageTemplate(IMAGE_TEMPLATE_PATH),),
    )


def build_click_image_script() -> FunctionTask:
    """构造应用层测试用图片目标点击脚本。"""
    return function_task(
        "click-image-test",
        f"ctx.click({ImageTarget(ImageTemplate(IMAGE_TEMPLATE_PATH))!r})",
        window=UnboundWindow(),
        templates=(ImageTemplate(IMAGE_TEMPLATE_PATH),),
    )


def build_screen_state_branch_script() -> FunctionTask:
    """构造应用层测试用界面状态分支脚本。"""

    return function_task(
        "screen-state-branch-test",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(Point(100, 200))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=UnboundWindow(),
        requires=TaskRequirements(states=("主页",)),
    )


def test_run_task_dry_run_prints_plain_script_operations(capsys) -> None:
    """验证 dry-run 会使用打印 adapter 执行普通脚本。"""
    result = run_task(build_plain_action_script(), dry_run=True)

    output = capsys.readouterr().out
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert output.splitlines() == [
        "wait 0.25s",
        "click Point(x=10, y=20)",
        "wait 0.5s",
        "click Point(x=30, y=40)",
    ]


def test_run_task_reports_invalid_dry_run_color_without_running(capsys) -> None:
    """验证颜色配置非法时应用层返回配置错误。"""
    result = run_task(
        CONDITIONAL_COLOR_DEMO_SCRIPT,
        dry_run=True,
        dry_run_color="bad",
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 2
    assert result.finish_reason == "configuration_failed"
    assert result.error_message == (
        "task run configuration failed: color must match #[0-9A-Fa-f]{6}"
    )


def test_run_task_reports_unhandled_color_wait_timeout(capsys) -> None:
    """直接等待到期时应用层返回 timed_out，并停止后续动作。"""
    result = run_task(WAIT_UNTIL_COLOR_DEMO_SCRIPT, dry_run=True)

    captured = capsys.readouterr()
    waits = [
        float(line.removeprefix("wait ").removesuffix("s"))
        for line in captured.out.splitlines()
    ]
    assert waits == pytest.approx([0.5, 0.5], abs=0.01)
    assert result.exit_code == 1
    assert result.finish_reason == "timed_out"
    assert "timed out" in result.error_message


def test_run_task_dry_run_wait_until_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片条件可通过配置的模板匹配成功。"""
    result = run_task(
        build_wait_until_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert captured.out == "click Point(x=100, y=200)\n"


def test_run_task_logs_screen_state_condition_when_logger_is_configured() -> None:
    """状态查询通过公开操作事件暴露成功结果。"""
    logger = FakeRunLogger()

    result = run_task(
        build_screen_state_branch_script(),
        dry_run=True,
        dry_run_screen_state="主页",
        logger=logger,
        emit_step_events=True,
    )

    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    observations = [
        event
        for event in logger.events
        if event.event_type == "step_succeeded" and event.step_type == "Observe"
    ]
    assert len(observations) == 1
    assert observations[0].status == "succeeded"


def test_run_task_dry_run_reports_unhandled_image_wait_timeout(capsys) -> None:
    """模拟画面缺少图片时直接等待返回 timed_out。"""
    result = run_task(build_wait_until_image_script(), dry_run=True)

    captured = capsys.readouterr()
    waits = [
        float(line.removeprefix("wait ").removesuffix("s"))
        for line in captured.out.splitlines()
    ]
    assert waits == pytest.approx([0.5, 0.5], abs=0.01)
    assert result.exit_code == 1
    assert result.finish_reason == "timed_out"
    assert "timed out" in result.error_message


def test_run_task_dry_run_click_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片目标点击可通过配置的模板匹配成功。"""
    result = run_task(
        build_click_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert captured.out == "click Point(x=0, y=0)\n"


def test_run_task_dry_run_click_image_stops_normally_when_target_is_missing(
    capsys,
) -> None:
    """验证 dry-run 未配置图片时图片目标点击正常停止。"""
    result = run_task(build_click_image_script(), dry_run=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 0
    assert result.finish_reason == "stopped_unmet_condition"
    assert result.error_message is None


def test_run_task_emits_step_events_when_enabled(capsys) -> None:
    """验证应用层可按需启用结构化步骤事件，不影响默认输出策略。"""
    logger = FakeRunLogger()

    result = run_task(
        build_click_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
        logger=logger,
        emit_step_events=True,
    )

    captured = capsys.readouterr()
    assert captured.out == "click Point(x=0, y=0)\n"
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert [event.event_type for event in logger.events] == [
        "run_started",
        "step_started",
        "image_target_resolved",
        "click_resolved",
        "click_performed",
        "step_succeeded",
        "run_finished",
    ]
    assert logger.events[1].step_path == "1"
    assert logger.events[2].details["point"] == "Point(x=0, y=0)"


def test_run_task_dry_run_screen_state_condition_uses_fixed_state(capsys) -> None:
    """验证 dry-run 界面状态条件可使用固定状态结果。"""
    result = run_task(
        build_screen_state_branch_script(),
        dry_run=True,
        dry_run_screen_state="主页",
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.error_message is None
    assert captured.out == "click Point(x=100, y=200)\n"
