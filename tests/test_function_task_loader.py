"""验证 Python 任务发现、声明依赖与详情的公开行为。

本模块使用临时工作区检查静态读取及错误隔离，不执行真实桌面操作。
函数运行和动作语义由运行用例与任务上下文测试覆盖。
"""

import json
from pathlib import Path

import pytest

from game_automation.portable.application.project_tasks import (
    load_project_task_catalog_result,
)
from game_automation.portable.application.task_catalog import TaskCatalog
from game_automation.portable.application.task_dependencies import (
    validate_task_resource_references,
)
from game_automation.portable.application.task_details import describe_task_details
from game_automation.portable.application.task_resources import (
    prepare_task_resources,
)
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.engine.runtime_requirements import (
    inspect_runtime_requirements,
)


def write_task(
    root: Path,
    metadata: dict,
    *,
    body: str = "def run(ctx):\n    return None\n",
    filename: str = "task.py",
) -> Path:
    """保存一份可由公开发现入口读取的任务文件。"""
    script_dir = root / "scripts"
    script_dir.mkdir(exist_ok=True)
    path = script_dir / filename
    path.write_text(f"TASK = {metadata!r}\n\n{body}", encoding="utf-8")
    return path


def discover(root: Path):
    """只使用外部工作区文件构建脚本目录。"""
    return load_project_task_catalog_result(root, base_catalog=TaskCatalog(()))


def details(task: FunctionTask, root: Path, *, states: tuple[str, ...] = ()):
    """通过共享详情入口读取任务的声明依赖。"""
    return describe_task_details(
        task,
        asset_root=root / "assets",
        supported_image_suffixes=frozenset({".png"}),
        state_names=states,
    )


def test_catalog_and_details_read_function_task_without_executing_module(
    tmp_path,
) -> None:
    """查询目录与详情时跳过任务文件的所有可执行语句。"""
    marker = tmp_path / "executed"
    path = write_task(
        tmp_path,
        {"name": "static"},
        body=f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n\ndef run(ctx):\n    raise RuntimeError('not queried')\n",
    )

    result = discover(tmp_path)
    task = result.catalog.get("static")
    description = details(task, tmp_path)

    assert result.task_config_errors == ()
    assert isinstance(task, FunctionTask)
    assert task.source_path == path.resolve()
    assert description.exit_code == 0
    assert any(str(path.resolve()) in line for line in description.steps)
    assert not marker.exists()


def test_discovery_preserves_validated_source_snapshot(tmp_path) -> None:
    """目录中的任务输入绑定发现时的源码版本。"""
    path = write_task(tmp_path, {"name": "snapshot"})
    task = discover(tmp_path).catalog.get("snapshot")
    before = path.read_text(encoding="utf-8")

    path.write_text("raise RuntimeError('changed')\n", encoding="utf-8")

    assert task.source == before
    assert task.name == "snapshot"


@pytest.mark.parametrize(
    "source, message",
    [
        (
            "TASK = {'name': 'bad'}\nTASK = {'name': 'again'}\ndef run(ctx): pass\n",
            "TASK",
        ),
        ("TASK = dict(name='bad')\ndef run(ctx): pass\n", "literal"),
        ("TASK = {'name': 'bad'}\nasync def run(ctx): pass\n", "run"),
        ("TASK = {'name': 'bad'}\ndef run(): pass\n", "run"),
        ("TASK = {'name': 'bad'}\ndef run(ctx, other): pass\n", "run"),
        ("TASK = {'name': 'bad'}\ndef run(*args): pass\n", "run"),
        ("TASK = {'name': 'bad'}\ndef run(ctx): pass\ndef run(ctx): pass\n", "run"),
        (
            "TASK = {'name': 'bad', 'requires': {'statse': []}}\ndef run(ctx): pass\n",
            "requires",
        ),
        (
            "TASK = {'name': 'bad', 'requires': {'images': True}}\ndef run(ctx): pass\n",
            "images",
        ),
        (
            "TASK = {'name': 'bad', 'requires': {'colors': 'yes'}}\ndef run(ctx): pass\n",
            "colors",
        ),
        (
            "TASK = {'name': 'bad', 'requires': {'states': ['']}}\ndef run(ctx): pass\n",
            "states",
        ),
        ("TASK = {'name': 'bad', 'step': []}\ndef run(ctx): pass\n", "step"),
        (
            "TASK = {'name': 'bad', 'resources': {'imagse': {}}}\ndef run(ctx): pass\n",
            "resources.imagse",
        ),
        (
            "TASK = {'name': 'bad', 'resources': {'points': {'button': {'x': 1, 'y': 2, 'z': 3}}}}\ndef run(ctx): pass\n",
            "point resource button.z",
        ),
        (
            "TASK = {'name': 'bad', 'resources': {'regions': {'panel': {'left': 0, 'top': 0, 'width': 10, 'height': 10, 'extra': 1}}}}\ndef run(ctx): pass\n",
            "region resource panel.extra",
        ),
        (
            "TASK = {'name': 'bad', 'resources': {'searches': {'button': {'image': 'button', 'min_confidnce': 0.94}}}}\ndef run(ctx): pass\n",
            "image search resource button.min_confidnce",
        ),
        (
            "TASK = {'name': 'bad', 'resources': {'searches': {'button': {'image': 'button', 'region': {'left': 0, 'top': 0, 'width': 10, 'height': 10, 'extra': 1}}}}}\ndef run(ctx): pass\n",
            "image search region.extra",
        ),
        ("TASK = {'name': 'bad'}\ndef run(ctx):\n    break\n", "syntax"),
        ("TASK = {'name': 'bad'}\ndef run(ctx):\n    yield ctx\n", "run"),
    ],
)
def test_bad_python_task_is_isolated_from_valid_tasks(
    tmp_path, source, message
) -> None:
    """单文件的元信息或入口错误不阻断其他任务发现。"""
    write_task(tmp_path, {"name": "good"}, filename="good.py")
    (tmp_path / "scripts" / "bad.py").write_text(source, encoding="utf-8")

    result = discover(tmp_path)

    assert result.catalog.list_names() == ("good",)
    assert len(result.task_config_errors) == 1
    assert result.task_config_errors[0].file == "bad.py"
    assert message in result.task_config_errors[0].message


def test_resource_error_is_cleared_after_reloading_corrected_task(tmp_path) -> None:
    """修正资源字段后重新发现任务，保留有效声明及其他任务。"""
    write_task(tmp_path, {"name": "good"}, filename="good.py")
    write_task(tmp_path, {"name": "fixed", "resources": {"imagse": {}}})
    assert len(discover(tmp_path).task_config_errors) == 1

    write_task(
        tmp_path,
        {
            "name": "fixed",
            "resources": {
                "images": {"button": "button.png"},
                "points": {"button": {"x": 1, "y": 2}},
                "regions": {"panel": {"left": 0, "top": 0, "width": 10, "height": 10}},
                "searches": {
                    "button": {
                        "image": "button",
                        "region": "panel",
                        "min_confidence": 0.94,
                    }
                },
            },
        },
    )
    result = discover(tmp_path)

    assert result.task_config_errors == ()
    assert result.catalog.list_names() == ("good", "fixed")
    assert (
        result.catalog.get("fixed").resources.searches[0].search.min_confidence == 0.94
    )


def test_helper_files_are_not_listed_or_imported(tmp_path) -> None:
    """普通辅助模块与下划线文件保持在任务目录之外。"""
    write_task(tmp_path, {"name": "visible"})
    (tmp_path / "scripts" / "helper.py").write_text(
        "raise RuntimeError('helper imported')\n", encoding="utf-8"
    )
    (tmp_path / "scripts" / "_private.py").write_text(
        "TASK = {'name': 'private'}\ndef run(ctx): pass\n", encoding="utf-8"
    )

    assert discover(tmp_path).catalog.list_names() == ("visible",)


def test_nested_generator_does_not_change_run_entrypoint_kind(tmp_path) -> None:
    """入口内部的生成器辅助函数不影响同步入口自身的执行形式。"""
    write_task(
        tmp_path,
        {"name": "nested"},
        body="def run(ctx):\n    def items():\n        yield 1\n    return tuple(items())\n",
    )

    result = discover(tmp_path)

    assert result.catalog.list_names() == ("nested",)
    assert result.task_config_errors == ()


def test_task_metadata_accepts_literal_type_annotation(tmp_path) -> None:
    """字面量元信息允许普通 Python 类型注解。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "annotated.py").write_text(
        "TASK: dict = {'name': 'annotated'}\ndef run(ctx): pass\n", encoding="utf-8"
    )

    assert discover(tmp_path).catalog.list_names() == ("annotated",)


def test_function_task_survives_unsupported_json_file(tmp_path) -> None:
    """旧 JSON 文件不进入任务目录，Python 任务仍然可用。"""
    write_task(tmp_path, {"name": "same"})
    (tmp_path / "scripts" / "old.json").write_text(
        json.dumps({"name": "same", "steps": [{"wait": 0}]}), encoding="utf-8"
    )

    result = discover(tmp_path)

    assert result.catalog.list_names() == ("same",)
    assert result.task_config_errors == ()


def test_local_resources_automatically_supply_declared_dependencies(tmp_path) -> None:
    """资源声明同时供静态依赖和运行端口推导使用。"""
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    (asset_root / "button.png").write_bytes(b"template")
    write_task(
        tmp_path,
        {
            "name": "resources",
            "resources": {
                "points": {"open": {"x": 10, "y": 20}},
                "images": {"button": "button.png"},
                "regions": {"dialog": {"left": 0, "top": 0, "width": 40, "height": 30}},
                "searches": {
                    "confirm": {
                        "image": "button",
                        "region": "dialog",
                        "min_confidence": 0.9,
                    }
                },
            },
            "requires": {"points": ["open"], "states": ["home"], "colors": True},
            "target": {
                "application": "Game",
                "window_title": "Window",
                "width": 800,
                "height": 600,
                "backend": "macos-window-background",
            },
        },
    )

    task = discover(tmp_path).catalog.get("resources")
    description = details(task, tmp_path, states=("home",))
    requirements = inspect_runtime_requirements(task)

    assert task.requires.points == ("open",)
    assert task.requires.images == ("button",)
    assert task.requires.searches == ("confirm",)
    assert description.image_dependencies == (str(asset_root / "button.png"),)
    assert description.point_dependencies == ("open",)
    assert description.state_dependencies == ("home",)
    assert description.exit_code == 0
    assert {status for _, status, _ in description.readiness} == {"ok"}
    assert requirements.needs_image_locator
    assert requirements.needs_screen_state_reader
    assert requirements.needs_color_reader
    validate_task_resource_references(task)


def test_missing_references_are_visible_in_details_and_rejected_before_run(
    tmp_path,
) -> None:
    """声明中的缺失点位与图片搜索可在运行前定位。"""
    write_task(
        tmp_path,
        {
            "name": "missing",
            "requires": {
                "points": ["unknown"],
                "images": ["missing"],
                "searches": ["missing-search"],
                "states": ["unknown-state"],
            },
        },
    )
    task = discover(tmp_path).catalog.get("missing")

    description = details(task, tmp_path)

    assert description.exit_code == 2
    assert len(description.readiness) == 4
    assert {status for _, status, _ in description.readiness} == {"missing"}
    with pytest.raises(LookupError, match="unknown"):
        validate_task_resource_references(task)


def test_function_task_can_resolve_shared_searches(tmp_path) -> None:
    """显式共享搜索依赖沿用工作区资源合并及图片检查。"""
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    (asset_root / "button.png").write_bytes(b"template")
    (asset_root / "window-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "home",
                        "searches": [{"name": "shared", "image": "button.png"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    write_task(tmp_path, {"name": "shared", "requires": {"searches": ["shared"]}})

    task = prepare_task_resources(discover(tmp_path).catalog.get("shared"), tmp_path)

    validate_task_resource_references(task)
    assert details(task, tmp_path).image_dependencies == (
        str(asset_root / "button.png"),
    )


def test_missing_script_directory_returns_empty_result(tmp_path) -> None:
    """尚未创建脚本目录的工作区仍可读取空目录。"""
    result = discover(tmp_path)

    assert result.catalog.list_names() == ()
    assert result.task_config_errors == ()
