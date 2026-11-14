"""静态发现工作区内直接执行函数的 Python 任务。

本模块只读取 TASK 字面量、检查 run 入口并保存源码快照，不导入任务模块。
目标与资源语法复用配置解析，实际执行由应用层运行用例负责。
"""

from __future__ import annotations

import ast
from pathlib import Path

from game_automation.portable.application.task_metadata import (
    parse_script_resources,
    parse_script_target,
)
from game_automation.portable.domain import TargetCatalog
from game_automation.portable.domain.task import FunctionTask, TaskRequirements


def parse_function_task_source(
    source: str, *, path: Path, asset_root: Path
) -> FunctionTask | None:
    """校验同步入口和字面量声明，将同一版源码绑定到任务输入。"""
    try:
        tree = ast.parse(source, filename=str(path))
        compile(tree, str(path), "exec", dont_inherit=True)
    except SyntaxError as exc:
        raise ValueError(
            f"invalid Python task syntax at line {exc.lineno}: {exc.msg}"
        ) from exc
    assignments = [node for node in tree.body if _assigns_task(node)]
    if not assignments:
        return None
    if len(assignments) != 1:
        raise ValueError("Python task requires exactly one TASK assignment")
    assignment = assignments[0]
    if isinstance(assignment, ast.Assign):
        if len(assignment.targets) != 1 or not isinstance(
            assignment.targets[0], ast.Name
        ):
            raise ValueError("TASK must use a single literal assignment")
    elif not isinstance(assignment, ast.AnnAssign):
        raise ValueError("TASK must use a literal assignment")
    try:
        metadata = ast.literal_eval(assignment.value)
    except (TypeError, ValueError) as exc:
        raise ValueError("TASK must be a literal dictionary") from exc
    if not isinstance(metadata, dict):
        raise ValueError("TASK must be a literal dictionary")
    unknown = metadata.keys() - {"name", "target", "resources", "requires"}
    if unknown:
        raise ValueError(
            f"unknown TASK fields: {', '.join(map(str, sorted(unknown, key=str)))}"
        )
    _validate_run(tree)
    resources = parse_script_resources(
        metadata.get("resources", {}), asset_root=asset_root
    )
    return FunctionTask(
        name=metadata.get("name"),
        source_path=path,
        source=source,
        resources=resources,
        target=parse_script_target(metadata.get("target")),
        requires=_parse_requires(metadata.get("requires", {}), resources),
    )


def _assigns_task(node: ast.AST) -> bool:
    """识别模块顶层对 TASK 的赋值，包括应报告的多目标赋值。"""
    targets = ()
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign | ast.AugAssign):
        targets = (node.target,)
    return any(
        isinstance(item, ast.Name) and item.id == "TASK"
        for target in targets
        for item in ast.walk(target)
    )


def _validate_run(tree: ast.Module) -> None:
    """要求唯一同步 run 函数接收一个位置参数并直接执行函数体。"""
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == "run"
    ]
    if len(functions) != 1 or not isinstance(functions[0], ast.FunctionDef):
        raise ValueError(
            "Python task requires exactly one synchronous run(ctx) function"
        )
    function = functions[0]
    args = function.args
    if (
        len(args.posonlyargs) + len(args.args) != 1
        or args.vararg is not None
        or args.kwarg is not None
        or args.kwonlyargs
    ):
        raise ValueError("Python task run(ctx) must accept one positional argument")
    visitor = _RunBodyVisitor()
    for node in function.body:
        visitor.visit(node)
    if visitor.is_generator:
        raise ValueError(
            "Python task run(ctx) must be a regular function, not a generator"
        )


class _RunBodyVisitor(ast.NodeVisitor):
    """检查入口自身的生成器语法，允许辅助函数使用自己的执行形式。"""

    def __init__(self) -> None:
        """初始化入口是否包含 yield 的检查结果。"""
        self.is_generator = False

    def visit_Yield(self, node: ast.Yield) -> None:
        """记录入口函数自身包含生成器返回。"""
        self.is_generator = True

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        """记录入口函数自身包含生成器委托。"""
        self.is_generator = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """跳过嵌套辅助函数的独立作用域。"""

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """跳过嵌套异步辅助函数的独立作用域。"""

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """跳过嵌套匿名函数的独立作用域。"""


def _parse_requires(value: object, resources: TargetCatalog) -> TaskRequirements:
    """合并局部资源与显式共享依赖，校验未知声明字段。"""
    if not isinstance(value, dict):
        raise ValueError("TASK requires must be an object")
    unknown = value.keys() - {"points", "images", "searches", "states", "colors"}
    if unknown:
        raise ValueError(
            f"unknown TASK requires fields: {', '.join(map(str, sorted(unknown, key=str)))}"
        )
    return TaskRequirements(
        points=_dependency_names(value, "points", resources.points),
        images=_dependency_names(value, "images", resources.images),
        searches=_dependency_names(value, "searches", resources.searches),
        states=_dependency_names(value, "states"),
        colors=value.get("colors", False),
    )


def _dependency_names(value: dict, key: str, local: tuple = ()) -> tuple[str, ...]:
    """把声明中的名称列表与本地资源名称合并并保持阅读顺序。"""
    names = value.get(key, [])
    if not isinstance(names, list) or any(
        not isinstance(name, str) or not name.strip() for name in names
    ):
        raise ValueError(f"TASK requires {key} must be a list of non-empty names")
    return tuple(dict.fromkeys((*tuple(resource.name for resource in local), *names)))
