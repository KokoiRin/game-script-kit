"""验证命名脚本注册表的查询和错误处理。"""

import pytest

from game_automation.portable.scripts_manager.catalog import (
    DEFAULT_SCRIPT_CATALOG,
    ScriptCatalog,
    ScriptNotFoundError,
)
from game_automation.portable.application.project_scripts import load_project_script_catalog
from game_automation.portable.domain import Click, Point, ScreenWindow, Script


def build_script(name: str) -> Script:
    """构造一个用于注册表测试的最小脚本。"""
    return Script(name=name, window=ScreenWindow(), steps=(Click(Point(1, 2)),))


def test_script_catalog_lists_names_in_registration_order() -> None:
    """验证注册表按注册顺序列出脚本名称。"""
    catalog = ScriptCatalog((build_script("first"), build_script("second")))

    assert catalog.list_names() == ("first", "second")


def test_script_catalog_gets_script_by_name() -> None:
    """验证注册表可以按名称返回对应脚本对象。"""
    script = build_script("target")
    catalog = ScriptCatalog((script,))

    assert catalog.get("target") is script


def test_script_catalog_rejects_unknown_name() -> None:
    """验证未知脚本名称会返回领域错误。"""
    catalog = ScriptCatalog((build_script("known"),))

    with pytest.raises(ScriptNotFoundError, match="unknown script: missing"):
        catalog.get("missing")


def test_script_catalog_rejects_duplicate_names() -> None:
    """验证重复脚本名称会在注册阶段被拒绝。"""
    with pytest.raises(ValueError, match="duplicate script name: same"):
        ScriptCatalog((build_script("same"), build_script("same")))


def test_default_catalog_includes_conditional_color_demo() -> None:
    """验证默认注册表包含颜色条件分支示例脚本。"""
    assert "conditional-color-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_wait_until_color_demo() -> None:
    """验证默认注册表包含条件等待示例脚本。"""
    assert "wait-until-color-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_conditional_screen_state_demo() -> None:
    """验证默认注册表包含界面状态条件分支示例脚本。"""
    assert "conditional-screen-state-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_wait_until_image_demo() -> None:
    """验证默认注册表包含图片条件等待示例脚本。"""
    assert "wait-until-image-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_wait_until_screen_state_demo() -> None:
    """验证默认注册表包含界面状态条件等待示例脚本。"""
    assert "wait-until-screen-state-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_click_image_demo() -> None:
    """验证默认注册表包含图片目标点击示例脚本。"""
    assert "click-image-demo" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_default_catalog_includes_leave_retry_loop() -> None:
    """验证默认注册表包含离开/重来轮询点击脚本。"""
    assert "click-leave-or-retry-loop" in DEFAULT_SCRIPT_CATALOG.list_names()


def test_project_catalog_includes_file_scripts(tmp_path) -> None:
    """验证项目 catalog 会合并用户脚本文件和内置脚本。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "user.json").write_text(
        '{"name": "用户脚本", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    base_catalog = ScriptCatalog((build_script("builtin"),))

    catalog = load_project_script_catalog(tmp_path, base_catalog=base_catalog)

    assert catalog.list_names() == ("builtin", "用户脚本")
    assert catalog.get("builtin").name == "builtin"
    assert catalog.get("用户脚本").name == "用户脚本"


def test_project_catalog_keeps_builtin_scripts_when_script_dir_missing(tmp_path) -> None:
    """验证项目脚本目录不存在时仍保留内置脚本。"""
    base_catalog = ScriptCatalog((build_script("builtin"),))

    catalog = load_project_script_catalog(tmp_path, base_catalog=base_catalog)

    assert catalog.list_names() == ("builtin",)


def test_project_catalog_rejects_duplicate_script_names(tmp_path) -> None:
    """验证文件脚本和内置脚本重名时返回可读错误。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "duplicate.json").write_text(
        '{"name": "builtin", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    base_catalog = ScriptCatalog((build_script("builtin"),))

    with pytest.raises(ValueError, match="duplicate script name: builtin"):
        load_project_script_catalog(tmp_path, base_catalog=base_catalog)
