"""验证函数任务通过公开上下文执行动作与处理局部失败。

测试使用可控时钟、输入和观察端口，不连接桌面或执行工作区源码。
Python 控制流由函数任务用例覆盖，动作不变量由独立核心测试保护。
"""

from pathlib import Path

import pytest

from game_automation.portable.domain import (
    AreaWindow,
    Color,
    ImageMatch,
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    Rect,
    TargetCatalog,
)
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from game_automation.task import (
    Point,
    RunCancelled,
    TargetNotFound,
    TaskContext,
    TaskTimeout,
)


class World:
    """让输入、观察与有效任务时间共享同一可控边界。"""

    def __init__(self, matches=(), *, states=("主页",), recognition_cost=0):
        """保存待返回的观察序列及输入记录。"""
        self.now = 0.0
        self.paused = 0.0
        self.matches = list(matches)
        self.states = list(states)
        self.recognition_cost = recognition_cost
        self.actions = []
        self.searches = []
        self.events = []
        self.cancelled = False

    def clock(self):
        """返回扣除平台暂停时间的有效任务时间。"""
        return self.now - self.paused

    def click(self, target):
        """记录实际送出的点击。"""
        self.actions.append(("click", target))

    def drag_to(self, start, end, duration_seconds=0):
        """记录原子拖拽。"""
        self.actions.append(("drag", start, end, duration_seconds))

    def hotkey(self, keys):
        """记录设备收到的一组按键。"""
        self.actions.append(("hotkey", keys))

    def wait(self, seconds):
        """推进虚拟任务时钟。"""
        self.actions.append(("wait", seconds))
        self.now += seconds

    def locate(self, template, **kwargs):
        """依序返回匹配并把识图成本记入任务时间。"""
        self.now += self.recognition_cost
        self.searches.append((template, kwargs))
        return self.matches.pop(0) if self.matches else None

    def read_current_state(self, **kwargs):
        """依序返回画面状态，末项保持不变。"""
        return self.states.pop(0) if len(self.states) > 1 else self.states[0]

    def read_color(self, point):
        """记录取色坐标并返回固定颜色。"""
        self.actions.append(("color", point))
        return Color(1, 2, 3)

    def is_cancelled(self):
        """返回用户是否已请求取消。"""
        return self.cancelled

    def log(self, message):
        """测试只需收集结构化事件。"""

    def log_event(self, event):
        """保留共享动作内核输出的事件。"""
        self.events.append(event)


def make_context(world, *, runtime_control=None):
    """为测试任务装配同一套输入、观察、取消和任务时钟。"""
    resources = TargetCatalog(
        points=(NamedPoint("入口", Point(3, 4)),),
        images=(NamedImage("按钮图片", ImageTemplate("assets/button.png")),),
        searches=(
            NamedImageSearch(
                "按钮", ImageSearchSpec(ImageRef("按钮图片"), min_confidence=0.9)
            ),
        ),
    )
    task = FunctionTask(
        "测试任务",
        Path("scripts/test.py"),
        "def run(ctx): pass",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        resources=resources,
        requires=TaskRequirements(searches=("按钮",)),
    )
    return TaskContext(
        task.window,
        task.resources,
        device=world,
        color_reader=world,
        image_locator=world,
        screen_state_reader=world,
        cancellation_token=world,
        logger=world,
        clock=world.clock,
        runtime_control=runtime_control,
        emit_step_events=True,
    )


def match(left=110, top=220):
    """构造处于全局逻辑坐标中的图片匹配。"""
    return ImageMatch(Rect(left, top, 10, 10), confidence=0.95)


def test_optional_image_lookup_returns_match_or_none():
    """可选查询保留未命中结果及命名搜索的阈值和窗口区域。"""
    found = match()
    world = World([None, found])
    context = make_context(world)
    assert context.find("按钮") is None
    assert context.find("按钮") == found
    assert world.searches[0][0] == ImageTemplate("assets/button.png")
    assert world.searches[0][1]["region"] == Rect(100, 200, 800, 600)
    assert world.searches[0][1]["min_confidence"] == 0.9


def test_simple_inputs_reuse_window_coordinates_and_atomic_device():
    """函数任务的固定输入沿用窗口换算和原子按键契约。"""
    world = World()
    context = make_context(world)
    context.click("入口")
    context.hotkey("command", "v")
    context.drag(Point(1, 2), Point(3, 4), duration=0.2)
    assert world.actions == [
        ("click", Point(103, 204)),
        ("hotkey", ("command", "v")),
        ("drag", Point(101, 202), Point(103, 204), 0.2),
    ]


def test_wait_image_returns_match_and_click_relocates_before_input():
    """等待得到的旧匹配不会被随后点击复用。"""
    world = World([None, match(110), match(130), match(150)])
    context = make_context(world)
    assert context.wait_image("按钮", timeout=5) == match(110)
    context.click_image("按钮", timeout=5, offset=Point(2, 3))
    assert world.actions == [("wait", 0.5), ("click", Point(157, 228))]


def test_missing_required_image_can_be_handled_locally():
    """必需点击缺图可在任务局部处理，随后仍能执行另一分支。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TargetNotFound, match="图片目标未找到"):
        context.click_image("按钮")
    context.click("入口")
    assert world.actions == [("click", Point(103, 204))]


def test_wait_timeout_clips_wait_and_allows_following_task_branch():
    """条件等待使用有效任务时间，到期后可以执行局部恢复分支。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TaskTimeout):
        context.wait_image("按钮", timeout=0.75, interval=0.5)
    context.click("入口")
    assert world.actions == [("wait", 0.5), ("wait", 0.25), ("click", Point(103, 204))]


def test_unbounded_wait_still_observes_finite_outer_deadline():
    """无限条件等待受外层显式限时作用域约束。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TaskTimeout):
        with context.deadline(2):
            context.wait_image("按钮", timeout=None, interval=10)
    context.click("入口")
    assert world.actions == [("wait", 2), ("click", Point(103, 204))]


def test_nested_deadline_preserves_earliest_outer_scope():
    """较长的内层期限不能覆盖外层剩余预算。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TaskTimeout):
        with context.deadline(2):
            with context.deadline(10):
                context.wait(8)
    assert world.actions == [("wait", 2)]
    context.wait(3)
    assert world.clock() == 5


def test_handled_inner_deadline_restores_outer_remaining_budget():
    """局部处理内层超时后仍沿用外层原来的截止时间。"""
    world = World()
    context = make_context(world)
    with context.deadline(4):
        with pytest.raises(TaskTimeout):
            with context.deadline(1):
                context.wait(10)
        context.wait(1)
    assert world.clock() == 2


def test_slow_recognition_cannot_send_click_after_deadline():
    """识别本身耗尽预算时不会投递点击。"""
    world = World([match()], recognition_cost=3)
    context = make_context(world)
    with pytest.raises(TaskTimeout):
        with context.deadline(2):
            context.click_image("按钮")
    assert world.actions == []


def test_platform_pause_does_not_consume_task_deadline():
    """平台暂停经过的墙上时间从任务预算扣除。"""
    world = World([match()])
    context = make_context(world)
    with context.deadline(2):
        world.now += 100
        world.paused += 100
        context.wait(1)
        assert context.find("按钮") == match()
    assert world.clock() == 1


def test_wait_state_and_state_query_use_same_reader():
    """状态等待与查询使用本次运行装配的状态端口。"""
    world = World(states=("活动", "主页"))
    context = make_context(world)
    context.wait_state("主页", timeout=3)
    assert context.state() == "主页"
    assert world.actions == [("wait", 0.5)]


def test_color_lookup_resolves_named_point_in_window():
    """取色使用固定窗口中的命名点位。"""
    world = World()
    context = make_context(world)
    assert context.color("入口") == Color(1, 2, 3)
    assert world.actions == [("color", Point(103, 204))]


def test_cancel_is_a_termination_signal_outside_ordinary_exception_recovery():
    """取消穿过普通异常处理，并保留高于期限的优先级。"""
    world = World()
    context = make_context(world)
    with pytest.raises(BaseException, match="script run cancelled") as caught:
        with context.deadline(1):
            world.now = 2
            world.cancelled = True
            try:
                context.click("入口")
            except Exception:
                context.click("入口")
    assert not isinstance(caught.value, Exception)
    assert world.actions == []


def test_input_preparation_uses_shared_runtime_control_once():
    """点击提交通过同一原生控制边界，保留唯一输入所有者。"""

    class Control:
        """记录每次完整输入准备的执行。"""

        def __init__(self):
            """初始化准备计数。"""
            self.calls = 0

        def execute_input(self, action):
            """由控制边界完成一次输入准备和提交。"""
            self.calls += 1
            return action()

    control = Control()
    world = World([match()])
    context = make_context(world, runtime_control=control)
    context.click_image("按钮")
    assert control.calls == 1
    assert world.actions == [("click", Point(115, 225))]


def test_actual_actions_produce_shared_structured_events():
    """函数任务的实际动作沿用现有结构化事件及递增步骤路径。"""
    world = World([match()])
    context = make_context(world)
    context.find("按钮")
    context.click("入口")
    started = [event for event in world.events if event.event_type == "step_started"]
    assert [(event.step_path, event.step_type) for event in started] == [
        ("1", "Observe"),
        ("2", "Click"),
    ]
    assert any(
        event.event_type == "click_performed" and event.step_path == "2"
        for event in world.events
    )


@pytest.mark.parametrize("seconds", [True, "1", None, -1, float("nan"), float("inf")])
def test_time_arguments_reject_invalid_values(seconds):
    """时间参数在作者接口边界拒绝无效输入。"""
    context = make_context(World())
    with pytest.raises(ValueError):
        context.wait(seconds)


@pytest.mark.parametrize("seconds", [0, -1, True, float("inf"), float("nan")])
def test_deadline_requires_positive_finite_seconds(seconds):
    """显式限时作用域仅接受正的有限秒数。"""
    context = make_context(World())
    with pytest.raises(ValueError):
        with context.deadline(seconds):
            pass


def test_cancel_during_device_wait_stops_before_following_input():
    """等待期间收到停止后，任务不能继续下一次输入。"""

    class CancellingWorld(World):
        """在可取消设备边界返回时发布停止信号。"""

        def wait(self, seconds):
            """推进时间后模拟用户停止。"""
            super().wait(seconds)
            self.cancelled = True

    world = CancellingWorld()
    context = make_context(world)
    with pytest.raises(BaseException, match="script run cancelled"):
        context.wait(1)
        context.hotkey("enter")
    assert world.actions == [("wait", 1)]


def test_window_recovery_repeats_only_unsent_input_preparation():
    """原生控制边界恢复后重新识图，最终只提交一次点击。"""

    class RetryPreparation(Exception):
        """表示尚未发送输入时的临时窗口变化。"""

    class RetryingWorld(World):
        """首次识别拒绝准备，恢复后返回新的匹配。"""

        def __init__(self):
            """初始化一次未提交准备的故障。"""
            super().__init__([match(140)])
            self.preparations = 0

        def locate(self, template, **kwargs):
            """保证故障发生于点击提交之前。"""
            self.preparations += 1
            if self.preparations == 1:
                raise RetryPreparation()
            return super().locate(template, **kwargs)

    class RecoveryControl:
        """模拟已有原生会话的未提交准备恢复。"""

        def execute_input(self, action):
            """只重试尚未提交的准备回调。"""
            try:
                return action()
            except RetryPreparation:
                return action()

    world = RetryingWorld()
    context = make_context(world, runtime_control=RecoveryControl())
    context.click_image("按钮")
    assert world.preparations == 2
    assert world.actions == [("click", Point(145, 225))]


def test_empty_deadline_reports_its_own_scope_without_relabeling_prior_action():
    """空限时段也拥有独立事件，先前成功动作不被标记成超时。"""
    world = World()
    context = make_context(world)
    context.click("入口")
    with pytest.raises(TaskTimeout) as caught:
        with context.deadline(1):
            world.now = 2
    assert caught.value.scope_id
    expired = [event for event in world.events if event.event_type == "scope_expired"]
    assert len(expired) == 1
    assert expired[0].step_path == caught.value.scope_id
    assert expired[0].step_path != "1"
    assert not any(
        event.step_path == "1" and event.status == "timed_out" for event in world.events
    )


def test_nested_timeout_identifies_the_outer_scope_that_actually_expired():
    """内层较长期限不能接管外层超时的归属。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TaskTimeout) as caught:
        with context.deadline(1) as outer_scope:
            with context.deadline(10):
                context.wait(3)
    assert caught.value.scope_id == outer_scope


@pytest.mark.parametrize(
    "anchor, expected",
    [
        ("top_left", Point(112, 223)),
        ("bottom_right", Point(122, 233)),
    ],
)
def test_image_click_resolves_anchor_offset_and_explicit_window_region(
    anchor, expected
):
    """显式区域按窗口偏移，点击使用全局匹配锚点加局部偏移。"""
    from game_automation.portable.domain import ImageTarget

    world = World([match()])
    context = make_context(world)

    context.click(
        ImageTarget(
            ImageRef("按钮图片"),
            region=Rect(5, 6, 20, 30),
            min_confidence=0.8,
            anchor=anchor,
            offset=Point(2, 3),
        )
    )

    assert world.searches[0][1]["region"] == Rect(105, 206, 20, 30)
    assert world.searches[0][1]["min_confidence"] == 0.8
    assert world.actions == [("click", expected)]


def test_click_image_override_and_continuous_hotkeys_share_latest_match():
    """置信度覆盖同时用于等待和最终重定位，连续按键不会额外观察。"""
    world = World([None, match(110), match(150)])
    context = make_context(world)

    context.click_image(
        "按钮",
        timeout=1,
        interval=0.25,
        min_confidence=0.7,
        then_hotkeys=(("command", "v"), ("enter",)),
    )

    assert [options["min_confidence"] for _, options in world.searches] == [
        0.7,
        0.7,
        0.7,
    ]
    assert world.actions == [
        ("wait", 0.25),
        ("click", Point(155, 225)),
        ("hotkey", ("command", "v")),
        ("hotkey", ("enter",)),
    ]


@pytest.mark.parametrize("confidence", [True, 0, -0.1, 1.1, float("nan"), float("inf")])
def test_image_confidence_override_rejects_invalid_values_before_observation(
    confidence,
):
    """无效阈值在设备或观察端口副作用之前拒绝。"""
    world = World([match()])
    context = make_context(world)

    with pytest.raises(ValueError):
        context.click_image("按钮", timeout=1, min_confidence=confidence)

    assert world.searches == []
    assert world.actions == []


@pytest.mark.parametrize("cancel_during_lookup", [False, True])
def test_click_image_rechecks_target_and_cancellation_after_successful_wait(
    cancel_during_lookup,
):
    """等待成功后的最终定位缺图或收到停止时，点击和连续按键均不提交。"""

    class ChangingWorld(World):
        """在最终定位边界改变观测结果或取消状态。"""

        def locate(self, template, **kwargs):
            """保留等待成功，并在第二次观察触发本例的变化。"""
            result = super().locate(template, **kwargs)
            if len(self.searches) == 2:
                self.cancelled = cancel_during_lookup
            return result

    world = ChangingWorld([match(), match() if cancel_during_lookup else None])
    context = make_context(world)

    with pytest.raises(RunCancelled if cancel_during_lookup else TargetNotFound):
        context.click_image("按钮", timeout=1, then_hotkeys=(("enter",),))

    assert len(world.searches) == 2
    assert world.actions == []


@pytest.mark.parametrize("cancel_after", ["click", "hotkey"])
def test_continuous_hotkeys_check_cancellation_between_atomic_inputs(cancel_after):
    """点击与连续组合键每次提交后都检查停止，已经发生的输入保留一次。"""

    class CancellingWorld(World):
        """在本例指定的原子输入完成后发布停止请求。"""

        def click(self, target):
            """记录点击，并按指定边界发布停止。"""
            super().click(target)
            self.cancelled = cancel_after == "click"

        def hotkey(self, keys):
            """记录首组组合键，之后拒绝下一组输入。"""
            super().hotkey(keys)
            self.cancelled = cancel_after == "hotkey"

    world = CancellingWorld([match()])
    context = make_context(world)

    with pytest.raises(RunCancelled):
        context.click_image("按钮", then_hotkeys=(("command", "v"), ("enter",)))

    expected = [("click", Point(115, 225))]
    if cancel_after == "hotkey":
        expected.append(("hotkey", ("command", "v")))
    assert world.actions == expected
    assert len(world.searches) == 1


@pytest.mark.parametrize(
    "keys",
    [
        (),
        (None,),
        ({},),
        ("command", 1),
        ("command", ""),
        ("command", "typo"),
        ("command", "command"),
    ],
)
def test_invalid_hotkeys_fail_before_any_atomic_input(keys):
    """空组合、非法键名和重复键在作者接口边界拒绝。"""
    world = World()
    context = make_context(world)

    with pytest.raises(ValueError):
        context.hotkey(*keys)

    assert world.actions == []


def test_unbounded_image_wait_stops_when_user_cancels():
    """未设截止时间的图片等待仍在每轮等待后响应用户停止。"""

    class CancellingWorld(World):
        """第一次轮询等待完成后发布停止请求。"""

        def wait(self, seconds):
            """推进时钟并模拟用户主动停止。"""
            super().wait(seconds)
            self.cancelled = True

    world = CancellingWorld()
    context = make_context(world)

    with pytest.raises(RunCancelled):
        context.wait_image("按钮", timeout=None, interval=0.25)

    assert len(world.searches) == 1
    assert world.actions == [("wait", 0.25)]


def test_nested_offsets_apply_after_image_anchor_without_duplicate_window_offset():
    """任意层偏移在全局匹配锚点上累计，窗口原点只应用到搜索区域。"""
    from game_automation.portable.domain import ImageTarget, OffsetTarget

    world = World([match()])
    context = make_context(world)
    target = OffsetTarget(
        OffsetTarget(ImageTarget(ImageRef("按钮图片"), anchor="top_left"), Point(1, 2)),
        Point(3, 4),
    )

    context.click(target)

    assert world.actions == [("click", Point(114, 226))]
    assert world.searches[0][1]["region"] == Rect(100, 200, 800, 600)


def test_negative_drag_duration_fails_before_atomic_input():
    """拖拽负时间在直接作者接口拒绝，设备没有收到任何输入。"""
    world = World()
    context = make_context(world)

    with pytest.raises(ValueError):
        context.drag(Point(1, 2), Point(3, 4), duration=-0.1)

    assert world.actions == []
