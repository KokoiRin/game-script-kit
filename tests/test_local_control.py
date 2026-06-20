"""验证本地控制 UI 复用的应用层 interface。

这些测试覆盖 UI 和 CLI 之外的 application seam：脚本查找、运行结果捕获、
固定测试任务白名单。它不测试 HTTP 细节，也不直接绑定 engine 内部实现。
"""

import json
import subprocess
import time

from PIL import Image

from game_automation.portable.domain import (
    Click,
    If,
    ImageBatchMatchResult,
    ImageExists,
    ImageRef,
    ImageMatch,
    ImageTarget,
    ImageTemplate,
    NamedImage,
    Point,
    Rect,
    Repeat,
    ScreenStateIs,
    ScreenWindow,
    Script,
    TargetCatalog,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.application.local_control import LocalControlApplication, PROJECT_ROOT
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


def test_local_control_project_root_points_to_repository_root() -> None:
    """验证 UI 测试按钮在项目根目录运行 pytest。"""
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "tests").is_dir()


def test_local_control_runs_named_script_and_captures_dry_run_output() -> None:
    """验证 UI 用例可以按名称 dry-run 脚本并返回可展示输出。"""
    app = LocalControlApplication()

    result = app.run_named_script(
        "conditional-color-demo",
        dry_run=True,
        dry_run_color="#102030",
    )

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
    assert result.stdout == "click Point(x=100, y=200)\n"


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


def test_local_control_describes_state_script_dependencies(tmp_path) -> None:
    """验证 UI 用例可以生成状态驱动脚本详情和可用依赖检查。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps({"groups": [{"state": "主页", "searches": []}]}, ensure_ascii=False),
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
    assert details.readiness == (
        ("状态: 主页", "ok", "状态已配置"),
        ("图片: assets/start.png", "ok", "图片文件可用"),
    )


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
    assert final.stderr == ""
    assert final.stdout == "click Point(x=100, y=200)\n"


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
    assert "script is already running" in duplicate.stderr
    assert final.exit_code == 130


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
    assert "image match template=assets/start.png" in final.stdout
    assert "found=True" in final.stdout
    assert "confidence=0.91" in final.stdout


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


def test_local_control_reuses_running_background_screen_state_for_real_script(tmp_path) -> None:
    """验证真实脚本优先复用运行中的后台界面状态。"""
    _write_home_state_config(tmp_path)
    clicks = []
    batch_requests = []
    script = _build_state_branch_script()

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
            batch_requests.append(tuple(requests))
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

    app.start_screen_state_probe(interval_seconds=30)
    running = _wait_until_probe_state(app, "主页")
    requests_after_probe = len(batch_requests)
    result = app.run_named_script("state-aware", dry_run=False)
    app.stop_screen_state_probe()

    assert running.current_state == "主页"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert clicks == [Point(100, 200)]
    assert len(batch_requests) == requests_after_probe
    assert "screen state reader reused background probe current_state=主页" in result.stdout


def test_local_control_falls_back_to_probe_when_background_state_is_unknown(tmp_path) -> None:
    """验证后台状态不可用时真实脚本仍执行即时探测。"""
    _write_home_state_config(tmp_path)
    clicks = []
    batch_requests = []
    script = _build_state_branch_script()

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
            """第一次返回未知，第二次返回主页命中。"""
            batch_requests.append(tuple(requests))
            if len(batch_requests) == 1:
                return (
                    ImageBatchMatchResult(
                        requests[0].template,
                        None,
                        elapsed_ms=4.0,
                    ),
                )
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

    app.start_screen_state_probe(interval_seconds=30)
    running = _wait_until_probe_output_contains(app, "current_state=未知")
    result = app.run_named_script("state-aware", dry_run=False)
    app.stop_screen_state_probe()

    assert running.current_state == "未知"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert clicks == [Point(100, 200)]
    assert len(batch_requests) == 2
    assert "screen state probe round current_state=主页" in result.stdout


def test_local_control_lists_image_assets_from_project_assets_folder(tmp_path) -> None:
    """验证 UI 用例只列出图片资源目录里的支持图片文件。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    (assets / "button.jpg").write_bytes(b"fake")
    (assets / "notes.txt").write_text("skip")

    app = LocalControlApplication(project_root=tmp_path)

    assert app.image_asset_folder_label() == "assets"
    assert app.list_image_assets() == ("button.jpg", "start.png")


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


def test_local_control_clicks_selected_image_asset_in_dry_run(tmp_path) -> None:
    """验证 UI 用例可把 assets 里的图片作为目标执行查找并点击脚本。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("start.png", dry_run=True)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=" in result.stdout
    assert "assets/start.png" in result.stdout
    assert "found=True" in result.stdout
    assert result.stdout.endswith("click Point(x=0, y=0)\n")


def test_local_control_passes_min_confidence_to_image_click(tmp_path) -> None:
    """验证 UI 用例会把最低匹配置信度传给图片目标。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    clicks = []
    confidences = []

    class FakeDevice(InputDevice):
        def click(self, target) -> None:
            """记录真实点击坐标。"""
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """图片点击用例不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """图片点击用例不会等待。"""

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """记录最低置信度并返回固定匹配。"""
            confidences.append(min_confidence)
            return ImageMatch(Rect(10, 20, 8, 6), confidence=0.91)

    app = LocalControlApplication(
        project_root=tmp_path,
        real_device_factory=FakeDevice,
        real_image_locator_factory=FakeImageLocator,
    )

    result = app.click_image_asset("start.png", dry_run=False, min_confidence=0.7)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert "image match template=" in result.stdout
    assert "confidence=0.91" in result.stdout
    assert confidences == [0.7]
    assert clicks == [Point(14, 23)]


def test_local_control_captures_screen_debug_screenshot(tmp_path) -> None:
    """验证 UI 用例可把真实截图保存到项目内诊断文件。"""
    captured_paths = []

    def screen_capture(path):
        captured_paths.append(path)
        path.write_bytes(b"png")

    app = LocalControlApplication(project_root=tmp_path, screen_capture_factory=lambda: screen_capture)

    result = app.capture_screen_screenshot()

    screenshot_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen.png"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == f"saved screenshot: {screenshot_path}\n"
    assert result.screenshot_path == str(screenshot_path)
    assert screenshot_path.read_bytes() == b"png"
    assert captured_paths == [screenshot_path]


def test_local_control_captures_screen_region_diagnostics(tmp_path) -> None:
    """验证 UI 用例可生成带状态区域框的诊断截图。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "regions": {
            "主页标题": {"left": 10, "top": 5, "width": 20, "height": 10}
          },
          "groups": [
            {
              "state": "主页",
              "searches": [
                {"name": "主页标题", "image": "home.png", "region": "主页标题"}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    Image.new("RGB", (4, 4), "black").save(assets / "home.png")

    def screen_capture(path):
        """保存测试用截图。"""
        Image.new("RGB", (200, 100), "white").save(path)

    app = LocalControlApplication(
        project_root=tmp_path,
        screen_capture_factory=lambda: screen_capture,
        screen_size_factory=lambda: Point(100, 50),
    )

    result = app.capture_screen_region_diagnostics()

    diagnostic_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen-regions.png"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == f"saved region diagnostics screenshot: {diagnostic_path}\n"
    assert result.screenshot_path == str(diagnostic_path)
    with Image.open(diagnostic_path) as diagnostic:
        assert diagnostic.size == (200, 100)
        assert diagnostic.getpixel((20, 10)) != (255, 255, 255)


def test_local_control_region_diagnostics_requires_screen_state_config(tmp_path) -> None:
    """验证区域诊断缺少状态配置时返回清晰错误。"""
    (tmp_path / "assets").mkdir()
    app = LocalControlApplication(project_root=tmp_path)

    result = app.capture_screen_region_diagnostics()

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "screen state config is required for region diagnostics" in result.stderr


def test_local_control_region_diagnostics_requires_named_regions(tmp_path) -> None:
    """验证区域诊断要求配置中存在命名区域。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        """
        {
          "regions": {},
          "groups": [
            {
              "state": "主页",
              "searches": [
                {"name": "主页标题", "image": "home.png"}
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    Image.new("RGB", (4, 4), "black").save(assets / "home.png")
    app = LocalControlApplication(project_root=tmp_path)

    result = app.capture_screen_region_diagnostics()

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "screen state config has no named regions" in result.stderr


def test_local_control_rejects_image_asset_outside_assets_folder(tmp_path) -> None:
    """验证 UI 用例拒绝通过相对路径逃逸图片资源目录。"""
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("../secret.png", dry_run=True)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "invalid image click request:" in result.stderr


def test_local_control_rejects_invalid_image_confidence(tmp_path) -> None:
    """验证 UI 用例拒绝非法图片最低匹配置信度。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("start.png", dry_run=True, min_confidence=1.1)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "image target min_confidence" in result.stderr


def test_local_control_rejects_unknown_test_task_without_running_command() -> None:
    """验证 UI 只能触发白名单测试任务。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((command, cwd))
        raise AssertionError("unknown test task must not execute a command")

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("shell")

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == "unknown test task: shell\n"
    assert commands == []


def test_local_control_runs_whitelisted_test_task() -> None:
    """验证 UI 测试按钮只通过固定任务执行命令。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((tuple(command), cwd))
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="2 passed\n",
            stderr="",
        )

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("all")

    assert result.exit_code == 0
    assert result.stdout == "2 passed\n"
    assert result.stderr == ""
    assert len(commands) == 1
    assert commands[0][0][-2:] == ("-m", "pytest")


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


def _wait_until_probe_state(app: LocalControlApplication, expected_state: str):
    """轮询等待后台界面探测进入指定状态。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_screen_state_probe()
        if status.running and status.current_state == expected_state:
            return status
        time.sleep(0.01)
    raise AssertionError(f"screen state probe did not reach {expected_state}")


def _wait_until_probe_output_contains(app: LocalControlApplication, expected_text: str):
    """轮询等待后台界面探测日志包含指定文本。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_screen_state_probe()
        if status.running and expected_text in status.stdout:
            return status
        time.sleep(0.01)
    raise AssertionError(f"screen state probe output did not contain {expected_text}")
