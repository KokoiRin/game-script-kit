"""star 命令行入口。

本 module 负责解析命令行参数、选择本地工作区并打印用户可见结果；脚本运行和
本地 UI 委托应用/入口编排层，recorder 子命令保留终端工具组装但不解释脚本步骤。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from game_automation.platform.local_desktop.composition import (
    run_script_on_local_desktop,
)
from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    SCREEN_STATE_CONFIG_NAME,
    image_asset_root,
)
from game_automation.portable.application.screen_state_config import load_screen_state_names
from game_automation.portable.application.script_details import ScriptDetailsResult, describe_script_details
from game_automation.portable.application.project_scripts import (
    ProjectScriptCatalogResult,
    load_project_script_catalog_result,
)
from game_automation.portable.application.run_plan import (
    ScriptPlanItem,
    ScriptPlanItemResult,
    ScriptPlanResult,
    ScriptPlanScriptResult,
    run_script_plan,
)
from game_automation.portable.application.script_resources import (
    load_shared_script_resources,
    script_with_shared_resources,
)
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptCatalog, ScriptNotFoundError


def _run_list(args: argparse.Namespace) -> int:
    """列出所有可用脚本。"""
    catalog_result = _load_cli_script_catalog_result(
        args.project_root, include_builtin_scripts=args.workspace is None,
    )
    for name in catalog_result.catalog.list_names():
        print(name)
    _print_script_config_errors(catalog_result)
    return 0


def _run_history(args: argparse.Namespace) -> int:
    """查询控制台持久历史，支持导出完整 JSON 供排查。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    store = SqliteRunHistoryStore(args.project_root / ".star" / "runs.sqlite3")
    try:
        result = store.read_run(args.run_id) if args.run_id else {"runs": store.list_runs()}
    except (LookupError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json_output or args.run_id:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not result["runs"]:
        print("暂无保存的控制台运行记录。")
    else:
        for item in result["runs"]:
            timestamp = item["started_at"] or "原时间未知"
            mode = "模拟" if item["dry_run"] else "真实"
            print(f"{item['id']}  {timestamp}  {mode}  {item['finish_reason']}  {item['name']}")
            if item["last_step"]:
                print(f"  最后步骤：{item['last_step']}")
            if item["error"]:
                print(f"  提示：{item['error'].strip()}")
    return 0


def _run_script(args: argparse.Namespace) -> int:
    """按名称运行脚本。"""
    target_application_error = _validate_target_application_args(args)
    if target_application_error != 0:
        return target_application_error
    if args.dry_run_script_images and not args.dry_run:
        print("--dry-run-script-images requires --dry-run", file=sys.stderr)
        return 2
    try:
        script = _load_cli_script_catalog_result(
            args.project_root, include_builtin_scripts=args.workspace is None,
        ).catalog.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"script configuration failed: {exc}", file=sys.stderr)
        return 2
    try:
        script = script_with_shared_resources(script, load_shared_script_resources(args.project_root))
    except (LookupError, ValueError) as exc:
        print(f"script resource configuration failed: {exc}", file=sys.stderr)
        return 2

    dry_run_images = _resolve_dry_run_images(args.dry_run_image, args.project_root)
    if args.dry_run_script_images:
        try:
            dry_run_images = _merge_dry_run_images(
                dry_run_images,
                _describe_script(script, args.project_root).image_dependencies,
            )
        except (LookupError, ValueError) as exc:
            print(f"script details configuration failed: {exc}", file=sys.stderr)
            return 2

    dry_run_screen_state = args.dry_run_screen_state

    result = run_script_on_local_desktop(
        script,
        dry_run=args.dry_run,
        dry_run_color=args.dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=dry_run_screen_state,
        target_application=args.target_app,
        target_window_title=args.target_window_title,
        project_root=args.project_root,
    )
    if result.error_message is not None:
        print(result.error_message, file=sys.stderr)
    return result.exit_code


def _run_plan(args: argparse.Namespace) -> int:
    """按用户给定顺序运行一轮脚本计划。"""
    target_application_error = _validate_target_application_args(args)
    if target_application_error != 0:
        return target_application_error
    if args.dry_run_script_images and not args.dry_run:
        print("--dry-run-script-images requires --dry-run", file=sys.stderr)
        return 2

    plan_items_result = _resolve_plan_items(args)
    if isinstance(plan_items_result, int):
        return plan_items_result
    dry_run_screen_state = args.dry_run_screen_state

    result = run_script_plan(
        plan_items_result,
        run_item=lambda item: _run_plan_item(
            item,
            dry_run=args.dry_run,
            dry_run_color=args.dry_run_color,
            dry_run_screen_state=dry_run_screen_state,
            target_application=args.target_app,
            target_window_title=args.target_window_title,
            project_root=args.project_root,
        ),
        continue_on_error=args.continue_on_error,
    )
    _print_run_plan_result(result)
    return result.exit_code


def _resolve_plan_items(args: argparse.Namespace) -> tuple[ScriptPlanItem, ...] | int:
    """解析 Run Plan 中每个脚本名和该脚本自己的 dry-run 图片依赖。"""
    catalog_result = _load_cli_script_catalog_result(
        args.project_root, include_builtin_scripts=args.workspace is None,
    )
    scripts = []
    for script_name in args.names:
        try:
            script = catalog_result.catalog.get(script_name)
        except ScriptNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"script configuration failed: {exc}", file=sys.stderr)
            return 2
        scripts.append((script_name, script))
    try:
        shared_resources = load_shared_script_resources(args.project_root)
    except (LookupError, ValueError) as exc:
        print(f"script resource configuration failed: {exc}", file=sys.stderr)
        return 2

    items: list[ScriptPlanItem] = []
    for script_name, script in scripts:
        try:
            script = script_with_shared_resources(script, shared_resources)
        except (LookupError, ValueError) as exc:
            print(f"script resource configuration failed: {exc}", file=sys.stderr)
            return 2
        dry_run_images = _resolve_dry_run_images(args.dry_run_image, args.project_root)
        if args.dry_run_script_images:
            try:
                dry_run_images = _merge_dry_run_images(
                    dry_run_images,
                    _describe_script(script, args.project_root).image_dependencies,
                )
            except (LookupError, ValueError) as exc:
                print(f"script details configuration failed: {exc}", file=sys.stderr)
                return 2
        items.append(ScriptPlanItem(script_name, script, dry_run_images=dry_run_images))
    return tuple(items)


def _run_plan_item(
    item: ScriptPlanItem,
    *,
    dry_run: bool,
    dry_run_color: str,
    dry_run_screen_state: str,
    target_application: str | None,
    target_window_title: str | None,
    project_root: Path,
) -> ScriptPlanScriptResult:
    """运行计划中的单个脚本并捕获输出，供计划摘要统一展示。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = run_script_on_local_desktop(
            item.script,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            dry_run_images=item.dry_run_images,
            dry_run_screen_state=dry_run_screen_state,
            target_application=target_application,
            target_window_title=target_window_title,
            project_root=project_root,
        )
    if result.error_message is not None:
        stderr.write(result.error_message)
        stderr.write("\n")
    return ScriptPlanScriptResult(
        exit_code=result.exit_code,
        finish_reason=result.finish_reason,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def _print_run_plan_result(result: ScriptPlanResult) -> None:
    """打印一轮计划摘要和每个脚本捕获到的输出。"""
    print(f"Run Plan: exit_code={result.exit_code} finish_reason={result.finish_reason}")
    for item in result.items:
        _print_run_plan_item_result(item)


def _print_run_plan_item_result(item: ScriptPlanItemResult) -> None:
    """打印计划中单个脚本的摘要和输出。"""
    print(
        f"[{item.index}] {item.script_name}: "
        f"exit_code={item.exit_code} finish_reason={item.finish_reason}"
    )
    if item.stdout:
        print(item.stdout, end="")
    if item.stderr:
        print(item.stderr, file=sys.stderr, end="")


def _validate_target_application_args(args: argparse.Namespace) -> int:
    """拒绝要求无副作用的 dry-run 同时激活真实应用。"""
    if args.target_window_title is not None and args.target_app is None:
        print("--target-window-title requires --target-app", file=sys.stderr)
        return 2
    if args.target_app is not None and args.dry_run:
        print("--target-app cannot be used with --dry-run", file=sys.stderr)
        return 2
    return 0


def _run_details(args: argparse.Namespace) -> int:
    """按名称展示脚本详情。"""
    try:
        script = _load_cli_script_catalog_result(
            args.project_root, include_builtin_scripts=args.workspace is None,
        ).catalog.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"script configuration failed: {exc}", file=sys.stderr)
        return 2
    try:
        script = script_with_shared_resources(script, load_shared_script_resources(args.project_root))
        details = _describe_script(script, args.project_root)
    except (LookupError, ValueError) as exc:
        print(f"script details configuration failed: {exc}", file=sys.stderr)
        return 2
    _print_script_details(details)
    return details.exit_code


def _load_cli_script_catalog_result(
    project_root: Path,
    *,
    include_builtin_scripts: bool,
) -> ProjectScriptCatalogResult:
    """加载选定工作区脚本，显式工作区只包含自己的 JSON 脚本。"""
    base_catalog = DEFAULT_SCRIPT_CATALOG if include_builtin_scripts else ScriptCatalog(())
    return load_project_script_catalog_result(project_root, base_catalog=base_catalog)


def _print_script_config_errors(catalog_result: ProjectScriptCatalogResult) -> None:
    """把文件脚本配置错误写入 stderr，避免污染 stdout 脚本列表。"""
    if not catalog_result.script_config_errors:
        return
    print("脚本配置错误：", file=sys.stderr)
    for error in catalog_result.script_config_errors:
        print(f"- {error.message}", file=sys.stderr)


def _describe_script(script, project_root: Path) -> ScriptDetailsResult:
    """生成 CLI 复用的脚本详情。"""
    return describe_script_details(
        script,
        asset_root=image_asset_root(project_root),
        supported_image_suffixes=IMAGE_ASSET_SUFFIXES,
        state_names=_configured_screen_state_names(project_root),
    )


def _resolve_dry_run_images(image_paths: list[str], project_root: Path) -> tuple[str, ...]:
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


def _configured_screen_state_names(project_root: Path) -> tuple[str, ...] | None:
    """读取状态配置中的状态名，配置不可用时返回 None。"""
    try:
        return load_screen_state_names(image_asset_root(project_root) / SCREEN_STATE_CONFIG_NAME)
    except ValueError:
        return None


def _print_script_details(details: ScriptDetailsResult) -> None:
    """把脚本详情结果打印成稳定的 CLI 文本。"""
    if details.exit_code != 0:
        print(details.stderr, file=sys.stderr, end="")
        return
    print(f"脚本：{details.name}")
    _print_section("步骤", details.steps)
    _print_section("状态等待", tuple(f"等待状态: {state}" for state in details.state_waits))
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
    """启动本地控制 UI。"""
    from game_automation.platform.local_desktop.entrypoints.local_ui import serve_local_control_ui

    return serve_local_control_ui(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        project_root=args.project_root,
        include_builtin_scripts=args.workspace is None,
    )


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
    parser = argparse.ArgumentParser(prog="star", description="Game automation toolkit.")
    parser.add_argument(
        "--workspace",
        metavar="PATH",
        help="Use scripts and assets from this existing local workspace (before the command).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available scripts.")
    history_parser = subparsers.add_parser("history", help="Read saved console run history.")
    history_parser.add_argument("run_id", nargs="?", help="Run ID whose full log should be exported.")
    history_parser.add_argument("--json", action="store_true", dest="json_output", help="Print JSON instead of the recent run summary.")

    details_parser = subparsers.add_parser("details", help="Show a named script's steps and dependencies.")
    details_parser.add_argument("name", help="Script name to inspect.")

    run_parser = subparsers.add_parser("run", help="Run a named script.")
    run_parser.add_argument("name", help="Script name to run.")
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned operations without real mouse.")
    mode.add_argument("--macos", action="store_true", help="Run with macOS adapter (default).")
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
        help="Treat resolved script image dependencies as found when dry-running.",
    )
    run_parser.add_argument(
        "--dry-run-screen-state",
        default="未知",
        help="Fixed screen state used when dry-running screen-state conditions.",
    )
    run_parser.add_argument(
        "--target-app",
        default=None,
        help="Activate this application before a real script run.",
    )
    run_parser.add_argument(
        "--target-window-title",
        default=None,
        help="Raise the unique top-level window containing this title and bind its bounds.",
    )

    run_plan_parser = subparsers.add_parser("run-plan", help="Run many named scripts in order.")
    run_plan_parser.add_argument("names", nargs="+", help="Script names to run in order.")
    run_plan_mode = run_plan_parser.add_mutually_exclusive_group()
    run_plan_mode.add_argument("--dry-run", action="store_true", help="Print planned operations without real mouse.")
    run_plan_mode.add_argument("--macos", action="store_true", help="Run with macOS adapter (default).")
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
        help="Treat each script's resolved image dependencies as found when dry-running.",
    )
    run_plan_parser.add_argument(
        "--dry-run-screen-state",
        default="未知",
        help="Fixed screen state used when dry-running screen-state conditions.",
    )
    run_plan_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running later scripts after a script returns a non-zero exit code.",
    )
    run_plan_parser.add_argument(
        "--target-app",
        default=None,
        help="Activate this application before every real plan item.",
    )
    run_plan_parser.add_argument(
        "--target-window-title",
        default=None,
        help="Raise and bind the matching top-level window before every real plan item.",
    )

    recorder_parser = subparsers.add_parser("recorder", help="Record screen coordinates.")
    recorder_parser.add_argument("--display-interval", type=float, default=1.0, help="Seconds between coordinate prints.")
    recorder_parser.add_argument("--poll-interval", type=float, default=0.05, help="Seconds between keyboard polls.")

    ui_parser = subparsers.add_parser("ui", help="Start the local control UI.")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Host address for the local UI server.")
    ui_parser.add_argument("--port", type=int, default=8765, help="Port for the local UI server.")
    ui_parser.add_argument("--no-open", action="store_true", help="Do not open a browser window after starting.")

    args = parser.parse_args(argv)
    try:
        args.project_root = _resolve_workspace(args.workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"invalid workspace: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        return _run_list(args)
    elif args.command == "history":
        return _run_history(args)
    elif args.command == "details":
        return _run_details(args)
    elif args.command == "run":
        return _run_script(args)
    elif args.command == "run-plan":
        return _run_plan(args)
    elif args.command == "recorder":
        return _run_recorder(args)
    elif args.command == "ui":
        return _run_ui(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
