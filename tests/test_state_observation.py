"""验证持续状态观察的稳定确认、停止与失败语义。

本 module 通过内存探测结果验证公开会话，不启动 GUI、采集真实画面或执行输入。
"""

import threading
import time

import pytest

from game_automation.portable.application.state_observation import StateObservation
from game_automation.portable.domain import (
    ImageMatch,
    ImageTemplate,
    Rect,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)


def result(state="页面", found=True):
    """构造有命中或未知的独立探测结果。"""
    candidate = ScreenStateCandidate(state, ImageTemplate("sample.png"))
    match = ImageMatch(Rect(10, 20, 30, 40), 0.95) if found else None
    return ScreenStateProbeResult((ScreenStateCandidateResult(candidate, match, 2),), 2)


def wait_until(predicate):
    """在有界时间内等待后台公开状态，避免无限等待测试。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    assert predicate()


class Probe:
    def __init__(self):
        """初始化观察证据和关闭事件。"""
        self.value = result()
        self.closed = threading.Event()

    def read(self):
        """返回当前结果，或模拟捕获失败。"""
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    def close(self):
        """标记探测资源已回收。"""
        self.closed.set()


def test_observation_confirms_state_then_invalidates_it_on_failure():
    """连续确认后输出状态，截图失败立即撤销旧状态并保留错误。"""
    probe = Probe()
    observer = StateObservation()
    try:
        observer.start(probe, hz=5, confirmations=2)
        wait_until(lambda: observer.snapshot().current_state == "页面")
        assert observer.snapshot().sequence >= 2
        assert observer.snapshot().sample.result.candidates[0].found is True
        probe.value = RuntimeError("目标窗口已关闭")
        wait_until(lambda: observer.snapshot().phase == "unavailable")
        assert observer.snapshot().current_state == "未知"
        assert "已关闭" in observer.snapshot().error
        assert observer.snapshot().performance.failures >= 1
    finally:
        assert observer.stop()
    assert not observer.snapshot().running
    assert probe.closed.is_set()


def test_observation_rejects_duplicate_start_and_invalid_frequency():
    """单个观察器不并发启动，频率必须处于可配置范围。"""
    observer = StateObservation()
    with pytest.raises(ValueError):
        observer.start(Probe(), hz=0)
    try:
        observer.start(Probe(), hz=5)
        with pytest.raises(RuntimeError, match="running"):
            observer.start(Probe(), hz=5)
    finally:
        observer.stop()


def test_stopped_observation_cannot_report_a_live_state():
    """停止后状态失效，不能被误当成实时判断。"""
    observer = StateObservation()
    observer.start(Probe(), hz=5, confirmations=1)
    wait_until(lambda: observer.snapshot().sequence >= 1)
    assert observer.stop()
    assert observer.snapshot().phase == "stopped"
    assert observer.snapshot().current_state == "未知"


@pytest.mark.parametrize("late_error", [False, True])
def test_stop_revokes_state_before_blocked_read_finishes(late_error):
    """停止立即撤销状态，迟到成功或失败均不能覆盖停止中。"""
    entered, release, closing, closed = (threading.Event() for _ in range(4))

    class Blocked(Probe):
        def read(self):
            """等待模拟卡住的截图。"""
            entered.set()
            release.wait(2)
            if late_error:
                raise RuntimeError("迟到错误")
            return result()

        def close(self):
            """保持清理进行中以观察迟到发布屏障。"""
            closing.set()
            closed.wait(2)

    observer = StateObservation()
    try:
        observer.start(Blocked(), confirmations=1)
        assert entered.wait(1)
        assert observer.request_stop().phase == "stopping"
        release.set()
        assert closing.wait(1)
        assert observer.snapshot().phase == "stopping"
        assert observer.snapshot().current_state == "未知"
        assert observer.snapshot().sample is None
        assert observer.snapshot().performance.attempts == 0
        assert observer.snapshot().performance.last_failure_at is None
        assert observer.snapshot().performance.last_failure_message == ""
    finally:
        release.set()
        closed.set()
        assert observer.stop()


def test_first_frame_timeout_and_slow_result_are_stale():
    """首帧卡住与超龄完成结果都不能成为已知状态。"""
    now = [0.0]
    entered, release = threading.Event(), threading.Event()

    class Slow(Probe):
        def read(self):
            """模拟超过时效预算才完成的采集。"""
            if entered.is_set():
                threading.Event().wait(0.2)
            entered.set()
            release.wait(2)
            return result()

    observer = StateObservation(clock=lambda: now[0])
    try:
        observer.start(Slow(), hz=5, confirmations=1)
        assert entered.wait(1)
        now[0] = 3
        assert observer.snapshot().phase == "stale"
        release.set()
        wait_until(lambda: observer.snapshot().sequence >= 1)
        assert observer.snapshot().current_state == "未知"
        assert observer.snapshot().performance.stale_results == 1
        assert observer.snapshot().performance.over_budget == 1
    finally:
        release.set()
        observer.stop()


def test_confirmation_restarts_after_long_capture_gap():
    """无人轮询的长间隔也打断连续确认，不能沿用旧确认次数。"""
    now = [0.0]
    observer = StateObservation(clock=lambda: now[0])
    try:
        observer.start(Probe(), hz=5, confirmations=2)
        wait_until(lambda: observer.snapshot().sequence == 1)
        now[0] = 3
        wait_until(lambda: observer.snapshot().sequence == 2)
        assert observer.snapshot().current_state == "未知"
        wait_until(lambda: observer.snapshot().sequence >= 3)
        assert observer.snapshot().current_state == "页面"
    finally:
        observer.stop()


def test_sample_wall_timestamp_is_from_capture_start():
    """画面时间保留采集开始值，不被匹配完成后的时间替换。"""
    wall = [100.0]

    class TimedProbe(Probe):
        def read(self):
            """模拟识别期间墙上时间前进。"""
            wall[0] = 200.0
            return result()

    observer = StateObservation(wall_clock=lambda: wall[0])
    try:
        observer.start(TimedProbe(), hz=1, confirmations=1)
        wait_until(lambda: observer.snapshot().sequence == 1)
        assert observer.snapshot().sample.observed_at == 100.0
    finally:
        observer.stop()


def test_performance_counts_rounds_and_retains_stopped_session():
    """轮次统计来自采样而非轮询，停止保留且新观察重置。"""
    observer = StateObservation()
    try:
        observer.start(Probe(), hz=1, confirmations=1)
        wait_until(lambda: observer.snapshot().sequence == 1)
        before = observer.snapshot().performance
        assert before.attempts == 1
        assert before.material_count == 1
        assert before.screenshot_ms is None
        for _ in range(10):
            assert observer.snapshot().performance == before
        observer.stop()
        assert observer.snapshot().performance == before
        observer.start(Probe(), hz=1)
        wait_until(lambda: observer.snapshot().sequence == 1)
        assert observer.snapshot().performance.attempts == 1
    finally:
        observer.stop()


def test_performance_rolling_window_and_failure_budget():
    """所有完成轮次计入预算与失败，分位数最多覆盖最近120轮。"""
    from game_automation.portable.application.state_observation import (
        ObservationPerformance,
    )

    stats = ObservationPerformance()
    for number in range(125):
        stats = stats.record(float(number), budget_ms=100, failed=number == 124)
    assert stats.attempts == 125
    assert stats.failures == 1
    assert stats.over_budget == 24
    assert len(stats.rounds_ms) == 120
    assert stats.percentile(0.5) == 64
    assert stats.percentile(0.95) == 118
    assert max(stats.rounds_ms) == 124


def test_recent_failure_survives_recovery_and_resets_on_restart():
    """成功恢复清空实时错误但保留有界失败历史，新观察清空历史。"""
    probe = Probe()
    probe.value = RuntimeError("窗口读取失败" + "细节" * 1000)
    observer = StateObservation(wall_clock=lambda: 1234.5)
    try:
        observer.start(probe, hz=5, confirmations=1)
        wait_until(lambda: observer.snapshot().phase == "unavailable")
        failed = observer.snapshot().performance
        assert failed.last_failure_at == 1234.5
        assert failed.last_failure_message.startswith("窗口读取失败")
        assert len(failed.last_failure_message) == 1024
        probe.value = result()
        wait_until(lambda: observer.snapshot().current_state == "页面")
        recovered = observer.snapshot()
        assert recovered.error == ""
        assert recovered.performance.last_failure_message == failed.last_failure_message
        assert recovered.performance.last_failure_at == 1234.5
        observer.stop()
        assert (
            observer.snapshot().performance.last_failure_message
            == failed.last_failure_message
        )
        observer.start(Probe(), hz=5, confirmations=1)
        wait_until(lambda: observer.snapshot().sequence >= 1)
        assert observer.snapshot().performance.last_failure_message == ""
        assert observer.snapshot().performance.last_failure_at is None
    finally:
        observer.stop()


def test_cached_source_proof_never_confirms_twice_or_refreshes_age():
    """重复读取同一源证据不确认第二次，也不能用读取时间续期。"""
    from dataclasses import replace

    from game_automation.portable.domain.screen_state import FrameProof

    now = [100.0]
    probe = Probe()
    probe.value = replace(result(), proof=FrameProof(1, 99.5))
    observer = StateObservation(clock=lambda: now[0])
    try:
        observer.start(probe, hz=5, confirmations=2)
        wait_until(lambda: observer.snapshot().sequence >= 2)
        assert observer.snapshot().current_state == "未知"
        assert observer.snapshot().age_ms == pytest.approx(500)
        assert observer.snapshot().performance.duplicate_results >= 1
        probe.value = replace(result(), proof=FrameProof(2, 100.0, "idle"))
        wait_until(lambda: observer.snapshot().current_state == "页面")
        now[0] = 103
        wait_until(lambda: observer.snapshot().phase == "stale")
        assert observer.snapshot().current_state == "未知"
    finally:
        observer.stop()


def test_old_stream_frame_is_stale_even_when_read_is_fast():
    """源事件已过期时，快速读取与匹配不能使其重新有效。"""
    from dataclasses import replace

    from game_automation.portable.domain.screen_state import FrameProof

    probe = Probe()
    probe.value = replace(result(), proof=FrameProof(1, 95))
    observer = StateObservation(clock=lambda: 100)
    try:
        observer.start(probe, hz=5, confirmations=1)
        wait_until(lambda: observer.snapshot().sequence >= 1)
        value = observer.snapshot()
        assert value.phase == "stale"
        assert value.current_state == "未知"
        assert value.performance.stale_results >= 1
        assert value.performance.round_ms == 0
        assert value.performance.source_age_ms == 5000
    finally:
        observer.stop()


def test_cleanup_failure_keeps_slot_occupied_until_backend_recovery():
    """停流失败不能谎报已停止或允许新流并发启动。"""

    class CannotClose(Probe):
        def close(self):
            """模拟系统不能确认停流。"""
            raise RuntimeError("停流未确认")

    observer = StateObservation()
    observer.start(CannotClose(), hz=5)
    wait_until(lambda: observer.snapshot().sequence >= 1)
    assert observer.stop() is False
    assert observer.snapshot().phase == "stopping"
    assert "停流未确认" in observer.snapshot().error
    with pytest.raises(RuntimeError, match="running"):
        observer.start(Probe())


def test_stream_source_future_timestamp_is_unavailable():
    """跨时钟转换出的未来时间不能作为零龄画面。"""
    from dataclasses import replace

    from game_automation.portable.domain.screen_state import FrameProof

    probe = Probe()
    probe.value = replace(result(), proof=FrameProof(1, 101))
    observer = StateObservation(clock=lambda: 100)
    try:
        observer.start(probe, hz=5, confirmations=1)
        wait_until(lambda: observer.snapshot().phase == "unavailable")
        assert observer.snapshot().current_state == "未知"
        assert "源时间无效" in observer.snapshot().error
    finally:
        observer.stop()


def test_wire_reports_processing_cost_separately_from_source_age():
    """协议耗时是本轮处理，不把缓存源年龄冒充处理成本。"""
    from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
        observation_wire,
    )
    from game_automation.portable.application.state_observation import (
        ObservationPhase,
        ObservationSample,
        ObservationSnapshot,
    )

    sample = ObservationSample(10, 11.5, 1000, result(), 5, 11.49)
    wire = observation_wire(
        ObservationSnapshot(
            phase=ObservationPhase.OBSERVING, sample=sample, age_ms=1500
        )
    )
    assert wire["elapsed_ms"] == pytest.approx(10)
    assert wire["age_ms"] == 1500
