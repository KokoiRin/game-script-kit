"""通过直接作者接口验证执行核心的输入、恢复与独立作用域。

本模块只装配纯窗口、资源和值对象以及 fake ports，不依赖任务文件或旧步骤树。
"""

import pytest

from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import ImageMatch, ImageTemplate
from game_automation.portable.domain.point_aliases import (
    NamedImage,
    NamedPoint,
    TargetCatalog,
)
from game_automation.portable.domain.targets import ImageTarget
from game_automation.portable.domain.windows import AreaWindow
from game_automation.task import RunCancelled, TargetNotFound, TaskContext, TaskTimeout


class World:
    """记录输入与事件，用可控任务时钟替换系统时间。"""

    def __init__(self):
        """初始化独立运行需要的 fake 状态。"""
        self.now = 0.0
        self.cancelled = False
        self.inputs = []
        self.matches = []
        self.events = []
        self.reads = 0

    def clock(self):
        """返回有效任务时间。"""
        return self.now

    def is_cancelled(self):
        """读取用户终止请求。"""
        return self.cancelled

    def click(self, point):
        """记录一次真正提交的点击。"""
        self.inputs.append(("click", point))

    def hotkey(self, keys):
        """记录一次原子按键。"""
        self.inputs.append(("hotkey", keys))

    def wait(self, seconds):
        """推进有效任务时间。"""
        self.now += seconds

    def locate(self, template, **kwargs):
        """每次调用读取新的匹配。"""
        self.reads += 1
        return self.matches.pop(0) if self.matches else None

    def log(self, message):
        """测试只保留结构化结果。"""

    def log_event(self, event):
        """收集操作和作用域的可观察事件。"""
        self.events.append(event)


def make_context(world, *, control=None):
    """直接装配核心，构造过程不经过任务定义或兼容解释器。"""
    return TaskContext(
        AreaWindow(Rect(100, 200, 80, 60)),
        TargetCatalog(
            points=(NamedPoint("button", Point(2, 3)),),
            images=(NamedImage("image", ImageTemplate("button.png")),),
        ),
        device=world,
        clock=world.clock,
        cancellation_token=world,
        image_locator=world,
        runtime_control=control,
        logger=world,
        emit_step_events=True,
    )


def test_checkpoint_failure_cannot_enter_recovery_after_user_cancel():
    """观察检查点失败时同时到达的取消仍穿过普通恢复逻辑。"""
    world = World()
    context = make_context(world)
    recovered = []

    def failing_checkpoint():
        """模拟观察失败期间用户发出停止请求。"""
        world.cancelled = True
        raise RuntimeError("checkpoint read failed")

    with pytest.raises(RunCancelled):
        with context.scope(checkpoint=failing_checkpoint):
            try:
                context.hotkey("enter")
            except Exception:
                recovered.append(True)

    assert recovered == []
    assert world.inputs == []


def test_plain_function_handles_missing_target_and_recovers_after_timeout():
    """普通 Python 可以局部恢复缺图和期限，然后继续一次新输入。"""
    world = World()
    context = make_context(world)

    def run(ctx):
        """把业务分支交给普通函数控制流。"""
        try:
            ctx.click_image("image")
        except TargetNotFound:
            try:
                ctx.wait_image("image", timeout=1, interval=0.6)
            except TaskTimeout:
                ctx.click("button")

    run(context)
    assert world.now == 1
    assert world.inputs == [("click", Point(102, 203))]


def test_expiring_empty_scope_preserves_previous_successful_operation():
    """作用域退出发生的超时拥有独立身份，成功动作事件保持成功。"""
    world = World()
    context = make_context(world)
    context.click("button")
    with pytest.raises(TaskTimeout) as caught:
        with context.deadline(1) as scope_id:
            world.now = 1
    assert caught.value.scope_id == scope_id
    action_events = [
        event.event_type for event in world.events if event.step_path == "1"
    ]
    assert action_events == [
        "step_started",
        "click_resolved",
        "click_performed",
        "step_succeeded",
    ]
    scope_events = [
        event.event_type for event in world.events if event.step_path == scope_id
    ]
    assert scope_events == ["scope_started", "scope_expired", "scope_finished"]


def test_longer_inner_scope_cannot_claim_expired_outer_scope():
    """调用方根据异常身份只处理自己拥有的期限。"""
    world = World()
    context = make_context(world)
    with pytest.raises(TaskTimeout) as caught:
        with context.deadline(1) as outer:
            with context.deadline(10) as inner:
                context.wait(5)
    assert caught.value.scope_id == outer
    assert caught.value.scope_id != inner
    assert world.now == 1


def test_outer_checkpoint_runs_before_inner_and_interrupt_crosses_inner_scope():
    """通用检查点保留外层优先级，嵌套作用域只负责自己的退出。"""

    class OuterStopped(BaseException):
        """模拟外层调用方拥有的控制信号。"""

    world = World()
    context = make_context(world)
    checks = []

    def outer_check():
        """终止外层调用，不让内层检查点抢先执行。"""
        checks.append("outer")
        raise OuterStopped()

    def inner_check():
        """记录内层检查点是否被错误调用。"""
        checks.append("inner")

    with pytest.raises(OuterStopped):
        with context.scope(checkpoint=outer_check):
            with context.scope(checkpoint=inner_check):
                context.click("button")
    assert checks == ["outer"]
    assert world.inputs == []


def test_continuous_hotkeys_use_pure_values_without_reading_guard_again():
    """点击后的连续按键共享原准备结果，期间仍检查取消和期限。"""
    world = World()
    world.matches = [ImageMatch(Rect(110, 210, 10, 10), 1)]
    context = make_context(world)
    guard_reads = []
    with context.scope(checkpoint=lambda: guard_reads.append("guard")):
        context.click(
            ImageTarget(ImageTemplate("button.png")),
            then_hotkeys=(("command", "v"), ("enter",)),
        )
    assert world.reads == 1
    assert guard_reads == ["guard"]
    assert world.inputs == [
        ("click", Point(115, 215)),
        ("hotkey", ("command", "v")),
        ("hotkey", ("enter",)),
    ]


def test_continuous_hotkeys_stop_after_first_key_consumes_budget():
    """连续按键之间到期时，下一组按键不会被发送。"""

    class SlowKeys(World):
        """在一个原子按键结束后耗尽时间预算。"""

        def hotkey(self, keys):
            """提交首组按键后模拟设备耗时。"""
            super().hotkey(keys)
            self.now += 2

    world = SlowKeys()
    context = make_context(world)
    with pytest.raises(TaskTimeout):
        with context.deadline(1):
            context.click("button", then_hotkeys=(("command", "v"), ("enter",)))
    assert world.inputs == [("click", Point(102, 203)), ("hotkey", ("command", "v"))]


def test_uncommitted_recovery_relocates_before_only_submission():
    """平台重新准备未提交输入时，再次定位会获得恢复后的坐标。"""

    class RecoverControl:
        """丢弃第一次尚未提交的准备结果。"""

        def execute_input(self, operation):
            """在定位返回前模拟一次可恢复展示变化。"""
            try:
                return operation()
            except InterruptedError:
                return operation()

    class RecoverWorld(World):
        """第一次定位失败，恢复后目标已经移动。"""

        def locate(self, template, **kwargs):
            """提供恢复前后不同的观测结果。"""
            self.reads += 1
            if self.reads == 1:
                raise InterruptedError()
            return ImageMatch(Rect(130, 240, 10, 10), 1)

    world = RecoverWorld()
    context = make_context(world, control=RecoverControl())
    context.click_image("image")
    assert world.reads == 2
    assert world.inputs == [("click", Point(135, 245))]
    assert sum(event.event_type == "click_performed" for event in world.events) == 1


def test_committed_input_is_never_replayed_after_recovery_consumes_budget():
    """提交后平台完成恢复返回，核心只报告到期并保留唯一输入。"""
    world = World()

    class RecoverAfterCommit:
        """模拟必要释放完成后才返回的平台控制。"""

        def execute_input(self, operation):
            """提交一次输入，再模拟有效任务时间经过。"""
            result = operation()
            world.now += 2
            return result

    context = make_context(world, control=RecoverAfterCommit())
    with pytest.raises(TaskTimeout):
        with context.deadline(1):
            context.click("button")
    assert world.inputs == [("click", Point(102, 203))]


def test_cancel_at_expiry_crosses_ordinary_exception_handler():
    """用户取消优先于同一时刻的期限，并穿过普通异常恢复。"""
    world = World()
    context = make_context(world)
    with pytest.raises(RunCancelled):
        with context.deadline(1):
            world.now = 1
            world.cancelled = True
            try:
                context.click("button")
            except Exception:
                pytest.fail("终止取消被普通异常捕获")
    assert world.inputs == []


def test_cancel_during_failed_input_remains_a_termination_signal():
    """平台同时报告故障和用户停止时，核心返回终止取消。"""

    class FailingWorld(World):
        """在平台输入边界发布停止并返回普通错误。"""

        def click(self, point):
            """模拟输入失败与用户停止同时到达。"""
            self.cancelled = True
            raise RuntimeError("input failed")

    world = FailingWorld()
    context = make_context(world)
    with pytest.raises(RunCancelled):
        context.click("button")


def test_checkpoint_can_use_public_observation_without_reentering_itself():
    """检查点可以自然调用公开观察，核心保留单次检查和输入顺序。"""
    world = World()
    world.matches = [ImageMatch(Rect(110, 210, 10, 10), 1)]
    context = make_context(world)
    checks = []

    def checkpoint():
        """使用作者接口读取当前图片。"""
        checks.append(context.find("image"))

    with context.scope(checkpoint=checkpoint):
        context.click("button")
    assert len(checks) == 1
    assert world.reads == 1
    assert world.inputs == [("click", Point(102, 203))]


def test_observation_inside_checkpoint_still_checks_the_outer_deadline():
    """抑制检查点重入时，观察自身仍检查取消与有效期限。"""

    class SlowWorld(World):
        """用慢观察耗尽本层有效时间预算。"""

        def locate(self, template, **kwargs):
            """返回图片前推进有效任务时间。"""
            self.now += 2
            return ImageMatch(Rect(110, 210, 10, 10), 1)

    world = SlowWorld()
    context = make_context(world)
    with pytest.raises(TaskTimeout) as caught:
        with context.scope(
            seconds=1, checkpoint=lambda: context.find("image")
        ) as owner:
            context.click("button")
    assert caught.value.scope_id == owner
    assert world.inputs == []
