"""验证应用层脚本运行 module 会组装 runner、调用 runner 并归一化错误。

这些测试直接覆盖 portable run_script 的 interface，真实平台 adapter 通过工厂注入。
"""

from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain import (
    Click,
    Color,
    ImageExists,
    ImageMatch,
    ImageTemplate,
    ImageTarget,
    Point,
    Rect,
    ScreenWindow,
    Script,
    WaitUntil,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.scripts_manager import (
    CONDITIONAL_COLOR_DEMO_SCRIPT,
    RECORDED_CLICKS_SCRIPT,
    WAIT_UNTIL_COLOR_DEMO_SCRIPT,
)


IMAGE_TEMPLATE_PATH = "assets/start.png"


def build_wait_until_image_script() -> Script:
    """构造应用层测试用图片等待脚本。"""
    return Script(
        name="wait-until-image-test",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ImageExists(ImageTemplate(IMAGE_TEMPLATE_PATH)),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
            Click(Point(100, 200)),
        ),
    )


def build_click_image_script() -> Script:
    """构造应用层测试用图片目标点击脚本。"""
    return Script(
        name="click-image-test",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageTemplate(IMAGE_TEMPLATE_PATH))),),
    )


def test_run_script_dry_run_prints_plain_script_operations(capsys) -> None:
    """验证 dry-run 会使用打印 adapter 执行普通脚本。"""
    result = run_script(RECORDED_CLICKS_SCRIPT, dry_run=True)

    output = capsys.readouterr().out
    assert result.exit_code == 0
    assert result.error_message is None
    assert "wait 3s" in output
    assert "Point(x=242, y=92)" in output


def test_run_script_reports_invalid_dry_run_color_without_running(capsys) -> None:
    """验证颜色配置非法时应用层返回配置错误。"""
    result = run_script(
        CONDITIONAL_COLOR_DEMO_SCRIPT,
        dry_run=True,
        dry_run_color="bad",
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 2
    assert result.error_message == (
        "script run configuration failed: color must match #[0-9A-Fa-f]{6}"
    )


def test_run_script_reports_wait_until_timeout(capsys) -> None:
    """验证 WaitUntil 超时时应用层返回运行超时错误。"""
    result = run_script(WAIT_UNTIL_COLOR_DEMO_SCRIPT, dry_run=True)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert result.exit_code == 1
    assert result.error_message == "script run timed out: wait until condition timed out"


def test_run_script_dry_run_wait_until_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片条件可通过配置的模板匹配成功。"""
    result = run_script(
        build_wait_until_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.error_message is None
    assert captured.out == "click Point(x=100, y=200)\n"


def test_run_script_dry_run_wait_until_image_times_out_by_default(capsys) -> None:
    """验证 dry-run 未配置图片时图片等待会超时。"""
    result = run_script(build_wait_until_image_script(), dry_run=True)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert result.exit_code == 1
    assert result.error_message == "script run timed out: wait until condition timed out"


def test_run_script_dry_run_click_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片目标点击可通过配置的模板匹配成功。"""
    result = run_script(
        build_click_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.error_message is None
    assert captured.out == "click Point(x=0, y=0)\n"


def test_run_script_dry_run_click_image_reports_missing_target(capsys) -> None:
    """验证 dry-run 未配置图片时图片目标点击报告未找到。"""
    result = run_script(build_click_image_script(), dry_run=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 1
    assert result.error_message == "script run failed: image target not found: assets/start.png"


def test_run_script_real_mode_uses_injected_device_without_color_reader(capsys) -> None:
    """验证无颜色需求脚本真实运行时只使用注入的输入 adapter。"""
    clicks = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """recorded-clicks 不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """测试中不真实等待。"""

    result = run_script(
        RECORDED_CLICKS_SCRIPT,
        dry_run=False,
        real_device_factory=FakeMacOSPointerDevice,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 0
    assert result.error_message is None
    assert clicks == [
        Point(242, 92),
        Point(736, 323),
        Point(741, 400),
    ]


def test_run_script_real_mode_injects_color_reader_for_color_script() -> None:
    """验证有颜色需求脚本真实运行时会使用注入的取色 adapter。"""
    clicks = []
    read_points = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """conditional-color-demo 不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """测试中不真实等待。"""

    class FakePixelColorReader:
        def read_color(self, point) -> Color:
            read_points.append(point)
            return Color.from_hex("#102030")

    result = run_script(
        CONDITIONAL_COLOR_DEMO_SCRIPT,
        dry_run=False,
        real_device_factory=FakeMacOSPointerDevice,
        real_color_reader_factory=FakePixelColorReader,
    )

    assert result.exit_code == 0
    assert result.error_message is None
    assert read_points == [Point(50, 60)]
    assert clicks == [Point(100, 200)]


def test_run_script_real_mode_injects_image_locator_for_image_script() -> None:
    """验证有图片需求脚本真实运行时会使用注入的图像定位 adapter。"""
    clicks = []
    located_templates = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """图片等待脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """测试中不真实等待。"""

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """记录模板并返回固定图片匹配。"""
            located_templates.append(template)
            return ImageMatch(Rect(0, 0, 10, 10), confidence=1.0)

    result = run_script(
        build_wait_until_image_script(),
        dry_run=False,
        real_device_factory=FakeMacOSPointerDevice,
        real_image_locator_factory=FakeImageLocator,
    )

    assert result.exit_code == 0
    assert result.error_message is None
    assert located_templates == [ImageTemplate(IMAGE_TEMPLATE_PATH)]
    assert clicks == [Point(100, 200)]


def test_run_script_real_mode_reports_color_reader_setup_error() -> None:
    """验证真实取色 adapter setup 失败时应用层返回 setup 错误。"""
    class FailingPixelColorReader:
        def __init__(self) -> None:
            raise RuntimeError("screen color unavailable")

    result = run_script(
        CONDITIONAL_COLOR_DEMO_SCRIPT,
        dry_run=False,
        real_device_factory=lambda: object(),
        real_color_reader_factory=FailingPixelColorReader,
    )

    assert result.exit_code == 1
    assert result.error_message == "script run setup failed: screen color unavailable"


def test_run_script_real_mode_reports_image_locator_setup_error() -> None:
    """验证真实图像定位 adapter setup 失败时应用层返回 setup 错误。"""
    class FailingImageLocator:
        def __init__(self) -> None:
            raise RuntimeError("screen image unavailable")

    result = run_script(
        build_wait_until_image_script(),
        dry_run=False,
        real_device_factory=lambda: object(),
        real_image_locator_factory=FailingImageLocator,
    )

    assert result.exit_code == 1
    assert result.error_message == "script run setup failed: screen image unavailable"


def test_run_script_real_mode_reports_image_locator_runtime_error() -> None:
    """验证真实图像定位运行失败时应用层返回运行错误。"""
    class FailingImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """模拟模板读取或截图匹配失败。"""
            raise RuntimeError("template unreadable")

    result = run_script(
        build_wait_until_image_script(),
        dry_run=False,
        real_device_factory=lambda: object(),
        real_image_locator_factory=FailingImageLocator,
    )

    assert result.exit_code == 1
    assert result.error_message == "script run failed: template unreadable"
