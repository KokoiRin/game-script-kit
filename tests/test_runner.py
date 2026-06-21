"""验证脚本 runner 会把领域步骤映射到输入设备端口。"""

import pytest

from game_automation.portable.engine.runner import ScriptCancelledError, ScriptRunner
from game_automation.portable.domain import (
    AreaWindow,
    Click,
    Color,
    ColorIs,
    Drag,
    If,
    ImageExists,
    ImageMatch,
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    ImageTarget,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    OffsetTarget,
    Point,
    PointRef,
    Rect,
    RegionRef,
    Repeat,
    ScreenWindow,
    ScreenStateIs,
    SearchRef,
    Script,
    TargetCatalog,
    Wait,
    WaitUntil,
    UnknownImageNameError,
    UnknownPointNameError,
)
from tests.support.fake_device import FakeInputDevice


class FakeColorReader:
    """提供 runner 测试用固定取色结果。"""

    def __init__(self, color: Color) -> None:
        """保存固定颜色并记录读取点。"""
        self.color = color
        self.points: list[Point] = []

    def read_color(self, point: Point) -> Color:
        """记录读取点并返回固定颜色。"""
        self.points.append(point)
        return self.color


class SequenceColorReader:
    """按序返回颜色，序列耗尽后保持最后一个颜色。"""

    def __init__(self, colors: list[Color]) -> None:
        """保存颜色序列并记录读取点。"""
        self.colors = colors
        self.points: list[Point] = []

    def read_color(self, point: Point) -> Color:
        """返回下一个颜色并记录读取点。"""
        self.points.append(point)
        index = min(len(self.points) - 1, len(self.colors) - 1)
        return self.colors[index]


class SequenceImageLocator:
    """按序返回图像匹配结果，序列耗尽后保持最后一个结果。"""

    def __init__(self, matches: list[ImageMatch | None]) -> None:
        """保存匹配结果序列并记录定位参数。"""
        self.matches = matches
        self.calls = []

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger=None,
    ) -> ImageMatch | None:
        """返回下一个匹配结果并记录定位参数。"""
        self.calls.append((template, region, min_confidence))
        index = min(len(self.calls) - 1, len(self.matches) - 1)
        return self.matches[index]


class FakeRunEventLogger:
    """收集 runner 输出的结构化事件和文本日志。"""

    def __init__(self) -> None:
        """初始化事件和文本列表。"""
        self.messages: list[str] = []
        self.events = []

    def log(self, message: str) -> None:
        """记录普通文本日志。"""
        self.messages.append(message)

    def log_event(self, event) -> None:
        """记录结构化脚本运行事件。"""
        self.events.append(event)


class SequenceScreenStateReader:
    """按序返回界面状态，序列耗尽后保持最后一个状态。"""

    def __init__(self, states: list[str]) -> None:
        """保存状态序列并记录读取参数。"""
        self.states = states
        self.calls = []

    def read_current_state(self, *, min_confidence: float = 0.8, logger=None) -> str:
        """返回下一个状态并记录最低置信度。"""
        self.calls.append(min_confidence)
        index = min(len(self.calls) - 1, len(self.states) - 1)
        return self.states[index]


def test_runner_maps_steps_to_device_with_script_window() -> None:
    """验证 runner 使用脚本级窗口解析点击和拖拽坐标。"""
    device = FakeInputDevice()
    script = Script(
        name="area-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Click(Point(10, 20)),
            Drag(Point(30, 40), Point(50, 60), duration_seconds=0.4),
            Wait(0.2),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == ["click", "drag_to", "wait"]
    assert device.actions[0].target == Point(110, 220)
    assert device.actions[1].start == Point(130, 240)
    assert device.actions[1].end == Point(150, 260)
    assert device.actions[1].duration_seconds == 0.4
    assert device.actions[2].duration_seconds == 0.2


def test_runner_clicks_named_point_on_screen_window() -> None:
    """验证 runner 能把命名点位解析为屏幕坐标点击。"""
    device = FakeInputDevice()
    script = Script(
        name="named-point-runner",
        window=ScreenWindow(),
        steps=(Click(PointRef("头像")),),
        resources=TargetCatalog(points=(NamedPoint("头像", Point(242, 92)),)),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(242, 92)


def test_runner_resolves_named_point_with_area_window() -> None:
    """验证命名点位仍然应用脚本窗口坐标规则。"""
    device = FakeInputDevice()
    script = Script(
        name="named-point-area-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(Click(PointRef("头像")),),
        resources=TargetCatalog(points=(NamedPoint("头像", Point(42, 9)),)),
    )

    ScriptRunner(device=device).run(script)

    assert device.actions[0].target == Point(142, 209)


def test_runner_reports_unknown_named_point() -> None:
    """验证未知点位名称会在执行时报告清楚。"""
    script = Script(
        name="unknown-named-point-runner",
        window=ScreenWindow(),
        steps=(Click(PointRef("头像")),),
    )

    with pytest.raises(UnknownPointNameError, match="unknown point target: 头像"):
        ScriptRunner(device=FakeInputDevice()).run(script)


def test_runner_clicks_offset_static_point() -> None:
    """验证 runner 能点击固定点位偏移后的点。"""
    device = FakeInputDevice()
    script = Script(
        name="offset-static-point-runner",
        window=ScreenWindow(),
        steps=(Click(OffsetTarget(Point(10, 20), Point(5, -3))),),
    )

    ScriptRunner(device=device).run(script)

    assert device.actions[0].target == Point(15, 17)


def test_runner_clicks_offset_named_point() -> None:
    """验证 runner 能点击命名点位偏移后的点。"""
    device = FakeInputDevice()
    script = Script(
        name="offset-named-point-runner",
        window=ScreenWindow(),
        steps=(Click(PointRef("头像").offset(x=120, y=0)),),
        resources=TargetCatalog(points=(NamedPoint("头像", Point(242, 92)),)),
    )

    ScriptRunner(device=device).run(script)

    assert device.actions[0].target == Point(362, 92)


def test_runner_expands_repeat_steps() -> None:
    """验证 runner 会按固定次数展开 Repeat 内部步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="repeat-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Repeat(
                times=3,
                steps=(
                    Click(Point(10, 20)),
                    Wait(0.5),
                ),
            ),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == [
        "click",
        "wait",
        "click",
        "wait",
        "click",
        "wait",
    ]
    assert [action.target for action in device.actions if action.name == "click"] == [
        Point(110, 220),
        Point(110, 220),
        Point(110, 220),
    ]


def test_runner_emits_step_events_for_repeat_and_click() -> None:
    """验证 runner 启用事件日志后记录 Repeat 轮次和点击执行结果。"""
    device = FakeInputDevice()
    logger = FakeRunEventLogger()
    script = Script(
        name="repeat-events",
        window=ScreenWindow(),
        steps=(Repeat(times=2, steps=(Click(Point(10, 20)),)),),
    )

    ScriptRunner(device=device, logger=logger, emit_step_events=True).run(script)

    assert [event.event_type for event in logger.events] == [
        "step_started",
        "repeat_iteration_started",
        "step_started",
        "click_resolved",
        "click_performed",
        "step_succeeded",
        "repeat_iteration_started",
        "step_started",
        "click_resolved",
        "click_performed",
        "step_succeeded",
        "step_succeeded",
    ]
    assert logger.events[1].details["iteration"] == "1"
    assert logger.events[6].details["iteration"] == "2"
    assert logger.events[3].details["point"] == "Point(x=10, y=20)"


def test_runner_stops_repeat_when_cancellation_is_requested() -> None:
    """验证 runner 在循环运行中收到取消信号后停止后续步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="cancel-repeat-runner",
        window=ScreenWindow(),
        steps=(
            Repeat(
                times=3,
                steps=(
                    Click(Point(1, 2)),
                    Wait(0.5),
                ),
            ),
        ),
    )

    class CancelAfterFirstWait:
        def is_cancelled(self) -> bool:
            """第一轮等待结束后报告取消。"""
            return len(device.actions) >= 2

    with pytest.raises(ScriptCancelledError, match="script run cancelled"):
        ScriptRunner(device=device, cancellation_token=CancelAfterFirstWait()).run(script)

    assert [action.name for action in device.actions] == ["click", "wait"]


def test_runner_expands_nested_repeat_steps_with_script_window() -> None:
    """验证 runner 会递归展开嵌套 Repeat 并保留窗口坐标解析。"""
    device = FakeInputDevice()
    script = Script(
        name="nested-repeat-runner",
        window=AreaWindow(Rect(10, 20, 800, 600)),
        steps=(
            Repeat(
                times=2,
                steps=(
                    Click(Point(1, 2)),
                    Repeat(times=2, steps=(Drag(Point(3, 4), Point(5, 6)),)),
                ),
            ),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == [
        "click",
        "drag_to",
        "drag_to",
        "click",
        "drag_to",
        "drag_to",
    ]
    assert device.actions[0].target == Point(11, 22)
    assert device.actions[1].start == Point(13, 24)
    assert device.actions[1].end == Point(15, 26)
    assert device.actions[4].start == Point(13, 24)
    assert device.actions[4].end == Point(15, 26)


def test_runner_executes_then_branch_when_color_condition_matches() -> None:
    """验证颜色条件为真时 runner 只执行 then 分支。"""
    device = FakeInputDevice()
    color_reader = FakeColorReader(Color(10, 20, 30))
    script = Script(
        name="if-then-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Click(Point(5, 6)),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(103, 204)


def test_runner_executes_else_branch_when_color_condition_does_not_match() -> None:
    """验证颜色条件为假时 runner 只执行 else 分支。"""
    device = FakeInputDevice()
    script = Script(
        name="if-else-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(99, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["wait"]
    assert device.actions[0].duration_seconds == 0.5


def test_runner_emits_if_branch_event() -> None:
    """验证 If 条件分支会记录结构化选择结果。"""
    device = FakeInputDevice()
    logger = FakeRunEventLogger()
    script = Script(
        name="if-events",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(
        device=device,
        color_reader=FakeColorReader(Color(99, 20, 30)),
        logger=logger,
        emit_step_events=True,
    ).run(script)

    branch_events = [event for event in logger.events if event.event_type == "condition_evaluated"]
    assert branch_events[0].step_path == "1"
    assert branch_events[0].details["result"] == "False"
    assert branch_events[0].details["branch"] == "else"


def test_runner_skips_empty_else_branch_and_continues() -> None:
    """验证空 else 分支不会发起操作且后续步骤继续执行。"""
    device = FakeInputDevice()
    script = Script(
        name="if-empty-else-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
            ),
            Wait(1),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(0, 0, 0))).run(script)

    assert [action.name for action in device.actions] == ["wait"]
    assert device.actions[0].duration_seconds == 1


def test_runner_resolves_color_condition_point_with_script_window() -> None:
    """验证颜色条件点会使用脚本窗口解析为屏幕坐标。"""
    device = FakeInputDevice()
    color_reader = FakeColorReader(Color(1, 2, 3))
    script = Script(
        name="if-window-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            If(
                condition=ColorIs(Point(7, 8), Color(1, 2, 3)),
                then_steps=(Wait(0.1),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert color_reader.points == [Point(107, 208)]


def test_runner_matches_color_condition_with_channel_tolerance() -> None:
    """验证颜色条件按每个 RGB 通道容差匹配。"""
    device = FakeInputDevice()
    script = Script(
        name="if-tolerance-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30), tolerance=2),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(12, 18, 31))).run(script)

    assert [action.name for action in device.actions] == ["click"]


def test_runner_requires_color_reader_for_color_condition() -> None:
    """验证执行颜色条件时必须注入颜色读取端口。"""
    script = Script(
        name="if-missing-reader-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="color reader"):
        ScriptRunner(device=FakeInputDevice()).run(script)


def test_runner_executes_then_branch_when_screen_state_matches() -> None:
    """验证界面状态条件为真时 runner 执行 then 分支。"""
    device = FakeInputDevice()
    state_reader = SequenceScreenStateReader(["主页"])
    script = Script(
        name="if-screen-state-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页", min_confidence=0.7),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, screen_state_reader=state_reader).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert state_reader.calls == [0.7]


def test_runner_requires_screen_state_reader_for_screen_state_condition() -> None:
    """验证执行界面状态条件时必须注入界面状态读取端口。"""
    script = Script(
        name="if-missing-state-reader-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ScreenStateIs("主页"),
                then_steps=(Click(Point(3, 4)),),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="screen state reader"):
        ScriptRunner(device=FakeInputDevice()).run(script)


def test_runner_executes_then_branch_when_image_exists() -> None:
    """验证图片存在条件为真时 runner 执行 then 分支。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(0, 0, 10, 10), confidence=1.0)])
    script = Script(
        name="if-image-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            If(
                condition=ImageExists(
                    ImageTemplate("assets/start.png"),
                    region=Rect(1, 2, 30, 40),
                    min_confidence=0.8,
                ),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(103, 204)
    assert locator.calls == [
        (ImageTemplate("assets/start.png"), Rect(101, 202, 30, 40), 0.8)
    ]


def test_runner_clicks_image_target_center_with_offset_and_region() -> None:
    """验证图片目标点击会解析区域并点击匹配中心加 offset。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="click-image-target",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Click(
                ImageTarget(
                    ImageTemplate("assets/start.png"),
                    region=Rect(1, 2, 300, 400),
                    min_confidence=0.8,
                    offset=Point(5, -3),
                )
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(30, 37)
    assert locator.calls == [
        (ImageTemplate("assets/start.png"), Rect(101, 202, 300, 400), 0.8)
    ]


def test_runner_clicks_image_target_anchor() -> None:
    """验证图片目标可以点击指定匹配 anchor。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="click-image-target-anchor",
        window=ScreenWindow(),
        steps=(
            Click(
                ImageTarget(
                    ImageTemplate("assets/start.png"),
                    anchor="right_center",
                )
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert device.actions[0].target == Point(40, 40)


def test_runner_applies_image_target_offset_after_anchor() -> None:
    """验证图片目标 offset 会在 anchor 点位后应用。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="click-image-target-anchor-offset",
        window=ScreenWindow(),
        steps=(
            Click(
                ImageTarget(
                    ImageTemplate("assets/start.png"),
                    anchor="right_center",
                    offset=Point(24, 0),
                )
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert device.actions[0].target == Point(64, 40)


def test_runner_resolves_named_image_target_before_clicking() -> None:
    """验证图片点击会把命名图片解析为模板后再定位。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="named-image-click-runner",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageRef("开始按钮"), min_confidence=0.8)),),
        resources=TargetCatalog(images=(NamedImage("开始按钮", ImageTemplate("assets/start.png")),)),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert device.actions[0].target == Point(25, 40)
    assert locator.calls == [(ImageTemplate("assets/start.png"), None, 0.8)]


def test_runner_resolves_named_image_search_target_before_clicking() -> None:
    """验证图片目标可以引用命名搜索规格。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="named-image-search-click-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(Click(ImageTarget(SearchRef("开始按钮"))),),
        resources=TargetCatalog(
            images=(NamedImage("开始", ImageTemplate("assets/start.png")),),
            regions=(NamedRegion("按钮区", Rect(10, 20, 30, 40)),),
            searches=(
                NamedImageSearch(
                    "开始按钮",
                    ImageSearchSpec(ImageRef("开始"), RegionRef("按钮区"), min_confidence=0.8),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert device.actions[0].target == Point(25, 40)
    assert locator.calls == [
        (ImageTemplate("assets/start.png"), Rect(110, 220, 30, 40), 0.8)
    ]


def test_runner_overrides_named_image_search_target_region() -> None:
    """验证图片目标显式区域会覆盖命名搜索区域。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator([ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)])
    script = Script(
        name="named-image-search-click-region-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Click(
                ImageTarget(
                    SearchRef("开始按钮"),
                    region=Rect(1, 2, 30, 40),
                    min_confidence=0.9,
                )
            ),
        ),
        resources=TargetCatalog(
            searches=(
                NamedImageSearch(
                    "开始按钮",
                    ImageSearchSpec(
                        ImageTemplate("assets/start.png"),
                        region=Rect(10, 20, 30, 40),
                        min_confidence=0.8,
                    ),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert locator.calls == [
        (ImageTemplate("assets/start.png"), Rect(101, 202, 30, 40), 0.9)
    ]


def test_runner_reports_unknown_named_image_target() -> None:
    """验证未知图片名称会在图片目标点击时报错。"""
    script = Script(
        name="unknown-named-image-click-runner",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageRef("开始按钮"))),),
    )

    with pytest.raises(UnknownImageNameError, match="unknown image target: 开始按钮"):
        ScriptRunner(
            device=FakeInputDevice(),
            image_locator=SequenceImageLocator([None]),
        ).run(script)


def test_runner_stops_normally_when_image_target_is_missing() -> None:
    """验证图片目标未找到时 runner 正常停止且不执行后续步骤。"""
    device = FakeInputDevice()
    logger = FakeRunEventLogger()
    script = Script(
        name="click-missing-image-target",
        window=ScreenWindow(),
        steps=(
            Click(ImageTarget(ImageTemplate("assets/missing.png"))),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(
        device=device,
        image_locator=SequenceImageLocator([None]),
        logger=logger,
        emit_step_events=True,
    ).run(script)

    assert device.actions == []
    assert [event.event_type for event in logger.events] == [
        "step_started",
        "image_target_missing",
        "step_stopped",
    ]
    assert logger.events[1].details["template"] == "assets/missing.png"


def test_runner_requires_image_locator_for_image_target() -> None:
    """验证图片目标点击需要图像定位端口。"""
    script = Script(
        name="click-image-target-no-locator",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageTemplate("assets/start.png"))),),
    )

    with pytest.raises(RuntimeError, match="image locator"):
        ScriptRunner(device=FakeInputDevice()).run(script)


def test_runner_executes_nested_if_and_repeat_steps() -> None:
    """验证 runner 能递归解释嵌套 If 和 Repeat。"""
    device = FakeInputDevice()
    matching_condition = ColorIs(Point(1, 2), Color(10, 20, 30))
    script = Script(
        name="nested-if-repeat-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=matching_condition,
                then_steps=(
                    Repeat(
                        times=2,
                        steps=(
                            If(
                                condition=matching_condition,
                                then_steps=(Click(Point(3, 4)),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["click", "click"]


def test_runner_wait_until_continues_immediately_when_condition_matches() -> None:
    """验证 WaitUntil 初始条件满足时不等待并继续后续步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="wait-until-immediate",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(3, 4)


def test_runner_wait_until_waits_until_condition_matches() -> None:
    """验证 WaitUntil 会按间隔等待直到条件满足。"""
    device = FakeInputDevice()
    color_reader = SequenceColorReader(
        [
            Color(0, 0, 0),
            Color(0, 0, 0),
            Color(10, 20, 30),
        ]
    )
    script = Script(
        name="wait-until-eventual",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert [action.name for action in device.actions] == ["wait", "wait", "click"]
    assert [action.duration_seconds for action in device.actions if action.name == "wait"] == [0.5, 0.5]
    assert device.actions[-1].target == Point(103, 204)
    assert color_reader.points == [Point(101, 202), Point(101, 202), Point(101, 202)]


def test_runner_wait_until_waits_until_image_exists() -> None:
    """验证 WaitUntil 可以轮询图片存在条件直到满足。"""
    device = FakeInputDevice()
    locator = SequenceImageLocator(
        [
            None,
            ImageMatch(Rect(10, 20, 30, 40), confidence=1.0),
        ]
    )
    script = Script(
        name="wait-until-image",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ImageExists(ImageTemplate("assets/start.png")),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, image_locator=locator).run(script)

    assert [action.name for action in device.actions] == ["wait", "click"]
    assert locator.calls == [
        (ImageTemplate("assets/start.png"), None, 1.0),
        (ImageTemplate("assets/start.png"), None, 1.0),
    ]


def test_runner_wait_until_waits_until_screen_state_matches() -> None:
    """验证 WaitUntil 可以轮询界面状态条件直到满足。"""
    device = FakeInputDevice()
    state_reader = SequenceScreenStateReader(["人物", "主页"])
    script = Script(
        name="wait-until-screen-state",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ScreenStateIs("主页", min_confidence=0.6),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, screen_state_reader=state_reader).run(script)

    assert [action.name for action in device.actions] == ["wait", "click"]
    assert state_reader.calls == [0.6, 0.6]


def test_runner_wait_until_times_out_and_stops_following_steps() -> None:
    """验证 WaitUntil 超时后正常停止且不执行后续步骤。"""
    device = FakeInputDevice()
    logger = FakeRunEventLogger()
    script = Script(
        name="wait-until-timeout",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(
        device=device,
        color_reader=FakeColorReader(Color(0, 0, 0)),
        logger=logger,
        emit_step_events=True,
    ).run(script)

    assert [action.name for action in device.actions] == ["wait", "wait"]
    assert [action.duration_seconds for action in device.actions] == [0.5, 0.5]
    assert [event.event_type for event in logger.events] == [
        "step_started",
        "condition_evaluated",
        "condition_evaluated",
        "condition_evaluated",
        "wait_until_timed_out",
        "step_stopped",
    ]
    assert logger.events[-2].details["attempt"] == "3"


def test_runner_wait_until_caps_wait_to_remaining_timeout() -> None:
    """验证 WaitUntil 最后一轮等待不会超过剩余超时预算。"""
    device = FakeInputDevice()
    script = Script(
        name="wait-until-remaining-budget",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=1,
                interval_seconds=0.6,
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(0, 0, 0))).run(script)

    assert [action.duration_seconds for action in device.actions] == [0.6, 0.4]


def test_runner_wait_until_executes_inside_nested_control_flow() -> None:
    """验证 WaitUntil 可在嵌套控制流中执行。"""
    device = FakeInputDevice()
    condition = ColorIs(Point(1, 2), Color(10, 20, 30))
    script = Script(
        name="wait-until-nested",
        window=ScreenWindow(),
        steps=(
            If(
                condition=condition,
                then_steps=(
                    Repeat(
                        times=2,
                        steps=(
                            WaitUntil(
                                condition=condition,
                                timeout_seconds=1,
                                interval_seconds=0.5,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert device.actions == []


def test_engine_import_does_not_import_macos_adapter() -> None:
    """验证导入 engine 不会顺带导入 macOS adapter。"""
    import sys

    sys.modules.pop("game_automation.platform.macos.adapters", None)

    import game_automation.portable.engine  # noqa: F401

    assert "game_automation.platform.macos.adapters" not in sys.modules
