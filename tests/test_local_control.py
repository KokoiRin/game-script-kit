"""验证本地控制 UI 复用的应用层 interface。

这些测试覆盖 UI 和 CLI 之外的 application seam：脚本查找、运行结果捕获、
界面状态读取、取消和未完成结果。它不测试 HTTP 细节，也不直接绑定 engine 内部实现。
"""

import json
import time

import pytest

from game_automation.portable.domain import (
    Click,
    If,
    ImageBatchMatchResult,
    ImageExists,
    ImageRef,
    ImageMatch,
    ImageSearchSpec,
    ImageTarget,
    ImageTemplate,
    NamedPoint,
    NamedImage,
    NamedImageSearch,
    Point,
    PointRef,
    Rect,
    SearchRef,
    Repeat,
    ScreenStateIs,
    ScreenWindow,
    Script,
    TargetCatalog,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.application.local_control import (
    LocalControlApplication,
)
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


from game_automation.portable.application.config_script_loader import ScriptConfigError
from game_automation.portable.application.screen_state_reader import ProjectScreenStateReader
def test_local_control_runs_named_script_and_captures_dry_run_output() -> None:
    """验证 UI 用例可以按名称 dry-run 脚本并返回可展示输出。"""
    script = Script(
        name="sample",
        window=ScreenWindow(),
        steps=(Click(Point(100, 200)), Wait(0.25)),
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
    script = Script(
        name="state-branch",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(100, 200)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(
        "state-branch",
        dry_run=True,
        dry_run_screen_state="主页",
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == (
        "screen state condition expected=主页 actual=主页 min_confidence=0.8 matched=True\n"
        "click Point(x=100, y=200)\n"
    )


def test_local_control_runs_image_script_with_dry_run_images() -> None:
    """验证 UI 用例可给 dry-run 图片脚本提供模拟命中模板。"""
    script = Script(
        name="image-click",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageTemplate("assets/start.png"))),),
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
    script = Script(
        name="named-image-click",
        window=ScreenWindow(),
        resources=TargetCatalog(images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)),
        steps=(Click(ImageTarget(ImageRef("离开"))),),
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
    script = Script(
        name="named-search-click",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮",
                    ImageSearchSpec(ImageRef("离开"), min_confidence=0.8),
                ),
            ),
        ),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
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


def test_local_control_runs_screen_state_search_ref_script_with_dry_run_images(tmp_path) -> None:
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
    script = Script(
        name="shared-search-click",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

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
            {"groups": [{"state": "主页", "searches": [{"name": "主页标题", "image": "start.png"}]}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="state-branch",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(ImageTarget(ImageTemplate("assets/start.png"))),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("state-branch")

    assert details.exit_code == 0
    assert details.name == "state-branch"
    assert details.stderr == ""
    assert any('If ScreenStateIs("主页")' in step for step in details.steps)
    assert details.dependencies == ("状态: 主页", "图片: assets/start.png")
    assert details.state_dependencies == ("主页",)
    assert details.image_dependencies == ("assets/start.png",)
    assert details.state_decisions == (
        (
            "主页",
            ("Click ImageTarget(assets/start.png, min_confidence=1)",),
            ("Wait 0.5s",),
        ),
    )
    assert details.readiness == (
        ("状态: 主页", "ok", "状态已配置"),
        ("图片: assets/start.png", "ok", "图片文件可用"),
    )


def test_local_control_describes_screen_state_waits(tmp_path) -> None:
    """验证 UI 用例会把状态等待收集为结构化详情。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "home.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {"groups": [{"state": "主页", "searches": [{"name": "主页标题", "image": "home.png"}]}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="state-wait",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ScreenStateIs("主页"),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
            Click(Point(100, 200)),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("state-wait")

    assert details.exit_code == 0
    assert details.state_waits == ("主页",)
    assert details.state_dependencies == ("主页",)
    assert details.state_decisions == ()


def test_local_control_describes_point_dependencies() -> None:
    """验证脚本详情会结构化收集命名点位依赖并忽略裸坐标。"""
    script = Script(
        name="point-alias-script",
        window=ScreenWindow(),
        steps=(
            Click(PointRef("头像")),
            Repeat(times=2, steps=(Click(PointRef("头像")), Click(Point(100, 200)))),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("point-alias-script")

    assert details.dependencies == ("点位: 头像",)
    assert details.point_dependencies == ("头像",)


@pytest.mark.parametrize("configured", [False, True])
def test_local_control_checks_point_readiness(tmp_path, configured) -> None:
    """详情应按资源目录标明嵌套偏移点位是否已配置，并将重复引用合并为一项检查。"""
    points = (NamedPoint("头像", Point(10, 20)),) if configured else ()
    script = Script(
        "point-readiness", ScreenWindow(),
        (Repeat(1, (Click(PointRef("头像").offset(x=5)), Click(PointRef("头像")))),),
        resources=TargetCatalog(points=points),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script(script.name)

    expected = ("点位: 头像", "ok", "点位已配置") if configured else (
        "点位: 头像", "missing", "点位未配置",
    )
    assert details.readiness == (expected,)


def test_local_control_describes_named_image_dependencies() -> None:
    """验证 UI 用例会把命名图片依赖解析成 dry-run 可用图片路径。"""
    script = Script(
        name="named-image-branch",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(
                NamedImage("离开", ImageTemplate("assets/离开.png")),
                NamedImage("重来", ImageTemplate("assets/重来.png")),
            ),
        ),
        steps=(
            If(
                condition=ImageExists(ImageRef("离开")),
                then_steps=(Click(ImageTarget(ImageRef("重来"))),),
            ),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("named-image-branch")

    assert details.image_dependencies == ("assets/离开.png", "assets/重来.png")


def test_local_control_describes_named_image_search_dependencies() -> None:
    """验证 UI 用例会把命名搜索依赖解析成 dry-run 可用图片路径。"""
    script = Script(
        name="named-search-branch",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮",
                    ImageSearchSpec(ImageRef("离开"), min_confidence=0.8),
                ),
            ),
        ),
        steps=(
            If(
                condition=ImageExists(SearchRef("离开按钮")),
                then_steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
            ),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("named-search-branch")

    assert details.dependencies == ('图片: SearchRef("离开按钮")',)
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
    script = Script(
        name="shared-search-details",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

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


def test_local_control_script_resources_override_screen_state_search_ref(tmp_path) -> None:
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
    script = Script(
        name="local-search-override",
        window=ScreenWindow(),
        resources=TargetCatalog(
            searches=(
                NamedImageSearch(
                    "离开按钮",
                    ImageSearchSpec(ImageTemplate("assets/脚本.png")),
                ),
            ),
        ),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("local-search-override")

    assert details.image_dependencies == ("assets/脚本.png",)


def test_local_control_checks_named_image_readiness(tmp_path) -> None:
    """验证命名图片依赖会按解析后的 assets 路径检查可用性。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    script = Script(
        name="named-image-ready",
        window=ScreenWindow(),
        resources=TargetCatalog(images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)),
        steps=(Click(ImageTarget(ImageRef("离开"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("named-image-ready")

    assert details.readiness == (
        ('图片: ImageRef("离开")', "ok", "命名图片已配置，图片文件可用：assets/离开.png"),
    )


def test_local_control_checks_named_image_search_readiness(tmp_path) -> None:
    """验证命名搜索依赖会按解析后的 assets 路径检查可用性。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    script = Script(
        name="named-search-ready",
        window=ScreenWindow(),
        resources=TargetCatalog(
            images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
            searches=(
                NamedImageSearch(
                    "离开按钮",
                    ImageSearchSpec(ImageRef("离开"), min_confidence=0.8),
                ),
            ),
        ),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("named-search-ready")

    assert details.readiness == (
        ('图片: SearchRef("离开按钮")', "ok", "命名搜索已配置，图片文件可用：assets/离开.png"),
    )


def test_local_control_reports_missing_named_image_file(tmp_path) -> None:
    """验证命名图片已配置但文件缺失时会报告缺失。"""
    (tmp_path / "assets").mkdir()
    script = Script(
        name="named-image-missing-file",
        window=ScreenWindow(),
        resources=TargetCatalog(images=(NamedImage("离开", ImageTemplate("assets/离开.png")),)),
        steps=(Click(ImageTarget(ImageRef("离开"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("named-image-missing-file")

    assert details.readiness == (
        ('图片: ImageRef("离开")', "missing", "命名图片已配置，但图片文件不存在或后缀不受支持：assets/离开.png"),
    )


def test_local_control_ignores_unknown_named_image_dependency() -> None:
    """验证未知命名图片不会被伪造成 dry-run 图片路径。"""
    script = Script(
        name="unknown-named-image",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageRef("缺失"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-image")

    assert details.image_dependencies == ()


def test_local_control_reports_unknown_named_image_readiness() -> None:
    """验证未知命名图片依赖会报告命名图片未配置。"""
    script = Script(
        name="unknown-named-image",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageRef("缺失"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-image")

    assert details.readiness == (
        ('图片: ImageRef("缺失")', "missing", "命名图片未配置"),
    )


def test_local_control_reports_unknown_named_image_search_readiness() -> None:
    """验证未知命名搜索依赖会报告命名搜索未配置。"""
    script = Script(
        name="unknown-named-search",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("缺失搜索"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    details = app.describe_script("unknown-named-search")

    assert details.readiness == (
        ('图片: SearchRef("缺失搜索")', "missing", "命名搜索未配置"),
    )


def test_local_control_describes_missing_script_dependencies(tmp_path) -> None:
    """验证 UI 用例会标出缺失图片和无法确认的状态依赖。"""
    script = Script(
        name="state-branch",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(ImageTarget(ImageTemplate("assets/start.png"))),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

    details = app.describe_script("state-branch")

    assert details.readiness == (
        ("状态: 主页", "unknown", "状态配置不可用，无法确认"),
        ("图片: assets/start.png", "missing", "图片文件不存在或后缀不受支持"),
    )


def test_local_control_describes_unknown_script() -> None:
    """验证未知脚本详情请求返回清晰错误。"""
    app = LocalControlApplication(catalog=ScriptCatalog((_build_state_branch_script(),)))

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
    script = Script(
        name="state-branch",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(100, 200)),),
                else_steps=(Wait(0.5),),
            ),
        ),
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
    assert "script event type=condition_evaluated path=1 step=If result=True branch=then" in final.stdout
    assert "screen state condition expected=主页 actual=主页 min_confidence=0.8 matched=True" in final.stdout
    assert "click Point(x=100, y=200)" in final.stdout
    assert "script event type=run_finished status=completed exit_code=0" in final.stdout
    assert [event.event_type for event in final.events][:2] == ["run_started", "step_started"]


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
    script = Script(
        name="shared-search-background",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path)

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
    script = Script(
        name="long-loop",
        window=ScreenWindow(),
        steps=(Repeat(times=1000, steps=(Wait(0.01),)),),
    )

    class SlowDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
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
    script = Script(
        name="long-loop",
        window=ScreenWindow(),
        steps=(Repeat(times=1000, steps=(Wait(0.01),)),),
    )

    class SlowDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
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
    script = Script(
        name="image-loop",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ImageExists(ImageTemplate("assets/start.png"), min_confidence=0.8),
                timeout_seconds=1,
                interval_seconds=0.1,
            ),
        ),
    )

    class FakeDevice(InputDevice):
        def click(self, target: Point) -> None:
            """本测试不会点击。"""

        def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
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
                            {"name": "主页标题", "image": "主页.png", "region": "主页标题"}
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
    script = Script(
        name="state-aware",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(100, 200)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    class FakeDevice(InputDevice):
        def click(self, target: Point) -> None:
            """记录真实点击坐标。"""
            clicks.append(target)

        def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
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


def _build_state_branch_script() -> Script:
    """构造命中主页状态时点击的测试脚本。"""
    return Script(
        name="state-aware",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(100, 200)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )



def test_local_control_lists_scripts_and_isolated_config_errors() -> None:
    """脚本列表与坏配置报告保留供入口展示，坏文件不阻断好脚本。"""
    script = Script("sample", ScreenWindow(), (Wait(0),))
    error = ScriptConfigError("bad.json", "steps must not be empty")
    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), script_config_errors=(error,),
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
    script = Script(
        "wait-for-image", ScreenWindow(),
        (WaitUntil(ImageExists(ImageTemplate("missing.png")), 0.1, 0.1), Click(Point(10, 20))),
    )
    app = LocalControlApplication(catalog=ScriptCatalog((script,)))

    result = app.run_named_script(script.name, dry_run=True)
    app.start_named_script(script.name, dry_run=True)
    status = _wait_until_finished(app)

    assert result.exit_code == status.exit_code == 0
    assert result.finish_reason == status.finish_reason == "stopped_unmet_condition"
    assert "click Point" not in result.stdout
    assert "click Point" not in status.stdout


def test_local_control_runtime_failure_is_exposed_in_both_entry_modes() -> None:
    """真实设备动作失败时，同步与后台结果都明确失败并包含原始原因。"""
    script = Script("failing", ScreenWindow(), (Click(Point(10, 20)),))

    class FailingDevice:
        def click(self, target):
            """模拟真实输入设备不可用。"""
            raise RuntimeError("input permission denied")

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), real_device_factory=FailingDevice,
    )

    result = app.run_named_script(script.name, dry_run=False)
    app.start_named_script(script.name, dry_run=False)
    status = _wait_until_finished(app)

    assert result.exit_code == status.exit_code == 1
    assert result.finish_reason == status.finish_reason == "failed"
    assert "input permission denied" in result.stderr
    assert "input permission denied" in status.stderr


def test_local_control_unknown_point_finishes_without_actions_and_allows_restart(tmp_path) -> None:
    """嵌套偏移目标引用未知点位时应在动作前结束为配置失败，随后仍能启动有效脚本。"""
    invalid = Script(
        "invalid-point", ScreenWindow(),
        (Click(Point(10, 20)), Repeat(1, (Click(PointRef("missing").offset(x=5)),))),
    )
    valid = Script("valid", ScreenWindow(), (Wait(0),))
    app = LocalControlApplication(catalog=ScriptCatalog((invalid, valid)), project_root=tmp_path)

    app.start_named_script(invalid.name, dry_run=True)
    failed = _wait_until_finished(app)

    assert failed.exit_code == 2
    assert failed.finish_reason == "configuration_failed"
    assert "unknown point target: missing" in failed.stderr
    assert "click Point" not in failed.stdout
    assert failed.events[-1].event_type == "run_finished"
    assert failed.events[-1].status == "configuration_failed"

    app.start_named_script(valid.name, dry_run=True)
    restarted = _wait_until_finished(app)
    assert restarted.exit_code == 0
    assert restarted.finish_reason == "completed"
    assert restarted.stderr == ""


@pytest.mark.parametrize("failure_at", ["setup", "action"])
def test_local_control_unexpected_error_finishes_and_allows_restart(tmp_path, failure_at) -> None:
    """设备初始化或动作抛出未归一化异常时，后台应报告失败、跳过后续动作且允许再次启动。"""
    calls = []

    class BrokenDevice:
        def click(self, target):
            """模拟动作调用抛出既有运行用例未捕获的异常。"""
            raise OSError("device disconnected")

        def wait(self, duration_seconds):
            """记录不应继续执行的后续动作。"""
            calls.append("wait")

    def build_device():
        """分别在外部能力初始化和动作阶段模拟同一连接故障。"""
        if failure_at == "setup":
            raise OSError("device disconnected")
        return BrokenDevice()

    broken = Script("broken", ScreenWindow(), (Click(Point(10, 20)), Wait(1)))
    valid = Script("valid", ScreenWindow(), (Wait(0),))
    app = LocalControlApplication(
        catalog=ScriptCatalog((broken, valid)), project_root=tmp_path,
        real_device_factory=build_device,
    )

    app.start_named_script(broken.name, dry_run=False)
    failed = _wait_until_finished(app)

    assert failed.exit_code == 1
    assert failed.finish_reason == "failed"
    assert "OSError: device disconnected" in failed.stderr
    assert calls == []
    assert failed.events[-1].event_type == "run_finished"
    assert failed.events[-1].status == "failed"

    app.start_named_script(valid.name, dry_run=True)
    restarted = _wait_until_finished(app)
    assert restarted.exit_code == 0
    assert restarted.finish_reason == "completed"
    assert restarted.stderr == ""


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
        project_root=tmp_path, real_image_locator_factory=lambda: locator,
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
        project_root=tmp_path, real_image_locator_factory=MatchingLocator,
    )
    assert reader.read_current_state() == "主页"
    config_path = tmp_path / "assets" / "screen-states.json"
    config = json.loads(config_path.read_text())
    config["groups"][0]["state"] = "新主页"
    config_path.write_text(json.dumps(config))

    assert reader.read_current_state() == "新主页"


def test_project_state_reader_without_config_preserves_template_name_fallback(tmp_path) -> None:
    """未建立状态配置的旧项目仍可按 assets 模板文件名识别状态。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "主页.png").write_bytes(b"fake")

    class MatchingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """命中模板文件名对应的状态。"""
            return ImageMatch(Rect(0, 0, 20, 20), 0.9)

    reader = ProjectScreenStateReader(
        project_root=tmp_path, real_image_locator_factory=MatchingLocator,
    )

    assert reader.read_current_state() == "主页"


def test_local_control_live_invalid_state_config_finishes_with_failure(tmp_path) -> None:
    """等待期间状态配置损坏时返回失败结果，不让后台会话永远停在运行中。"""
    _write_home_state_config(tmp_path)
    config_path = tmp_path / "assets" / "screen-states.json"
    original_config = config_path.read_text()
    script = Script("state-wait", ScreenWindow(), (WaitUntil(ScreenStateIs("主页"), 1, 0.1),))

    class MutatingDevice:
        def wait(self, duration_seconds):
            """模拟用户在等待两次识别之间保存了非法配置。"""
            config_path.write_text("{")

    class MissingLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """初次读取不命中，进入等待后再读取配置。"""
            return None

    app = LocalControlApplication(
        catalog=ScriptCatalog((script,)), project_root=tmp_path,
        real_device_factory=MutatingDevice, real_image_locator_factory=MissingLocator,
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
