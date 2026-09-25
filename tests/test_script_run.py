"""验证应用层脚本运行 module 会组装 runner、调用 runner 并归一化错误。

这些测试直接覆盖 portable run_script 的 interface，真实平台 adapter 通过工厂注入。
"""

from game_automation.portable.application.script_run import run_script
from game_automation.portable.application.ports import FocusedApplicationWindow
from game_automation.portable.domain import (
    Click,
    Hotkey,
    Color,
    ImageExists,
    ImageMatch,
    ImageTemplate,
    ImageTarget,
    Point,
    Rect,
    ScreenWindow,
    ScreenStateIs,
    Script,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.scripts_manager import (
    CONDITIONAL_COLOR_DEMO_SCRIPT,
    RECORDED_CLICKS_SCRIPT,
    WAIT_UNTIL_COLOR_DEMO_SCRIPT,
)


IMAGE_TEMPLATE_PATH = "assets/start.png"


class FakeRunLogger:
    """收集脚本运行测试中的运行日志。"""

    def __init__(self) -> None:
        """初始化日志列表。"""
        self.messages: list[str] = []
        self.events = []

    def log(self, message: str) -> None:
        """记录一条运行日志。"""
        self.messages.append(message)

    def log_event(self, event) -> None:
        """记录一条结构化运行事件。"""
        self.events.append(event)


def test_hotkey_run_logs_performed_keys() -> None:
    """组合键执行成功后，运行日志应给出实际执行的键组合，供 CLI/UI 展示。"""
    logger = FakeRunLogger()
    script = Script("paste", ScreenWindow(), (Hotkey(("command", "v")),))

    result = run_script(script, dry_run=True, logger=logger, emit_step_events=True)

    assert result.finish_reason == "completed"
    performed = [event for event in logger.events if event.event_type == "hotkey_performed"]
    assert len(performed) == 1
    assert performed[0].details == {"keys": "command+v"}


def test_hotkey_failure_stops_script_without_success_event() -> None:
    """输入设备拒绝粘贴时，脚本应报告失败、停止后续步骤，且不记录组合键成功。"""
    class FailingKeyboard(InputDevice):
        def hotkey(self, keys: tuple[str, ...]) -> None:
            """模拟设备按键失败。"""
            raise RuntimeError("keyboard blocked")

        def wait(self, duration_seconds: float) -> None:
            """后续步骤若被误执行，立即让测试失败。"""
            raise AssertionError("continued after hotkey failure")

    logger = FakeRunLogger()
    script = Script("paste", ScreenWindow(), (Hotkey(("command", "v")), Wait(1)))

    result = run_script(script, dry_run=False, real_device_factory=FailingKeyboard,
                        logger=logger, emit_step_events=True)

    assert result.exit_code == 1
    assert result.finish_reason == "failed"
    assert "keyboard blocked" in result.error_message
    assert not any(event.event_type == "hotkey_performed" for event in logger.events)


def test_cancelled_script_does_not_send_hotkey() -> None:
    """执行前已取消的脚本应返回 cancelled，不向设备发送粘贴按键。"""
    class Cancelled:
        def is_cancelled(self) -> bool:
            """模拟用户已请求取消。"""
            return True

    class UnexpectedKeyboard(InputDevice):
        def hotkey(self, keys: tuple[str, ...]) -> None:
            """取消后若仍发送按键则让测试失败。"""
            raise AssertionError("sent hotkey after cancellation")

    result = run_script(
        Script("paste", ScreenWindow(), (Hotkey(("command", "v")),)),
        dry_run=False, real_device_factory=UnexpectedKeyboard, cancellation_token=Cancelled(),
    )

    assert result.exit_code == 130
    assert result.finish_reason == "cancelled"


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


def build_screen_state_branch_script() -> Script:
    """构造应用层测试用界面状态分支脚本。"""
    from game_automation.portable.domain import If

    return Script(
        name="screen-state-branch-test",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(100, 200)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )


def test_run_script_dry_run_prints_plain_script_operations(capsys) -> None:
    """验证 dry-run 会使用打印 adapter 执行普通脚本。"""
    result = run_script(RECORDED_CLICKS_SCRIPT, dry_run=True)

    output = capsys.readouterr().out
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
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
    assert result.finish_reason == "configuration_failed"
    assert result.error_message == (
        "script run configuration failed: color must match #[0-9A-Fa-f]{6}"
    )


def test_run_script_stops_normally_when_wait_until_times_out(capsys) -> None:
    """验证 WaitUntil 超时时应用层返回未满足条件的结束原因。"""
    result = run_script(WAIT_UNTIL_COLOR_DEMO_SCRIPT, dry_run=True)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert result.exit_code == 0
    assert result.finish_reason == "stopped_unmet_condition"
    assert result.error_message is None


def test_run_script_dry_run_wait_until_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片条件可通过配置的模板匹配成功。"""
    result = run_script(
        build_wait_until_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert captured.out == "click Point(x=100, y=200)\n"


def test_run_script_logs_screen_state_condition_when_logger_is_configured() -> None:
    """验证脚本运行注入 logger 时会记录界面状态条件评估摘要。"""
    logger = FakeRunLogger()

    result = run_script(
        build_screen_state_branch_script(),
        dry_run=True,
        dry_run_screen_state="主页",
        logger=logger,
    )

    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert logger.messages == [
        "screen state condition expected=主页 actual=主页 min_confidence=0.8 matched=True"
    ]


def test_run_script_dry_run_wait_until_image_stops_normally_by_default(capsys) -> None:
    """验证 dry-run 未配置图片时图片等待会正常停止。"""
    result = run_script(build_wait_until_image_script(), dry_run=True)

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert result.exit_code == 0
    assert result.finish_reason == "stopped_unmet_condition"
    assert result.error_message is None


def test_run_script_dry_run_click_image_with_configured_match(capsys) -> None:
    """验证 dry-run 图片目标点击可通过配置的模板匹配成功。"""
    result = run_script(
        build_click_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert result.error_message is None
    assert captured.out == "click Point(x=0, y=0)\n"


def test_run_script_dry_run_click_image_stops_normally_when_target_is_missing(capsys) -> None:
    """验证 dry-run 未配置图片时图片目标点击正常停止。"""
    result = run_script(build_click_image_script(), dry_run=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert result.exit_code == 0
    assert result.finish_reason == "stopped_unmet_condition"
    assert result.error_message is None


def test_run_script_emits_step_events_when_enabled(capsys) -> None:
    """验证应用层可按需启用结构化步骤事件，不影响默认输出策略。"""
    logger = FakeRunLogger()

    result = run_script(
        build_click_image_script(),
        dry_run=True,
        dry_run_images=(IMAGE_TEMPLATE_PATH,),
        logger=logger,
        emit_step_events=True,
    )

    captured = capsys.readouterr()
    assert captured.out == "click Point(x=0, y=0)\n"
    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert [event.event_type for event in logger.events] == [
        "run_started",
        "step_started",
        "image_target_resolved",
        "click_resolved",
        "click_performed",
        "step_succeeded",
        "run_finished",
    ]
    assert logger.events[1].step_path == "1"
    assert logger.events[2].details["point"] == "Point(x=0, y=0)"


def test_run_script_dry_run_screen_state_condition_uses_fixed_state(capsys) -> None:
    """验证 dry-run 界面状态条件可使用固定状态结果。"""
    result = run_script(
        build_screen_state_branch_script(),
        dry_run=True,
        dry_run_screen_state="主页",
    )

    captured = capsys.readouterr()
    assert result.exit_code == 0
    assert result.error_message is None
    assert captured.out == "click Point(x=100, y=200)\n"


def test_run_script_real_mode_injects_screen_state_reader_for_state_script() -> None:
    """验证真实运行状态条件脚本时会使用注入的状态读取端口。"""
    clicks = []
    confidence_values = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """状态分支脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """状态分支命中后不会等待。"""

    class FakeScreenStateReader:
        def read_current_state(self, *, min_confidence=0.8, logger=None):
            """记录最低置信度并返回固定状态。"""
            confidence_values.append(min_confidence)
            return "主页"

    result = run_script(
        build_screen_state_branch_script(),
        dry_run=False,
        real_device_factory=FakeMacOSPointerDevice,
        real_screen_state_reader_factory=FakeScreenStateReader,
    )

    assert result.exit_code == 0
    assert result.error_message is None
    assert confidence_values == [0.8]
    assert clicks == [Point(100, 200)]


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


def test_run_script_activates_target_application_before_creating_device() -> None:
    """验证真实运行会先激活目标应用，再创建输入设备并执行动作。"""
    events = []

    class FakeApplicationActivator:
        def activate(self, application: str) -> None:
            """记录目标应用激活。"""
            events.append(("activate", application))

    class FakeInputDevice(InputDevice):
        def click(self, target) -> None:
            """记录脚本点击。"""
            events.append(("click", target))

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """本测试脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """本测试脚本不会等待。"""

    def build_device() -> FakeInputDevice:
        """记录输入设备创建时机。"""
        events.append(("build_device", None))
        return FakeInputDevice()

    script = Script("activate-first", ScreenWindow(), (Click(Point(5, 6)),))

    result = run_script(
        script,
        dry_run=False,
        target_application="Safari",
        real_application_activator_factory=FakeApplicationActivator,
        real_device_factory=build_device,
    )

    assert result.exit_code == 0
    assert result.finish_reason == "completed"
    assert events == [
        ("activate", "Safari"),
        ("build_device", None),
        ("click", Point(5, 6)),
    ]


def test_run_script_reports_target_application_activation_failure_without_device() -> None:
    """验证目标应用激活失败会阻止真实输入设备创建。"""
    device_builds = []

    class FailingApplicationActivator:
        def activate(self, application: str) -> None:
            """模拟平台无法激活目标应用。"""
            raise RuntimeError(f"cannot activate {application}")

    def build_device():
        """记录不应发生的输入设备创建。"""
        device_builds.append(True)
        raise AssertionError("device must not be created")

    script = Script("activation-fails", ScreenWindow(), (Click(Point(1, 2)),))

    result = run_script(
        script,
        dry_run=False,
        target_application="Missing App",
        real_application_activator_factory=FailingApplicationActivator,
        real_device_factory=build_device,
    )

    assert result.exit_code == 1
    assert result.finish_reason == "setup_failed"
    assert result.error_message == "script run setup failed: cannot activate Missing App"
    assert device_builds == []


def test_run_script_dry_run_does_not_activate_target_application() -> None:
    """验证 portable dry-run 即使收到目标应用也不会产生桌面副作用。"""
    activator_builds = []

    def build_activator():
        """记录不应发生的目标应用 adapter 创建。"""
        activator_builds.append(True)
        raise AssertionError("activator must not be created")

    script = Script("dry-run-no-activation", ScreenWindow(), (Click(Point(1, 2)),))

    result = run_script(
        script,
        dry_run=True,
        target_application="Safari",
        real_application_activator_factory=build_activator,
    )

    assert result.exit_code == 0
    assert activator_builds == []


def test_run_script_focuses_target_window_and_binds_script_copy_before_device() -> None:
    """验证真实运行按顺序选窗并把窗口矩形绑定到本轮脚本副本。"""
    events = []

    class FakeApplicationActivator:
        def activate(self, application: str) -> None:
            """记录应用激活。"""
            events.append(("activate", application))

    class FakeWindowController:
        def focus_window(self, application: str, title_contains: str) -> FocusedApplicationWindow:
            """记录窗口选择并返回固定屏幕矩形。"""
            events.append(("focus_window", application, title_contains))
            return FocusedApplicationWindow("Star 视觉自动化靶场", Rect(100, 200, 800, 600))

    class FakeInputDevice(InputDevice):
        def click(self, target) -> None:
            """记录窗口内点位解析后的点击。"""
            events.append(("click", target))

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """本测试脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """本测试脚本不会等待。"""

    def build_device() -> FakeInputDevice:
        """记录输入设备创建时机。"""
        events.append(("build_device", None))
        return FakeInputDevice()

    script = Script("window-bound", ScreenWindow(), (Click(Point(10, 20)),))

    result = run_script(
        script,
        dry_run=False,
        target_application="Safari",
        target_window_title="视觉自动化靶场",
        real_application_activator_factory=FakeApplicationActivator,
        real_application_window_controller_factory=FakeWindowController,
        real_device_factory=build_device,
    )

    assert result.exit_code == 0
    assert events == [
        ("activate", "Safari"),
        ("focus_window", "Safari", "视觉自动化靶场"),
        ("build_device", None),
        ("click", Point(110, 220)),
    ]
    assert script.window == ScreenWindow()


def test_run_script_reports_target_window_failure_without_device() -> None:
    """验证窗口选择失败会归一化为 setup failure 并阻止设备创建。"""
    device_builds = []

    class FakeApplicationActivator:
        def activate(self, application: str) -> None:
            """模拟应用激活成功。"""

    class FailingWindowController:
        def focus_window(self, application: str, title_contains: str) -> FocusedApplicationWindow:
            """模拟目标窗口不存在。"""
            raise RuntimeError("target window was not found")

    def build_device():
        """记录不应发生的输入设备创建。"""
        device_builds.append(True)
        raise AssertionError("device must not be created")

    script = Script("window-missing", ScreenWindow(), (Click(Point(1, 2)),))

    result = run_script(
        script,
        dry_run=False,
        target_application="Safari",
        target_window_title="Missing",
        real_application_activator_factory=FakeApplicationActivator,
        real_application_window_controller_factory=FailingWindowController,
        real_device_factory=build_device,
    )

    assert result.exit_code == 1
    assert result.finish_reason == "setup_failed"
    assert result.error_message == "script run setup failed: target window was not found"
    assert device_builds == []


def test_run_script_rejects_target_window_without_target_application() -> None:
    """验证 portable application 要求窗口标题和目标应用一起提供。"""
    script = Script("window-without-app", ScreenWindow(), (Click(Point(1, 2)),))

    result = run_script(
        script,
        dry_run=False,
        target_window_title="视觉自动化靶场",
        real_device_factory=lambda: (_ for _ in ()).throw(AssertionError("must not build device")),
    )

    assert result.exit_code == 2
    assert result.finish_reason == "configuration_failed"
    assert result.error_message == (
        "script run configuration failed: target window title requires target application"
    )


def test_run_script_dry_run_does_not_focus_target_window() -> None:
    """验证 portable dry-run 不创建真实窗口控制 adapter。"""
    controller_builds = []

    def build_controller():
        """记录不应发生的窗口控制 adapter 创建。"""
        controller_builds.append(True)
        raise AssertionError("window controller must not be created")

    script = Script("dry-window", ScreenWindow(), (Click(Point(1, 2)),))

    result = run_script(
        script,
        dry_run=True,
        target_application="Safari",
        target_window_title="视觉自动化靶场",
        real_application_window_controller_factory=build_controller,
    )

    assert result.exit_code == 0
    assert controller_builds == []


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
