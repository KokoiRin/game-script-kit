"""验证执行核心与任务格式、平台装配之间的依赖方向。

行为从函数任务公开运行入口验证，源码检查仅保护本轮明确的 module 职责。
测试使用 dry-run，并检查旧步骤解释模块已删除。
"""

import ast
from pathlib import Path

from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain.task import FunctionTask


def test_execution_core_has_no_legacy_control_or_platform_imports():
    """核心只消费中立值与运行能力，任务格式由应用层负责。"""
    root = Path(__file__).resolve().parents[1]
    source = root / "src/game_automation/portable/engine/task_context.py"
    tree = ast.parse(source.read_text())
    forbidden_names = {
        "Script",
        "FunctionTask",
        "Step",
        "Repeat",
        "If",
        "WaitUntil",
        "ScriptRunner",
        "ActionRuntime",
    }
    forbidden_modules = (
        "game_automation.platform",
        "game_automation.portable.application",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (forbidden_names & {item.name for item in node.names})
            assert not (node.module or "").startswith(forbidden_modules)
            assert not (node.module or "").endswith(
                (".runner", ".action_runtime", ".condition_evaluator")
            )
        elif isinstance(node, ast.Import):
            assert not any(
                item.name.startswith(forbidden_modules) for item in node.names
            )


def test_function_task_runs_with_legacy_modules_removed(tmp_path):
    """公开函数入口只依赖直接执行核心和 Python 源码。"""
    task = FunctionTask(
        "独立核心",
        tmp_path / "task.py",
        'def run(ctx):\n    """执行一次模拟等待。"""\n    ctx.wait(0)\n',
    )

    result = run_script(task, dry_run=True)

    assert result.finish_reason == "completed"
    source_root = Path(__file__).resolve().parents[1] / "src/game_automation/portable"
    for module in (
        "domain/actions.py",
        "domain/conditions.py",
        "domain/script.py",
        "engine/runner.py",
        "engine/condition_evaluator.py",
        "application/config_script_loader.py",
    ):
        assert not (source_root / module).exists()
