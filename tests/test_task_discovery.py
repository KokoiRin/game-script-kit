"""验证任务目录统一发现和逐文件隔离。

本模块通过公开目录和格式入口读取临时工作区，不执行任务或访问桌面。
"""

import pytest

from game_automation.portable.application.project_scripts import (
    load_project_script_catalog_result,
)
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


@pytest.mark.parametrize("suffix", [".json", ".py"])
def test_catalog_isolates_dangling_source_symlinks(tmp_path, suffix) -> None:
    """坏源码链接不能阻断同目录中的有效任务。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "good.py").write_text(
        "TASK = {'name': 'good'}\ndef run(ctx): pass\n", encoding="utf-8"
    )
    (scripts / f"bad{suffix}").symlink_to(tmp_path / "missing")

    result = load_project_script_catalog_result(
        tmp_path, base_catalog=ScriptCatalog(())
    )

    assert result.catalog.list_names() == ("good",)
    assert len(result.script_config_errors) == 1
    assert result.script_config_errors[0].file == f"bad{suffix}"


def test_json_source_reports_required_python_migration(tmp_path):
    """旧 JSON 文件产生迁移诊断且不会执行其中的动作。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "old.json").write_text('{"name": "old", "steps": [{"wait": 0}]}')
    result = load_project_script_catalog_result(tmp_path)
    assert result.catalog.list_names() == ()
    assert len(result.script_config_errors) == 1
    assert result.script_config_errors[0].file == "old.json"
    assert "run(ctx)" in result.script_config_errors[0].message


@pytest.mark.parametrize("suffix", [".json", ".py"])
def test_catalog_isolates_invalid_source_encoding(tmp_path, suffix) -> None:
    """两种格式使用同一逐文件编码错误边界。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "good.py").write_text(
        "TASK = {'name': 'good'}\ndef run(ctx): pass\n", encoding="utf-8"
    )
    (scripts / f"bad{suffix}").write_bytes(b"\xff")

    result = load_project_script_catalog_result(
        tmp_path, base_catalog=ScriptCatalog(())
    )

    assert result.catalog.list_names() == ("good",)
    assert tuple(error.file for error in result.script_config_errors) == (
        f"bad{suffix}",
    )


def test_catalog_reports_invalid_directory_once(tmp_path) -> None:
    """统一目录检查只产生一条路径诊断。"""
    (tmp_path / "scripts").write_text("not a directory", encoding="utf-8")

    result = load_project_script_catalog_result(
        tmp_path, base_catalog=ScriptCatalog(())
    )

    assert result.catalog.list_names() == ()
    assert len(result.script_config_errors) == 1
    assert "not a directory" in result.script_config_errors[0].message


def test_catalog_preserves_filename_order_and_duplicate_source(tmp_path):
    """Python 按文件名排序，重名错误指向被隔离的后续文件。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for file, name in (
        ("c.py", "shared"),
        ("a.py", "first"),
        ("b.py", "shared"),
        ("d.py", "last"),
    ):
        (scripts / file).write_text(
            f"TASK = {{'name': {name!r}}}\ndef run(ctx): pass\n"
        )
    result = load_project_script_catalog_result(tmp_path)
    assert result.catalog.list_names() == ("first", "shared", "last")
    assert tuple(error.file for error in result.script_config_errors) == ("c.py",)
    assert "duplicate script name: shared" in result.script_config_errors[0].message


def test_python_encoding_declaration_and_snapshot_use_the_same_source(tmp_path) -> None:
    """按 Python 编码声明静态解析并保存被解析的同一源码快照。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    source = "# coding: latin-1\nTASK = {'name': 'café'}\ndef run(ctx): pass\n"
    (scripts / "encoded.py").write_bytes(source.encode("latin-1"))

    result = load_project_script_catalog_result(
        tmp_path, base_catalog=ScriptCatalog(())
    )

    assert result.script_config_errors == ()
    assert result.catalog.get("café").source == source
