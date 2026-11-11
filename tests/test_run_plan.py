"""验证一轮脚本计划的 application 编排语义。

这些测试只覆盖计划顺序、停止策略和结果聚合；它不测试 CLI 参数解析，
也不绑定单个脚本 runner 的内部实现。
"""

import pytest

from game_automation.portable.application.run_plan import (
    ScriptPlanItem,
    ScriptPlanScriptResult,
    run_script_plan,
)
from game_automation.portable.domain import Script, ScreenWindow, Wait


def test_run_script_plan_runs_items_in_order() -> None:
    """验证计划按用户给定顺序执行脚本。"""
    calls: list[str] = []
    items = (
        ScriptPlanItem("first", Script("first", ScreenWindow(), (Wait(0),))),
        ScriptPlanItem("second", Script("second", ScreenWindow(), (Wait(0),))),
    )

    result = run_script_plan(
        items,
        run_item=lambda item: _record_success(item.name, calls),
    )

    assert calls == ["first", "second"]
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert [(item.script_name, item.exit_code) for item in result.items] == [
        ("first", 0),
        ("second", 0),
    ]


def test_run_script_plan_stops_after_first_error_by_default() -> None:
    """验证计划默认在首个失败脚本后停止。"""
    calls: list[str] = []
    items = (
        ScriptPlanItem("first", Script("first", ScreenWindow(), (Wait(0),))),
        ScriptPlanItem("second", Script("second", ScreenWindow(), (Wait(0),))),
    )

    result = run_script_plan(
        items,
        run_item=lambda item: _fail_first(item.name, calls),
    )

    assert calls == ["first"]
    assert result.exit_code == 1
    assert result.finish_reason == "failed"
    assert [(item.script_name, item.exit_code) for item in result.items] == [("first", 1)]


def test_run_script_plan_can_continue_after_error() -> None:
    """验证 continue_on_error 会继续执行并保留第一个失败退出码。"""
    calls: list[str] = []
    items = (
        ScriptPlanItem("first", Script("first", ScreenWindow(), (Wait(0),))),
        ScriptPlanItem("second", Script("second", ScreenWindow(), (Wait(0),))),
    )

    result = run_script_plan(
        items,
        run_item=lambda item: _fail_first(item.name, calls),
        continue_on_error=True,
    )

    assert calls == ["first", "second"]
    assert result.exit_code == 1
    assert result.finish_reason == "failed"
    assert [(item.script_name, item.exit_code) for item in result.items] == [
        ("first", 1),
        ("second", 0),
    ]


def test_run_script_plan_stops_after_unmet_condition() -> None:
    """验证脚本正常停止但未完成时计划不会误报整轮完成。"""
    calls: list[str] = []
    items = (
        ScriptPlanItem("first", Script("first", ScreenWindow(), (Wait(0),))),
        ScriptPlanItem("second", Script("second", ScreenWindow(), (Wait(0),))),
    )

    result = run_script_plan(
        items,
        run_item=lambda item: _stop_first(item.name, calls),
    )

    assert calls == ["first"]
    assert result.exit_code == 0
    assert result.finish_reason == "stopped_unmet_condition"
    assert [(item.script_name, item.finish_reason) for item in result.items] == [
        ("first", "stopped_unmet_condition")
    ]


@pytest.mark.parametrize("continue_on_error,prior_failure", [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize("cancel_exit_code", [0, 130])
def test_run_script_plan_cancellation_ends_plan(continue_on_error, prior_failure, cancel_exit_code) -> None:
    """取消结果应终止计划并成为整体结果，不受继续策略、先前失败或退出码是否为零影响。"""
    names = ("failed", "cancelled", "never-run") if prior_failure else ("cancelled", "never-run")
    items = tuple(ScriptPlanItem(name, Script(name, ScreenWindow(), (Wait(0),))) for name in names)
    calls = []

    def run_item(item):
        """返回已发生的普通失败或用户取消，并记录是否误启动了后续项。"""
        calls.append(item.name)
        if item.name == "failed":
            return ScriptPlanScriptResult(1, "failed", stderr="earlier error")
        if item.name == "cancelled":
            return ScriptPlanScriptResult(cancel_exit_code, "cancelled", stdout="stopping", stderr="user cancelled")
        return ScriptPlanScriptResult(0)

    result = run_script_plan(items, run_item=run_item, continue_on_error=continue_on_error)

    assert calls == list(names[:-1])
    assert result.exit_code == cancel_exit_code
    assert result.finish_reason == "cancelled"
    assert [item.script_name for item in result.items] == calls
    assert result.items[-1].finish_reason == "cancelled"
    assert result.items[-1].stdout == "stopping"
    assert result.items[-1].stderr == "user cancelled"


def _record_success(script_name: str, calls: list[str]) -> ScriptPlanScriptResult:
    """记录脚本名称并返回成功结果。"""
    calls.append(script_name)
    return ScriptPlanScriptResult(exit_code=0, finish_reason="completed", stdout=f"{script_name}\n")


def _fail_first(script_name: str, calls: list[str]) -> ScriptPlanScriptResult:
    """让 first 失败，其他脚本成功。"""
    calls.append(script_name)
    if script_name == "first":
        return ScriptPlanScriptResult(exit_code=1, finish_reason="failed", stderr="boom\n")
    return ScriptPlanScriptResult(exit_code=0, finish_reason="completed", stdout=f"{script_name}\n")


def _stop_first(script_name: str, calls: list[str]) -> ScriptPlanScriptResult:
    """让 first 因条件未满足停止，其他脚本成功。"""
    calls.append(script_name)
    if script_name == "first":
        return ScriptPlanScriptResult(exit_code=0, finish_reason="stopped_unmet_condition")
    return ScriptPlanScriptResult(exit_code=0, finish_reason="completed")
