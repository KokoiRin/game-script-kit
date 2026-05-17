"""验证命名脚本注册表的查询和错误处理。"""

import pytest

from game_automation.core import Click, Point, ScreenWindow, Script
from game_automation.core.script_catalog import ScriptCatalog, ScriptNotFoundError


def build_script(name: str) -> Script:
    """构造一个用于注册表测试的最小脚本。"""
    return Script(name=name, window=ScreenWindow(), actions=(Click(Point(1, 2)),))


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
