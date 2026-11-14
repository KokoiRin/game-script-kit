"""验证本地控制 UI 复用的应用层 interface。

这些测试覆盖 UI 和 CLI 之外的 application seam：脚本查找、运行结果捕获、
界面状态读取、取消和未完成结果。它不测试 HTTP 细节，也不直接绑定 engine 内部实现。
"""

import json
import time

import pytest

from game_automation.portable.application.local_control import (
    LocalControlApplication,
)
from game_automation.portable.application.screen_state_reader import (
    ProjectScreenStateReader,
)
from game_automation.portable.application.task_discovery import TaskLoadError
from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ImageMatch,
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    Point,
    Rect,
    RegionRef,
    ScreenWindow,
    TargetCatalog,
)
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
from tests.support.function_tasks import function_task


def test_local_control_runs_named_script_and_captures_dry_run_output() -> None:
    """验证 UI 用例可以按名称 dry-run 脚本并返回可展示输出。"""
    script = function_task(
        "sample",
        "ctx.click(Point(100, 200))\nctx.wait(0.25)",
        window=ScreenWindow(),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script("sample", dry_run=True)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "click Point(x=100, y=200)",
        "wait 0.25s",
    ]


def test_local_control_runs_state_script_with_dry_run_screen_state() -> None:
    """验证 UI 用例会把 dry-run 模拟状态传给状态条件脚本。"""
    script = function_task(
        "state-branch",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(Point(100, 200))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(
        "state-branch",
        dry_run=True,
        dry_run_screen_state="主页",
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == "click Point(x=100, y=200)\n"


def test_local_control_runs_image_script_with_dry_run_images() -> None:
    """验证 UI 用例可给 dry-run 图片脚本提供模拟命中模板。"""
    script = function_task(
        "image-click",
        "ctx.click(ImageTarget(ImageTemplate('assets/start.png')))",
        window=ScreenWindow(),
        templates=(ImageTemplate("assets/start.png"),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(
        "image-click",
        dry_run=True,
        dry_run_images=("assets/start.png",),
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=assets/start.png" in result.stdout
    assert result.stdout.splitlines()[-1] == "click Point(x=0, y=0)"


def test_local_control_runs_named_image_script_with_dry_run_images() -> None:
    """验证 UI 用例可用解析后的图片路径 dry-run 命名图片脚本。"""
    script = function_task(
        "named-image-click",
        "ctx.click(ImageTarget(ImageRef('离开')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)
        ),
        requires=TaskRequirements(images=("离开",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(
        "named-image-click",
        dry_run=True,
        dry_run_images=("assets/离开.png",),
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=assets/离开.png" in result.stdout
    assert result.stdout.splitlines()[-1] == "click Point(x=0, y=0)"


def test_local_control_runs_named_image_search_script_with_dry_run_images() -> None:
    """验证 UI 用例可用解析后的图片路径 dry-run 命名搜索脚本。"""
    script = function_task(
        "named-search-click",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮", ImageSearchSpec(ImageRef("离开"), min_confidence=0.8)
                ),
            ),
        ),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(
        "named-search-click",
        dry_run=True,
        dry_run_images=("assets/离开.png",),
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=assets/离开.png" in result.stdout
    assert result.stdout.splitlines()[-1] == "click Point(x=0, y=0)"


def test_local_control_runs_screen_state_search_ref_script_with_dry_run_images(
    tmp_path,
) -> None:
    """验证 UI 用例可用状态配置搜索别名 dry-run 脚本。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [
                            {
                                "name": "离开按钮",
                                "image": "离开.png",
                                "min_confidence": 0.75,
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "shared-search-click",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    result = app.run_named_script(
        "shared-search-click",
        dry_run=True,
        dry_run_images=(str(assets / "离开.png"),),
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=" in result.stdout
    assert str(assets / "离开.png") in result.stdout
    assert "min_confidence=0.75" in result.stdout
    assert result.stdout.splitlines()[-1] == "click Point(x=0, y=0)"


def test_local_control_describes_state_script_dependencies(tmp_path) -> None:
    """验证 UI 用例可以生成状态驱动脚本详情和可用依赖检查。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "主页",
                        "searches": [{"name": "主页标题", "image": "start.png"}],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "state-branch",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(ImageTarget(ImageTemplate('assets/start.png')))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
        templates=(ImageTemplate("assets/start.png"),),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("state-branch")

    assert details.exit_code == 0
    assert details.name == "state-branch"
    assert details.stderr == ""
    assert details.steps[0].startswith("Python run(ctx)")
    assert details.dependencies == ("状态: 主页", '图片: ImageRef("inline-0")')
    assert details.state_dependencies == ("主页",)
    assert details.image_dependencies == ("assets/start.png",)
    assert tuple(status for _, status, _ in details.readiness) == ("ok", "ok")


def test_local_control_describes_declared_states(tmp_path) -> None:
    """详情显示状态声明和函数入口。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "home.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "主页",
                        "searches": [{"name": "主页标题", "image": "home.png"}],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "state-wait",
        "ctx.wait_for(lambda: ctx.state(min_confidence=0.8) == '主页', timeout=1, interval=0.5)\n"
        "ctx.click(Point(100, 200))",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("state-wait")

    assert details.exit_code == 0
    assert details.state_dependencies == ("主页",)


def test_local_control_describes_point_dependencies() -> None:
    """验证脚本详情会结构化收集命名点位依赖并忽略裸坐标。"""
    script = function_task(
        "point-alias-script",
        "ctx.click(PointRef('头像'))\n"
        "for _ in range(2):\n"
        "    ctx.click(PointRef('头像'))\n"
        "    ctx.click(Point(100, 200))",
        window=ScreenWindow(),
        requires=TaskRequirements(points=("头像",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("point-alias-script")

    assert details.dependencies == ("点位: 头像",)
    assert details.point_dependencies == ("头像",)


@pytest.mark.parametrize("defined", [False, True])
def test_point_readiness_and_background_result_agree(tmp_path, defined) -> None:
    """详情检查与后台运行应一致报告点位是否已定义，且坏脚本不占住运行槽位。"""
    script = function_task(
        "point-check",
        "for _ in range(1):\n"
        "    ctx.click(OffsetTarget(PointRef('button'), Point(5, 0)))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            points=(NamedPoint("button", Point(10, 20)),) if defined else ()
        ),
        requires=TaskRequirements(points=("button",)),
    )
    valid = function_task("valid", "ctx.wait(0)", window=ScreenWindow())
    app = LocalControlApplication(
        catalog=ScriptCatalog((script, valid)), project_root=tmp_path
    )

    details = app.describe_script(script.name)
    assert details.exit_code == (0 if defined else 2)
    assert details.readiness == (
        (
            "点位: button",
            "ok" if defined else "missing",
            "点位已配置" if defined else "命名点位未配置",
        ),
    )

    app.start_named_script(script.name, dry_run=True)
    status = _wait_until_finished(app)
    assert (status.exit_code, status.finish_reason) == (
        (0, "completed") if defined else (2, "configuration_failed")
    )
    app.start_named_script(valid.name, dry_run=True)
    assert _wait_until_finished(app).finish_reason == "completed"


def test_local_control_describes_named_image_dependencies() -> None:
    """验证 UI 用例会把命名图片依赖解析成 dry-run 可用图片路径。"""
    script = function_task(
        "named-image-branch",
        "if ctx.find(ImageRef('离开'), min_confidence=None) is not None:\n"
        "    ctx.click(ImageTarget(ImageRef('重来')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(
                NamedImage("离开", ImageTemplate("assets/离开.png")),
                NamedImage("重来", ImageTemplate("assets/重来.png")),
            ),
        ),
        requires=TaskRequirements(images=("离开", "重来")),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("named-image-branch")

    assert details.image_dependencies == ("assets/离开.png", "assets/重来.png")


def test_local_control_describes_named_image_search_dependencies() -> None:
    """验证 UI 用例会把命名搜索依赖解析成 dry-run 可用图片路径。"""
    script = function_task(
        "named-search-branch",
        "if ctx.find(SearchRef('离开按钮'), min_confidence=None) is not None:\n"
        "    ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮", ImageSearchSpec(ImageRef("离开"), min_confidence=0.8)
                ),
            ),
        ),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("named-search-branch")

    assert details.dependencies == (
        '图片: ImageRef("离开")',
        '图片: SearchRef("离开按钮")',
    )
    assert details.image_dependencies == ("assets/离开.png",)


def test_local_control_describes_screen_state_search_ref_dependencies(tmp_path) -> None:
    """验证脚本详情可解析状态配置里的搜索别名。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [{"name": "离开按钮", "image": "离开.png"}],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "shared-search-details",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("shared-search-details")

    assert details.exit_code == 0
    assert details.image_dependencies == (str(assets / "离开.png"),)
    assert details.readiness == (
        (
            '图片: SearchRef("离开按钮")',
            "ok",
            f"命名搜索已配置，图片文件可用：{assets / '离开.png'}",
        ),
    )


def test_local_control_script_resources_override_screen_state_search_ref(
    tmp_path,
) -> None:
    """验证脚本自身搜索别名覆盖状态配置中的同名搜索。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "配置.png").write_bytes(b"fake")
    (assets / "脚本.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [{"name": "离开按钮", "image": "配置.png"}],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "local-search-override",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            searches=(
                NamedImageSearch(
                    "离开按钮", ImageSearchSpec(ImageTemplate("assets/脚本.png"))
                ),
            )
        ),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("local-search-override")

    assert details.image_dependencies == ("assets/脚本.png",)


@pytest.mark.parametrize(
    "config",
    [
        "{",
        json.dumps(
            {"groups": [{"state": "主页", "searches": [{"image": "missing.png"}]}]}
        ),
    ],
)
@pytest.mark.parametrize("kind", ["hotkey", "point", "image", "local-search", "state"])
def test_self_contained_scripts_ignore_unrelated_broken_state_config(
    tmp_path, config, kind
) -> None:
    """未依赖共享搜索的脚本不应因无关状态配置损坏而无法查看、模拟或运行。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    image_path = str(assets / "local.png")
    (assets / "local.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(config, encoding="utf-8")
    resources = TargetCatalog(
        points=(NamedPoint("button", Point(10, 20)),),
        images=(NamedImage("local", ImageTemplate(image_path)),),
        regions=(NamedRegion("area", Rect(0, 0, 100, 100)),),
        searches=(
            NamedImageSearch(
                "local-search", ImageSearchSpec(ImageRef("local"), RegionRef("area"))
            ),
        ),
    )
    bodies = {
        "hotkey": 'ctx.hotkey("command", "v")',
        "point": 'ctx.click("button")',
        "image": 'ctx.click_image("local")',
        "local-search": 'ctx.click_image("local-search")',
        "state": 'if ctx.state() == "主页":\n    ctx.wait(0)',
    }
    script = function_task(
        kind,
        bodies[kind],
        resources=resources,
        requires=TaskRequirements(states=("主页",) if kind == "state" else ()),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    assert app.describe_script(script.name).exit_code == 0
    result = app.run_named_script(
        script.name, dry_run=True, dry_run_images=(image_path,)
    )
    assert (result.exit_code, result.finish_reason) == (0, "completed")
    app.start_named_script(script.name, dry_run=True, dry_run_images=(image_path,))
    assert _wait_until_finished(app).finish_reason == "completed"


def test_shared_search_still_reports_broken_required_config(tmp_path) -> None:
    """实际依赖共享搜索时仍须报告配置错误，不能把坏配置当作图片未命中。"""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "screen-states.json").write_text("{")
    script = function_task(
        "shared",
        "ctx.click(ImageTarget(SearchRef('shared')))",
        window=ScreenWindow(),
        requires=TaskRequirements(searches=("shared",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    result = app.run_named_script(script.name, dry_run=True)

    assert (result.exit_code, result.finish_reason) == (2, "configuration_failed")
    assert "invalid screen state config json" in result.stderr


def test_local_control_checks_named_image_readiness(tmp_path) -> None:
    """验证命名图片依赖会按解析后的 assets 路径检查可用性。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    script = function_task(
        "named-image-ready",
        "ctx.click(ImageTarget(ImageRef('离开')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)
        ),
        requires=TaskRequirements(images=("离开",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("named-image-ready")

    assert details.readiness == (
        (
            '图片: ImageRef("离开")',
            "ok",
            "命名图片已配置，图片文件可用：assets/离开.png",
        ),
    )


def test_local_control_checks_named_image_search_readiness(tmp_path) -> None:
    """验证命名搜索依赖会按解析后的 assets 路径检查可用性。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    script = function_task(
        "named-search-ready",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮", ImageSearchSpec(ImageRef("离开"), min_confidence=0.8)
                ),
            ),
        ),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("named-search-ready")

    assert details.readiness == (
        (
            '图片: ImageRef("离开")',
            "ok",
            "命名图片已配置，图片文件可用：assets/离开.png",
        ),
        (
            '图片: SearchRef("离开按钮")',
            "ok",
            "命名搜索已配置，图片文件可用：assets/离开.png",
        ),
    )


def test_local_control_reports_missing_named_image_file(tmp_path) -> None:
    """验证命名图片已配置但文件缺失时会报告缺失。"""
    (tmp_path / "assets").mkdir()
    script = function_task(
        "named-image-missing-file",
        "ctx.click(ImageTarget(ImageRef('离开')))",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)
        ),
        requires=TaskRequirements(images=("离开",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("named-image-missing-file")

    assert details.readiness == (
        (
            '图片: ImageRef("离开")',
            "missing",
            "命名图片已配置，但图片文件不存在或后缀不受支持：assets/离开.png",
        ),
    )


def test_local_control_ignores_unknown_named_image_dependency() -> None:
    """验证未知命名图片不会被伪造成 dry-run 图片路径。"""
    script = function_task(
        "unknown-named-image",
        "ctx.click(ImageTarget(ImageRef('缺失')))",
        window=ScreenWindow(),
        requires=TaskRequirements(images=("缺失",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-image")

    assert details.image_dependencies == ()


def test_local_control_reports_unknown_named_image_readiness() -> None:
    """验证未知命名图片依赖会报告命名图片未配置。"""
    script = function_task(
        "unknown-named-image",
        "ctx.click(ImageTarget(ImageRef('缺失')))",
        window=ScreenWindow(),
        requires=TaskRequirements(images=("缺失",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-image")

    assert details.readiness == (
        ('图片: ImageRef("缺失")', "missing", "命名图片未配置"),
    )


def test_local_control_reports_unknown_named_image_search_readiness() -> None:
    """验证未知命名搜索依赖会报告命名搜索未配置。"""
    script = function_task(
        "unknown-named-search",
        "ctx.click(ImageTarget(SearchRef('缺失搜索')))",
        window=ScreenWindow(),
        requires=TaskRequirements(searches=("缺失搜索",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-search")

    assert details.readiness == (
        ('图片: SearchRef("缺失搜索")', "missing", "命名搜索未配置"),
    )


def test_local_control_describes_missing_script_dependencies(tmp_path) -> None:
    """验证 UI 用例会标出缺失图片和无法确认的状态依赖。"""
    script = function_task(
        "state-branch",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(ImageTarget(ImageTemplate('assets/start.png')))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
        templates=(ImageTemplate("assets/start.png"),),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    details = app.describe_script("state-branch")

    assert details.readiness == (
        ("状态: 主页", "unknown", "状态配置不可用，无法确认"),
        (
            '图片: ImageRef("inline-0")',
            "missing",
            "命名图片已配置，但图片文件不存在或后缀不受支持：assets/start.png",
        ),
    )


def test_local_control_describes_unknown_script() -> None:
    """验证未知脚本详情请求返回清晰错误。"""
    app = LocalControlApplication(
        catalog=ScriptCatalog((_build_state_branch_script(),))
    )

    details = app.describe_script("missing")

    assert details.exit_code == 1
    assert details.name == "missing"
    assert details.steps == ()
    assert details.dependencies == ()
    assert details.state_dependencies == ()
    assert details.image_dependencies == ()
    assert details.readiness == ()
    assert details.stderr == "unknown script: missing"


def test_local_control_background_state_script_uses_dry_run_screen_state() -> None:
    """验证后台脚本运行也会使用 dry-run 模拟状态。"""
    script = function_task(
        "state-branch",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(Point(100, 200))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    app.start_named_script(
        "state-branch",
        dry_run=True,
        dry_run_screen_state="主页",
    )
    final = _wait_until_finished(app)

    assert final.exit_code == 0
    assert final.finish_reason == "completed"
    assert final.stderr == ""
    assert "script event type=run_started" in final.stdout
    assert "step=Observe status=succeeded" in final.stdout
    assert "click Point(x=100, y=200)" in final.stdout
    assert "script event type=run_finished status=completed exit_code=0" in final.stdout
    assert [event.event_type for event in final.events][:2] == [
        "run_started",
        "step_started",
    ]


def test_local_control_background_run_uses_screen_state_search_ref(tmp_path) -> None:
    """验证后台脚本运行也会合并状态配置搜索别名。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [
                            {
                                "name": "离开按钮",
                                "image": "离开.png",
                                "min_confidence": 0.75,
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = function_task(
        "shared-search-background",
        "ctx.click(ImageTarget(SearchRef('离开按钮')))",
        window=ScreenWindow(),
        requires=TaskRequirements(searches=("离开按钮",)),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    app.start_named_script(
        "shared-search-background",
        dry_run=True,
        dry_run_images=(str(assets / "离开.png"),),
    )
    final = _wait_until_finished(app)

    assert final.exit_code == 0
    assert final.finish_reason == "completed"
    assert final.stderr == ""
    assert str(assets / "离开.png") in final.stdout
    assert "min_confidence=0.75" in final.stdout
    assert "click Point(x=0, y=0)" in final.stdout


def test_local_control_can_stop_background_script_run() -> None:
    """验证 UI application 可以取消后台运行中的脚本。"""
    script = function_task(
        "long-loop",
        "for _ in range(1000):\n    ctx.wait(0.01)",
        window=ScreenWindow(),
    )

    class SlowDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(
            self, start: Point, end: Point, duration_seconds: float = 0.0
        ) -> None:
            """本测试不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """短暂等待，让后台线程保持运行并允许停止请求进入。"""
            time.sleep(duration_seconds)

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        real_device_factory=SlowDevice,
    )

    started = app.start_named_script("long-loop", dry_run=False)
    assert started.running is True

    stopped = app.stop_running_script()
    assert stopped.running is True

    final = _wait_until_finished(app)
    assert final.running is False
    assert final.exit_code == 130
    assert final.finish_reason == "cancelled"
    assert "script run cancelled" in final.stderr


def test_local_control_rejects_second_background_script_while_running() -> None:
    """验证已有后台脚本运行时不会启动第二个脚本。"""
    script = function_task(
        "long-loop",
        "for _ in range(1000):\n    ctx.wait(0.01)",
        window=ScreenWindow(),
    )

    class SlowDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(
            self, start: Point, end: Point, duration_seconds: float = 0.0
        ) -> None:
            """本测试不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """短暂等待，让后台线程保持运行。"""
            time.sleep(duration_seconds)

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        real_device_factory=SlowDevice,
    )

    app.start_named_script("long-loop", dry_run=False)
    duplicate = app.start_named_script("long-loop", dry_run=False)
    app.stop_running_script()

    final = _wait_until_finished(app)
    assert duplicate.running is True
    assert duplicate.finish_reason == "running"
    assert "script is already running" in duplicate.stderr
    assert final.exit_code == 130
    assert final.finish_reason == "cancelled"


def test_local_control_background_status_includes_image_match_logs() -> None:
    """验证后台脚本状态会展示图片匹配耗时日志。"""
    script = function_task(
        "image-loop",
        "ctx.wait_for(lambda: ctx.find(ImageTemplate('assets/start.png'), min_confidence=0.8) is not None, timeout=1, interval=0.1)",
        window=ScreenWindow(),
        templates=(ImageTemplate("assets/start.png"),),
    )

    class FakeDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(
            self, start: Point, end: Point, duration_seconds: float = 0.0
        ) -> None:
            """本测试不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """本测试中的条件会立即满足，不需要等待。"""

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """返回固定图片匹配。"""
            return ImageMatch(Rect(10, 20, 30, 40), confidence=0.91)

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        real_device_factory=FakeDevice,
        real_image_locator_factory=FakeImageLocator,
    )

    app.start_named_script("image-loop", dry_run=False)
    final = _wait_until_finished(app)

    assert final.exit_code == 0
    assert final.finish_reason == "completed"
    assert "image match template=assets/start.png" in final.stdout
    assert "found=True" in final.stdout
    assert "confidence=0.91" in final.stdout
    assert any(event.event_type == "step_succeeded" for event in final.events)


def test_local_control_runs_script_with_screen_state_condition(tmp_path) -> None:
    """验证本地控制真实脚本可通过状态探测判断当前界面。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "主页.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "regions": {
                    "主页标题": {"left": 10, "top": 20, "width": 120, "height": 40}
                },
                "groups": [
                    {
                        "state": "主页",
                        "searches": [
                            {
                                "name": "主页标题",
                                "image": "主页.png",
                                "region": "主页标题",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    clicks = []
    batch_requests = []
    script = function_task(
        "state-aware",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(Point(100, 200))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )

    class FakeDevice(InputDevice):
        def click(self, target: Point) -> None:
            """记录真实点击坐标。"""
            clicks.append(target)

        def drag_to(
            self, start: Point, end: Point, duration_seconds: float = 0.0
        ) -> None:
            """状态分支脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """状态命中后不会等待。"""

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """记录状态探测请求并返回主页命中。"""
            batch_requests.append((requests, stop_on_first_match))
            return (
                ImageBatchMatchResult(
                    requests[0].template,
                    ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                    elapsed_ms=4.0,
                ),
            )

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        project_root=tmp_path,
        real_device_factory=FakeDevice,
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    result = app.run_named_script("state-aware", dry_run=False)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert clicks == [Point(100, 200)]
    assert len(batch_requests) == 1
    requests, stop_on_first_match = batch_requests[0]
    assert stop_on_first_match is True
    assert requests[0].region == Rect(10, 20, 120, 40)
    assert "screen state probe round current_state=主页" in result.stdout


def test_local_control_lists_screen_state_names_from_config(tmp_path) -> None:
    """验证 UI 用例按配置顺序列出界面状态并去重。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "groups": [
            {"state": "主页", "searches": []},
            {"state": "人物", "searches": []},
            {"state": "主页", "searches": []}
          ]
        }
        """,
        encoding="utf-8",
    )

    app = LocalControlApplication(project_root=tmp_path)

    assert app.list_screen_state_names() == ("主页", "人物")


def test_local_control_lists_no_screen_state_names_without_config(tmp_path) -> None:
    """验证缺少状态配置时 UI 状态候选为空。"""
    (tmp_path / "assets").mkdir()
    app = LocalControlApplication(project_root=tmp_path)

    assert app.list_screen_state_names() == ()


def test_local_control_lists_no_screen_state_names_for_invalid_config(tmp_path) -> None:
    """验证非法状态配置不会阻断 UI 初始化。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text('{"groups": "bad"}', encoding="utf-8")
    app = LocalControlApplication(project_root=tmp_path)

    assert app.list_screen_state_names() == ()


def _wait_until_finished(app: LocalControlApplication):
    """轮询等待后台脚本结束，避免测试绑定具体线程调度。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_script_run()
        if not status.running:
            return status
        time.sleep(0.01)
    raise AssertionError("background script did not finish")


@pytest.mark.parametrize("failure_stage", ["setup", "action"])
def test_background_unexpected_failure_finishes_and_allows_next_run(
    tmp_path, failure_stage
) -> None:
    """平台初始化或动作抛出意外异常时会话必须结束，并允许再次运行。"""

    class FailingDevice(InputDevice):
        def wait(self, duration_seconds: float) -> None:
            """模拟未被平台包装的系统错误。"""
            raise OSError("device disconnected")

    def build_device():
        """按测试场景在初始化时失败或返回动作失败的设备。"""
        if failure_stage == "setup":
            raise OSError("device disconnected")
        return FailingDevice()

    script = function_task("sample", "ctx.wait(0)", window=ScreenWindow())
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        project_root=tmp_path,
        real_device_factory=build_device,
    )

    app.start_named_script(script.name, dry_run=False)
    status = _wait_until_finished(app)

    assert status.exit_code == 1
    assert status.finish_reason == (
        "setup_failed" if failure_stage == "setup" else "failed"
    )
    assert "device disconnected" in status.stderr
    assert status.events[-1].event_type == "run_finished"
    assert status.events[-1].status == status.finish_reason

    app.start_named_script(script.name, dry_run=True)
    assert _wait_until_finished(app).finish_reason == "completed"


def test_background_session_finishes_when_run_use_case_raises(
    tmp_path, monkeypatch
) -> None:
    """后台会话在用例出现未归一化异常时仍须结束并保留诊断。"""
    from game_automation.portable.application import local_control

    def broken_run(*args, **kwargs):
        """模拟运行用例自身发生意外错误。"""
        raise ValueError("unexpected run error")

    monkeypatch.setattr(local_control, "run_script", broken_run)
    script = function_task("sample", "ctx.wait(0)", window=ScreenWindow())
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )

    app.start_named_script(script.name, dry_run=True)
    status = _wait_until_finished(app)

    assert (status.exit_code, status.finish_reason) == (1, "failed")
    assert "unexpected run error" in status.stderr
    assert status.events[-1].event_type == "run_finished"


def test_stopping_a_long_wait_joins_the_background_thread(tmp_path) -> None:
    """关闭桌面应用时长等待应迅速响应取消，且可等待实际线程回收。"""
    import threading

    entered = threading.Event()

    class WaitingDevice(InputDevice):
        def wait(self, duration_seconds):
            """保留真实等待语义，记录已经进入等待。"""
            entered.set()
            time.sleep(duration_seconds)

    script = function_task("long-wait", "ctx.wait(60)", window=ScreenWindow())
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        project_root=tmp_path,
        real_device_factory=WaitingDevice,
    )
    app.start_named_script(script.name, dry_run=False)
    assert entered.wait(1)
    app.stop_running_script()
    assert app.wait_for_script_stop(timeout=1)
    assert app.current_script_run().finish_reason == "cancelled"


def test_long_run_keeps_recent_logs_and_events_bounded(tmp_path) -> None:
    """长期运行只保留有界日志和近期事件，并保留最终结束原因。"""
    script = function_task(
        "many-steps",
        "for _ in range(3000):\n    ctx.wait(0)",
        window=ScreenWindow(),
    )
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path
    )
    app.start_named_script(script.name, dry_run=True)
    assert app.wait_for_script_stop(timeout=3)
    status = app.current_script_run()
    assert len(status.stdout) <= 262144
    assert len(status.events) <= 2048
    assert status.events[-1].event_type == "run_finished"
    assert status.finish_reason == "completed"


def _write_home_state_config(project_root) -> None:
    """写入只包含主页状态的测试配置。"""
    assets = project_root / "assets"
    assets.mkdir()
    (assets / "主页.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "主页",
                        "searches": [{"name": "主页标题", "image": "主页.png"}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _build_state_branch_script() -> FunctionTask:
    """构造命中主页状态时点击的测试脚本。"""
    return function_task(
        "state-aware",
        "if ctx.state(min_confidence=0.8) == '主页':\n"
        "    ctx.click(Point(100, 200))\n"
        "else:\n"
        "    ctx.wait(0.5)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )


def test_local_control_lists_scripts_and_isolated_config_errors() -> None:
    """脚本列表与坏配置报告保留供入口展示，坏文件不阻断好脚本。"""
    script = function_task("sample", "ctx.wait(0)", window=ScreenWindow())
    error = TaskLoadError("bad.json", "steps must not be empty")
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        script_config_errors=(error,),
    )

    assert app.list_scripts() == ("sample",)
    assert app.list_script_config_errors() == (error,)
    assert app.run_named_script("sample", dry_run=True).finish_reason == "completed"


def test_local_control_unknown_script_has_explicit_finish_reason() -> None:
    """同步和后台入口均把未知脚本作为未启动的错误结果返回。"""
    app = LocalControlApplication(catalog=ScriptCatalog(()))

    result = app.run_named_script("missing", dry_run=True)
    status = app.start_named_script("missing", dry_run=True)

    assert result.exit_code == status.exit_code == 1
    assert result.finish_reason == status.finish_reason == "script_not_found"
    assert "unknown script: missing" in result.stderr
    assert not status.running


def test_local_control_unmet_condition_is_not_reported_as_completed() -> None:
    """等待目标未满足时，同步和后台均保留正常停止原因并跳过后续点击。"""
    script = function_task(
        "wait-for-image",
        "ctx.wait_for(lambda: ctx.find(ImageTemplate('missing.png'), min_confidence=None) is not None, timeout=0.1, interval=0.1)\n"
        "ctx.click(Point(10, 20))",
        window=ScreenWindow(),
        templates=(ImageTemplate("missing.png"),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(script.name, dry_run=True)
    app.start_named_script(script.name, dry_run=True)
    status = _wait_until_finished(app)

    assert result.exit_code == status.exit_code == 1
    assert result.finish_reason == status.finish_reason == "timed_out"
    assert "click Point" not in result.stdout
    assert "click Point" not in status.stdout


def test_local_control_runtime_failure_is_exposed_in_both_entry_modes() -> None:
    """真实设备动作失败时，同步与后台结果都明确失败并包含原始原因。"""
    script = function_task("failing", "ctx.click(Point(10, 20))", window=ScreenWindow())

    class FailingDevice:
        def click(self, target):
            """模拟真实输入设备不可用。"""
            raise RuntimeError("input permission denied")

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        real_device_factory=FailingDevice,
    )

    result = app.run_named_script(script.name, dry_run=False)
    app.start_named_script(script.name, dry_run=False)
    status = _wait_until_finished(app)

    assert result.exit_code == status.exit_code == 1
    assert result.finish_reason == status.finish_reason == "failed"
    assert "input permission denied" in result.stderr
    assert "input permission denied" in status.stderr


def test_project_state_reader_reads_current_frame_each_time(tmp_path) -> None:
    """状态读取每次识别当前画面，上一轮主页命中不会掩盖随后的消失。"""
    _write_home_state_config(tmp_path)
    matches = iter((ImageMatch(Rect(0, 0, 20, 20), 0.9), None))

    class ChangingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """依次返回主页出现与消失的画面。"""
            return next(matches)

    locator = ChangingLocator()
    reader = ProjectScreenStateReader(
        project_root=tmp_path,
        real_image_locator_factory=lambda: locator,
    )

    assert reader.read_current_state() == "主页"
    assert reader.read_current_state() == "未知"


def test_project_state_reader_reloads_configuration_each_time(tmp_path) -> None:
    """运行中的状态配置更名后，下一次读取立即采用新状态名称。"""
    _write_home_state_config(tmp_path)

    class MatchingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """始终命中相同模板，使状态名称只来自当前配置。"""
            return ImageMatch(Rect(0, 0, 20, 20), 0.9)

    reader = ProjectScreenStateReader(
        project_root=tmp_path,
        real_image_locator_factory=MatchingLocator,
    )
    assert reader.read_current_state() == "主页"
    config_path = tmp_path / "assets" / "screen-states.json"
    config = json.loads(config_path.read_text())
    config["groups"][0]["state"] = "新主页"
    config_path.write_text(json.dumps(config))

    assert reader.read_current_state() == "新主页"


def test_project_state_reader_without_config_preserves_template_name_fallback(
    tmp_path,
) -> None:
    """未建立状态配置的旧项目仍可按 assets 模板文件名识别状态。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "主页.png").write_bytes(b"fake")

    class MatchingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """命中模板文件名对应的状态。"""
            return ImageMatch(Rect(0, 0, 20, 20), 0.9)

    reader = ProjectScreenStateReader(
        project_root=tmp_path,
        real_image_locator_factory=MatchingLocator,
    )

    assert reader.read_current_state() == "主页"


def test_local_control_live_invalid_state_config_finishes_with_failure(
    tmp_path,
) -> None:
    """等待期间状态配置损坏时返回失败结果，不让后台会话永远停在运行中。"""
    _write_home_state_config(tmp_path)
    config_path = tmp_path / "assets" / "screen-states.json"
    original_config = config_path.read_text()
    script = function_task(
        "state-wait",
        "ctx.wait_for(lambda: ctx.state(min_confidence=0.8) == '主页', timeout=1, interval=0.1)",
        window=ScreenWindow(),
        requires=TaskRequirements(states=("主页",)),
    )

    class MutatingDevice:
        def wait(self, duration_seconds):
            """模拟用户在等待两次识别之间保存了非法配置。"""
            config_path.write_text("{")

    class MissingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """初次读取不命中，进入等待后再读取配置。"""
            return None

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)),
        project_root=tmp_path,
        real_device_factory=MutatingDevice,
        real_image_locator_factory=MissingLocator,
    )

    result = app.run_named_script(script.name, dry_run=False)
    assert result.exit_code == 1
    assert result.finish_reason == "failed"
    assert "screen state configuration failed" in result.stderr

    config_path.write_text(original_config)
    app.start_named_script(script.name, dry_run=False)
    status = _wait_until_finished(app)
    assert status.exit_code == 1
    assert status.finish_reason == "failed"
    assert "screen state configuration failed" in status.stderr


def test_project_state_reader_reports_missing_locator() -> None:
    """未装配识图能力时，状态读取明确报告配置缺失而非伪造未知。"""
    with pytest.raises(RuntimeError, match="image locator is required"):
        ProjectScreenStateReader().read_current_state()
