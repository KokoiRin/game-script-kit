"""验证本地控制 UI 复用的应用层 interface。

这些测试覆盖 UI 和 CLI 之外的 application seam：脚本查找、运行结果捕获、
固定测试任务白名单。它不测试 HTTP 细节，也不直接绑定 engine 内部实现。
"""

import subprocess

from game_automation.portable.application.local_control import LocalControlApplication, PROJECT_ROOT


def test_local_control_project_root_points_to_repository_root() -> None:
    """验证 UI 测试按钮在项目根目录运行 pytest。"""
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "tests").is_dir()


def test_local_control_runs_named_script_and_captures_dry_run_output() -> None:
    """验证 UI 用例可以按名称 dry-run 脚本并返回可展示输出。"""
    app = LocalControlApplication()

    result = app.run_named_script(
        "conditional-color-demo",
        dry_run=True,
        dry_run_color="#102030",
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "click Point(x=100, y=200)",
        "wait 0.25s",
    ]


def test_local_control_rejects_unknown_test_task_without_running_command() -> None:
    """验证 UI 只能触发白名单测试任务。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((command, cwd))
        raise AssertionError("unknown test task must not execute a command")

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("shell")

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == "unknown test task: shell\n"
    assert commands == []


def test_local_control_runs_whitelisted_test_task() -> None:
    """验证 UI 测试按钮只通过固定任务执行命令。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((tuple(command), cwd))
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="2 passed\n",
            stderr="",
        )

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("all")

    assert result.exit_code == 0
    assert result.stdout == "2 passed\n"
    assert result.stderr == ""
    assert len(commands) == 1
    assert commands[0][0][-2:] == ("-m", "pytest")
