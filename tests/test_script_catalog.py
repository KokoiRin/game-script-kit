"""验证命名脚本注册表的查询和错误处理。"""

import pytest

from game_automation.portable.scripts_manager.catalog import (
    DEFAULT_SCRIPT_CATALOG,
    ScriptCatalog,
    ScriptNotFoundError,
)
from game_automation.portable.application.config_script_loader import ScriptConfigError
from game_automation.portable.application.project_scripts import (
    load_project_script_catalog,
    load_project_script_catalog_result,
)
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


def test_default_catalog_contains_only_generic_examples() -> None:
    """默认注册表只暴露八个通用示例，不自动加载个人录制或特定应用配方。"""
    assert DEFAULT_SCRIPT_CATALOG.list_names() == (
        "demo",
        "repeat-demo",
        "conditional-color-demo",
        "conditional-screen-state-demo",
        "wait-until-color-demo",
        "wait-until-image-demo",
        "wait-until-screen-state-demo",
        "click-image-demo",
    )


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


def test_project_catalog_reports_duplicate_script_names(tmp_path) -> None:
    """验证文件脚本和内置脚本重名时隔离坏脚本并报告错误。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "duplicate.json").write_text(
        '{"name": "builtin", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    base_catalog = ScriptCatalog((build_script("builtin"),))

    result = load_project_script_catalog_result(tmp_path, base_catalog=base_catalog)

    assert result.catalog.list_names() == ("builtin",)
    assert result.script_config_errors == (
        ScriptConfigError("duplicate.json", "duplicate.json: duplicate script name: builtin"),
    )


def test_project_catalog_reports_bad_file_without_hiding_good_scripts(tmp_path) -> None:
    """验证坏文件不会影响其他文件脚本进入项目 catalog。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "good.json").write_text(
        '{"name": "good", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    (script_dir / "bad.json").write_text(
        '{"name": "bad", "steps": [{"drag": {}}]}',
        encoding="utf-8",
    )
    base_catalog = ScriptCatalog((build_script("builtin"),))

    result = load_project_script_catalog_result(tmp_path, base_catalog=base_catalog)

    assert result.catalog.list_names() == ("builtin", "good")
    assert result.script_config_errors == (
        ScriptConfigError("bad.json", "bad.json: unsupported step type: drag"),
    )


def test_project_catalog_binds_resource_images_without_mutating_base_catalog(tmp_path) -> None:
    """图片与搜索资源按各自数据根装配，绝对路径与共享基础定义保持原值。"""
    from game_automation.portable.domain import (
        ImageRef, ImageSearchSpec, ImageTemplate, NamedImage, NamedImageSearch,
        SearchRef, TargetCatalog,
    )

    absolute_template = ImageTemplate(str(tmp_path / "shared.png"))
    script = Script(
        name="arbitrary-resource-example", window=ScreenWindow(), steps=(Click(Point(1, 2)),),
        resources=TargetCatalog(
            images=(
                NamedImage("relative", ImageTemplate("assets/image.png")),
                NamedImage("absolute", absolute_template),
            ),
            searches=(
                NamedImageSearch("direct", ImageSearchSpec(ImageTemplate("assets/search.png"))),
                NamedImageSearch("alias", ImageSearchSpec(ImageRef("relative"))),
                NamedImageSearch("absolute", ImageSearchSpec(absolute_template)),
            ),
        ),
    )
    base_catalog = ScriptCatalog((script,))

    for root in (tmp_path / "first", tmp_path / "second"):
        loaded = load_project_script_catalog(root, base_catalog=base_catalog).get(script.name)
        assert loaded.resources.resolve_image(ImageRef("relative")).path == str(root / "assets/image.png")
        assert loaded.resources.resolve_search(SearchRef("direct")).image.path == str(root / "assets/search.png")
        assert loaded.resources.resolve_search(SearchRef("alias")).image.path == str(root / "assets/image.png")
        assert loaded.resources.resolve_image(ImageRef("absolute")) == absolute_template
        assert loaded.resources.resolve_search(SearchRef("absolute")).image == absolute_template

    assert script.resources.resolve_image(ImageRef("relative")).path == "assets/image.png"
    assert script.resources.resolve_search(SearchRef("direct")).image.path == "assets/search.png"


@pytest.mark.parametrize("script_name", ["click-image-demo", "wait-until-image-demo"])
def test_project_builtin_image_details_and_execution_share_root_outside_cwd(
    tmp_path, monkeypatch, script_name,
) -> None:
    """仓库外启动时，内置图片示例的详情与真实定位端口仍使用相同数据根。"""
    from pathlib import Path

    from game_automation.portable.application.script_details import describe_script_details
    from game_automation.portable.application.script_run import run_script
    from game_automation.portable.domain import ImageMatch, Rect

    root = tmp_path / "project"
    assets = root / "assets"
    assets.mkdir(parents=True)
    image = assets / "start.png"
    image.write_bytes(b"synthetic template")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    script = load_project_script_catalog(root).get(script_name)
    details = describe_script_details(
        script, asset_root=assets, supported_image_suffixes=frozenset({".png"}), state_names=(),
    )
    located = []
    clicks = []

    class FakeDevice:
        def click(self, point):
            """记录动作，图片找到后应正常推进。"""
            clicks.append(point)

    class CheckingLocator:
        def locate(self, template, **kwargs):
            """像真实适配器一样按收到的路径读取模板，不借用当前目录。"""
            located.append(template.path)
            if not Path(template.path).is_file():
                raise RuntimeError("template is not available at the runtime path")
            return ImageMatch(Rect(10, 20, 4, 6), 1.0)

    result = run_script(
        script, dry_run=False, real_device_factory=FakeDevice,
        real_image_locator_factory=CheckingLocator,
    )

    assert details.readiness[0][1] == "ok"
    assert result.finish_reason == "completed"
    assert details.image_dependencies == (str(image),)
    assert located == [str(image)]
    assert clicks
