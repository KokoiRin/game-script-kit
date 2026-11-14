"""star 命令行入口。

本 module 负责解析命令行参数、选择本地工作区并打印用户可见结果；任务运行和
本地 UI 委托应用/入口编排层，recorder 子命令保留终端工具组装但不解释任务步骤。
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from game_automation.platform.local_desktop.composition import (
    run_task_on_local_desktop,
)
from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    image_asset_root,
)
from game_automation.portable.application.project_tasks import (
    ProjectTaskCatalogResult,
    load_project_task_catalog_result,
)
from game_automation.portable.application.run_plan import (
    TaskPlanItem,
    TaskPlanItemResult,
    TaskPlanResult,
    TaskPlanRunResult,
    run_task_plan,
)
from game_automation.portable.application.screen_state_config import (
    load_screen_state_names,
)
from game_automation.portable.application.task_catalog import TaskNotFoundError
from game_automation.portable.application.task_details import (
    TaskDetailsResult,
    describe_task_details,
)
from game_automation.portable.application.task_resources import (
    prepare_task_resources,
    task_state_config_path,
)


def _run_list(args: argparse.Namespace) -> int:
    """列出所有可用任务。"""
    catalog_result = _load_cli_task_catalog_result(
        args.project_root,
    )
    for name in catalog_result.catalog.list_names():
        print(name)
    _print_task_config_errors(catalog_result)
    return 0


def _run_task(args: argparse.Namespace) -> int:
    """按名称运行任务。"""
    if args.dry_run_script_images and not args.dry_run:
        print("--dry-run-script-images requires --dry-run", file=sys.stderr)
        return 2
    try:
        task = _load_cli_task_catalog_result(
            args.project_root,
        ).catalog.get(args.name)
    except TaskNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"task configuration failed: {exc}", file=sys.stderr)
        return 2
    try:
        task = prepare_task_resources(task, args.project_root)
    except (LookupError, ValueError) as exc:
        print(f"task resource configuration failed: {exc}", file=sys.stderr)
        return 2

    dry_run_images = _resolve_dry_run_images(args.dry_run_image, args.project_root)
    if args.dry_run_script_images:
        try:
            dry_run_images = _merge_dry_run_images(
                dry_run_images,
                _describe_task(task, args.project_root).image_dependencies,
            )
        except (LookupError, ValueError) as exc:
            print(f"task details configuration failed: {exc}", file=sys.stderr)
            return 2

    dry_run_screen_state = args.dry_run_screen_state

    result = run_task_on_local_desktop(
        task,
        dry_run=args.dry_run,
        dry_run_color=args.dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=dry_run_screen_state,
        project_root=args.project_root,
    )
    if result.error_message is not None:
        print(result.error_message, file=sys.stderr)
    return result.exit_code


def _run_plan(args: argparse.Namespace) -> int:
    """按用户给定顺序运行一轮任务计划。"""
    if args.dry_run_script_images and not args.dry_run:
        print("--dry-run-script-images requires --dry-run", file=sys.stderr)
        return 2

    plan_items_result = _resolve_plan_items(args)
    if isinstance(plan_items_result, int):
        return plan_items_result
    dry_run_screen_state = args.dry_run_screen_state

    result = run_task_plan(
        plan_items_result,
        run_item=lambda item: _run_plan_item(
            item,
            dry_run=args.dry_run,
            dry_run_color=args.dry_run_color,
            dry_run_screen_state=dry_run_screen_state,
            project_root=args.project_root,
        ),
        continue_on_error=args.continue_on_error,
    )
    _print_run_plan_result(result)
    return result.exit_code


def _resolve_plan_items(args: argparse.Namespace) -> tuple[TaskPlanItem, ...] | int:
    """解析 Run Plan 中每个任务名和该任务自己的 dry-run 图片依赖。"""
    catalog_result = _load_cli_task_catalog_result(
        args.project_root,
    )
    tasks = []
    for task_name in args.names:
        try:
            task = catalog_result.catalog.get(task_name)
        except TaskNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"task configuration failed: {exc}", file=sys.stderr)
            return 2
        tasks.append((task_name, task))
    items: list[TaskPlanItem] = []
    for task_name, task in tasks:
        try:
            task = prepare_task_resources(task, args.project_root)
        except (LookupError, ValueError) as exc:
            print(f"task resource configuration failed: {exc}", file=sys.stderr)
            return 2
        dry_run_images = _resolve_dry_run_images(args.dry_run_image, args.project_root)
        if args.dry_run_script_images:
            try:
                dry_run_images = _merge_dry_run_images(
                    dry_run_images,
                    _describe_task(task, args.project_root).image_dependencies,
                )
            except (LookupError, ValueError) as exc:
                print(f"task details configuration failed: {exc}", file=sys.stderr)
                return 2
        items.append(TaskPlanItem(task_name, task, dry_run_images=dry_run_images))
    return tuple(items)


def _run_plan_item(
    item: TaskPlanItem,
    *,
    dry_run: bool,
    dry_run_color: str,
    dry_run_screen_state: str,
    project_root: Path,
) -> TaskPlanRunResult:
    """运行计划中的单个任务并捕获输出，供计划摘要统一展示。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = run_task_on_local_desktop(
            item.task,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            dry_run_images=item.dry_run_images,
            dry_run_screen_state=dry_run_screen_state,
            project_root=project_root,
        )
    if result.error_message is not None:
        stderr.write(result.error_message)
        stderr.write("\n")
    return TaskPlanRunResult(
        exit_code=result.exit_code,
        finish_reason=result.finish_reason,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def _print_run_plan_result(result: TaskPlanResult) -> None:
    """打印一轮计划摘要和每个任务捕获到的输出。"""
    print(
        f"Run Plan: exit_code={result.exit_code} finish_reason={result.finish_reason}"
    )
    for item in result.items:
        _print_run_plan_item_result(item)


def _print_run_plan_item_result(item: TaskPlanItemResult) -> None:
    """打印计划中单个任务的摘要和输出。"""
    print(
        f"[{item.index}] {item.task_name}: "
        f"exit_code={item.exit_code} finish_reason={item.finish_reason}"
    )
    if item.stdout:
        print(item.stdout, end="")
    if item.stderr:
        print(item.stderr, file=sys.stderr, end="")


def _run_details(args: argparse.Namespace) -> int:
    """按名称展示任务详情。"""
    try:
        task = _load_cli_task_catalog_result(
            args.project_root,
        ).catalog.get(args.name)
    except TaskNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"task configuration failed: {exc}", file=sys.stderr)
        return 2
    try:
        task = prepare_task_resources(task, args.project_root)
        details = _describe_task(task, args.project_root)
    except (LookupError, ValueError) as exc:
        print(f"task details configuration failed: {exc}", file=sys.stderr)
        return 2
    _print_task_details(details)
    return details.exit_code


def _load_cli_task_catalog_result(project_root: Path) -> ProjectTaskCatalogResult:
    """只从所选工作区发现 Python 任务，并保留逐文件诊断。"""
    return load_project_task_catalog_result(project_root)


def _print_task_config_errors(catalog_result: ProjectTaskCatalogResult) -> None:
    """把任务配置错误写入 stderr，避免污染 stdout 任务列表。"""
    if not catalog_result.task_config_errors:
        return
    print("任务配置错误：", file=sys.stderr)
    for error in catalog_result.task_config_errors:
        print(f"- {error.message}", file=sys.stderr)


def _describe_task(task, project_root: Path) -> TaskDetailsResult:
    """生成 CLI 复用的任务详情。"""
    return describe_task_details(
        task,
        asset_root=image_asset_root(project_root),
        supported_image_suffixes=IMAGE_ASSET_SUFFIXES,
        state_names=_configured_window_state_names(project_root, task),
    )


def _resolve_dry_run_images(
    image_paths: list[str], project_root: Path
) -> tuple[str, ...]:
    """把显式模拟图片的相对路径绑定工作区，绝对模板路径保持原样。"""
    return tuple(
        value if Path(value).is_absolute() else str((project_root / value).resolve())
        for value in image_paths
    )


def _merge_dry_run_images(
    explicit_images: tuple[str, ...],
    script_images: tuple[str, ...],
) -> tuple[str, ...]:
    """合并用户显式 dry-run 图片和脚本解析出的图片依赖。"""
    return tuple(dict.fromkeys((*explicit_images, *script_images)))


def _configured_window_state_names(project_root: Path, task) -> tuple[str, ...] | None:
    """读取窗口规则中的状态名，配置不可用时返回 None。"""
    try:
        return load_screen_state_names(task_state_config_path(task, project_root))
    except ValueError:
        return None


def _print_task_details(details: TaskDetailsResult) -> None:
    """把任务详情结果打印成稳定的 CLI 文本。"""
    if details.stderr:
        print(details.stderr, file=sys.stderr, end="")
    if not details.steps:
        return
    print(f"任务：{details.name}")
    _print_section("任务入口", details.steps)
    _print_section("点位依赖", details.point_dependencies)
    _print_section("图片依赖", details.image_dependencies)
    _print_section("依赖", details.dependencies)
    _print_section(
        "依赖检查",
        tuple(
            f"{_readiness_status_label(status)} {label}：{message}"
            for label, status, message in details.readiness
        ),
    )


def _print_section(title: str, lines: tuple[str, ...]) -> None:
    """打印一个带标题的详情分组。"""
    print(f"{title}：")
    if not lines:
        print("- 无")
        return
    for line in lines:
        print(f"- {line}")


def _readiness_status_label(status: str) -> str:
    """把 readiness 状态转换成 CLI 展示标签。"""
    if status == "ok":
        return "[OK]"
    if status == "missing":
        return "[缺失]"
    return "[未知]"


def _run_recorder(args: argparse.Namespace) -> int:
    """启动坐标记录工具。"""
    from game_automation.platform.desktop.adapters import (
        PyAutoGuiPixelColorReader,
        PyAutoGuiPointerPositionReader,
        TerminalKeyStateReader,
    )
    from game_automation.portable.tools.coordinate_recorder import CoordinateRecorder

    key_reader = None
    try:
        key_reader = TerminalKeyStateReader()
        recorder = CoordinateRecorder(
            pointer_reader=PyAutoGuiPointerPositionReader(),
            key_reader=key_reader,
            color_reader=PyAutoGuiPixelColorReader(),
            display_interval_seconds=args.display_interval,
            poll_interval_seconds=args.poll_interval,
        )
        recorder.run()
    except RuntimeError as exc:
        print(f"coordinate recorder setup failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"coordinate recorder configuration failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if key_reader is not None:
            key_reader.close()
    return 0


def _run_ui(args: argparse.Namespace) -> int:
    """启动 macOS 原生桌面壳，未指定工作区时由原生选择器选择。"""
    from game_automation.platform.local_desktop.entrypoints.desktop_app import (
        launch_desktop,
    )

    try:
        return launch_desktop(
            workspace=args.project_root if args.workspace is not None else None
        )
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _run_prepare(args: argparse.Namespace) -> int:
    """在原生桌面壳中打开素材准备，任务素材使用显式工作区。"""
    if args.workspace is None:
        print("prepare requires --workspace PATH before the command", file=sys.stderr)
        return 2
    return _run_ui(args)


def _resolve_workspace(workspace: str | None) -> Path:
    """校验显式工作区并返回绝对目录，默认沿用当前项目根目录。"""
    if workspace is None:
        return PROJECT_ROOT
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"workspace must be an existing directory: {root}")
    return root


def main(argv: list[str] | None = None) -> int:
    """解析工作区与子命令，完成路径校验后调用对应入口。"""
    parser = argparse.ArgumentParser(
        prog="star", description="Game automation toolkit."
    )
    parser.add_argument(
        "--workspace",
        metavar="PATH",
        help="Use tasks and assets from this existing local workspace (before the command).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available tasks.")

    details_parser = subparsers.add_parser(
        "details", help="Show a named task's entry and dependencies."
    )
    details_parser.add_argument("name", help="Task name to inspect.")

    run_parser = subparsers.add_parser("run", help="Run a named task.")
    run_parser.add_argument("name", help="Task name to run.")
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without real mouse.",
    )
    mode.add_argument(
        "--macos", action="store_true", help="Run with macOS adapter (default)."
    )
    run_parser.add_argument(
        "--dry-run-color",
        default="#000000",
        help="Fixed #RRGGBB screen color used when dry-running color conditions.",
    )
    run_parser.add_argument(
        "--dry-run-image",
        action="append",
        default=[],
        help="Template path treated as found; relative to the workspace (for example assets/start.png). Can be repeated.",
    )
    run_parser.add_argument(
        "--dry-run-script-images",
        action="store_true",
        help="Treat resolved task image dependencies as found when dry-running.",
    )
    run_parser.add_argument(
        "--dry-run-screen-state",
        default="未知",
        help="Fixed state name used when dry-running state conditions.",
    )

    run_plan_parser = subparsers.add_parser(
        "run-plan", help="Run many named tasks in order."
    )
    run_plan_parser.add_argument("names", nargs="+", help="Task names to run in order.")
    run_plan_mode = run_plan_parser.add_mutually_exclusive_group()
    run_plan_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without real mouse.",
    )
    run_plan_mode.add_argument(
        "--macos", action="store_true", help="Run with macOS adapter (default)."
    )
    run_plan_parser.add_argument(
        "--dry-run-color",
        default="#000000",
        help="Fixed #RRGGBB screen color used when dry-running color conditions.",
    )
    run_plan_parser.add_argument(
        "--dry-run-image",
        action="append",
        default=[],
        help="Template path treated as found; relative to the workspace (for example assets/start.png). Can be repeated.",
    )
    run_plan_parser.add_argument(
        "--dry-run-script-images",
        action="store_true",
        help="Treat each task's resolved image dependencies as found when dry-running.",
    )
    run_plan_parser.add_argument(
        "--dry-run-screen-state",
        default="未知",
        help="Fixed state name used when dry-running state conditions.",
    )
    run_plan_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running later tasks after a task returns a non-zero exit code.",
    )

    recorder_parser = subparsers.add_parser(
        "recorder", help="Record screen coordinates."
    )
    recorder_parser.add_argument(
        "--display-interval",
        type=float,
        default=1.0,
        help="Seconds between coordinate prints.",
    )
    recorder_parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.05,
        help="Seconds between keyboard polls.",
    )

    subparsers.add_parser("ui", help="Start the macOS native desktop application.")

    subparsers.add_parser(
        "prepare", help="Open material preparation in the macOS native application."
    )

    args = parser.parse_args(argv)
    try:
        args.project_root = _resolve_workspace(args.workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"invalid workspace: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        return _run_list(args)
    elif args.command == "details":
        return _run_details(args)
    elif args.command == "run":
        return _run_task(args)
    elif args.command == "run-plan":
        return _run_plan(args)
    elif args.command == "recorder":
        return _run_recorder(args)
    elif args.command == "ui":
        return _run_ui(args)
    elif args.command == "prepare":
        return _run_prepare(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
