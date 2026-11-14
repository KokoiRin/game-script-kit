"""验证视觉靶场任务场景的纯状态转换。

这些测试只覆盖状态、时间、故障模式和事件真值；它不启动 HTTP 服务，
也不依赖 Star 的脚本执行模块或桌面 adapter。
"""

import pytest

from star_visual_lab.scenario import ScenarioActionError, TaskFlowScenario


class ManualClock:
    """提供场景测试可手动推进的单调时钟。"""

    def __init__(self) -> None:
        """从零开始记录测试时间。"""
        self.now = 0.0

    def __call__(self) -> float:
        """返回当前测试时间。"""
        return self.now

    def advance(self, seconds: float) -> None:
        """把测试时间向前推进指定秒数。"""
        self.now += seconds


def test_task_flow_scenario_completes_normal_flow_after_loading() -> None:
    """验证正常任务按主页、列表、加载、确认和完成顺序转换。"""
    clock = ManualClock()
    scenario = TaskFlowScenario(clock=clock, loading_delay_seconds=1.0)

    assert scenario.snapshot().state == "home"
    assert scenario.snapshot().available_actions == ("open_tasks",)

    scenario.perform("open_tasks")
    assert scenario.snapshot().state == "task_list"
    assert scenario.snapshot().available_actions == ("select_target",)

    scenario.perform("select_target")
    assert scenario.snapshot().state == "loading"
    assert scenario.snapshot().available_actions == ()

    clock.advance(0.9)
    assert scenario.snapshot().state == "loading"

    clock.advance(0.1)
    assert scenario.snapshot().state == "confirm"
    assert scenario.snapshot().available_actions == ("confirm_task",)

    scenario.perform("confirm_task")
    assert scenario.snapshot().state == "completed"
    assert scenario.snapshot().available_actions == ()

    assert [
        (event.kind, event.action, event.to_state) for event in scenario.events()
    ] == [
        ("reset", None, "home"),
        ("action", "open_tasks", "task_list"),
        ("action", "select_target", "loading"),
        ("transition", None, "confirm"),
        ("action", "confirm_task", "completed"),
    ]


def test_task_flow_scenario_rejects_action_not_allowed_in_current_state() -> None:
    """验证非法动作不会改变状态或追加事件。"""
    scenario = TaskFlowScenario()

    with pytest.raises(
        ScenarioActionError, match="action confirm_task is not allowed in state home"
    ):
        scenario.perform("confirm_task")

    assert scenario.snapshot().state == "home"
    assert len(scenario.events()) == 1


def test_task_flow_scenario_missing_target_hides_selection_action() -> None:
    """验证目标缺失模式进入列表后不能选择目标。"""
    scenario = TaskFlowScenario(mode="missing_target")

    scenario.perform("open_tasks")

    assert scenario.snapshot().state == "task_list"
    assert scenario.snapshot().available_actions == ()
    with pytest.raises(ScenarioActionError, match="select_target"):
        scenario.perform("select_target")


def test_task_flow_scenario_slow_mode_uses_longer_default_delay() -> None:
    """验证慢加载模式的默认延迟长于正常模式。"""
    normal = TaskFlowScenario(mode="normal")
    slow = TaskFlowScenario(mode="slow")

    assert (
        slow.snapshot().loading_delay_seconds > normal.snapshot().loading_delay_seconds
    )


def test_task_flow_scenario_reset_replaces_mode_delay_and_event_history() -> None:
    """验证重置会恢复主页并以新的 reset 事件重新开始。"""
    clock = ManualClock()
    scenario = TaskFlowScenario(clock=clock)
    scenario.perform("open_tasks")

    snapshot = scenario.reset(mode="slow", loading_delay_seconds=4.0)

    assert snapshot.state == "home"
    assert snapshot.mode == "slow"
    assert snapshot.loading_delay_seconds == 4.0
    assert snapshot.sequence == 1
    assert [(event.sequence, event.kind) for event in scenario.events()] == [
        (1, "reset")
    ]


@pytest.mark.parametrize("mode", ["unknown", "", "NORMAL"])
def test_task_flow_scenario_rejects_unknown_mode(mode: str) -> None:
    """验证场景拒绝未声明的故障模式。"""
    with pytest.raises(ValueError, match="unsupported visual lab mode"):
        TaskFlowScenario(mode=mode)


@pytest.mark.parametrize("delay", [-1.0, -0.1])
def test_task_flow_scenario_rejects_negative_loading_delay(delay: float) -> None:
    """验证加载延迟不能为负数。"""
    with pytest.raises(ValueError, match="loading delay"):
        TaskFlowScenario(loading_delay_seconds=delay)
