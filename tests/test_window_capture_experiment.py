"""用fake验证采集实验计数、单槽失效及停止，不访问真实桌面或权限。"""

import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

path = Path(__file__).resolve().parents[1] / "tools" / "benchmark_window_capture.py"
if not path.is_file():
    path = Path(__file__).with_name("benchmark_window_capture.py")
spec = importlib.util.spec_from_file_location("capture_bench", path)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def test_slot_keeps_one_frame_and_idle_does_not_create_confirmation():
    """idle与重复读取不能伪造新完整帧。"""
    s = b.LatestSlot()
    s.publish("idle")
    with pytest.raises(RuntimeError, match="waiting"):
        s.take()
    s.publish("complete", b"first")
    s.publish("idle")
    assert s.take() == (1, b"first")
    assert s.take() == (1, b"first")
    s.publish("complete", b"second")
    assert s.take() == (2, b"second")
    assert s.statuses == {"idle": 2, "complete": 2}


@pytest.mark.parametrize(
    "status", ["blank", "suspended", "stopped", "error", "invalid"]
)
def test_unavailable_event_removes_old_pixels(status):
    """无效源事件必须撤销旧像素。"""
    s = b.LatestSlot()
    s.publish("complete", b"pixels")
    s.publish(status)
    with pytest.raises(RuntimeError, match=status):
        s.take()


def test_close_fences_late_pixels_and_is_idempotent():
    """关闭后到达的complete不能重新交付。"""
    s = b.LatestSlot()
    s.publish("complete", b"pixels")
    s.close()
    s.close()
    s.publish("complete", b"late")
    assert s.sequence == 1
    with pytest.raises(RuntimeError, match="closed"):
        s.take()


def test_identity_allows_movement_but_refuses_resize_and_replacement():
    """窗口移动可接受，尺寸与身份变化失败。"""
    identity = b.Identity(10, 20, "title", 80, 60, 160, 120)
    row = {
        "kCGWindowNumber": 10,
        "kCGWindowOwnerPID": 20,
        "kCGWindowName": "title",
        "kCGWindowBounds": {"X": 100, "Y": 400, "Width": 80, "Height": 60},
    }
    identity.validate(row)
    row["kCGWindowBounds"]["Width"] = 81
    with pytest.raises(RuntimeError, match="geometry"):
        identity.validate(row)
    row["kCGWindowNumber"] = 11
    with pytest.raises(RuntimeError, match="identity"):
        identity.validate(row)


def fake_native():
    """提供不触系统的控制循环和host clock。"""
    return SimpleNamespace(
        pump=lambda seconds: None,
        host_now=lambda: 10,
        objc=SimpleNamespace(autorelease_pool=nullcontext),
    )


def test_case_reports_actual_work_duplicates_failure_and_warm_sample_window(
    monkeypatch,
):
    """失败不进入成功分位，首轮与热态分开，重复帧不冒充新帧。"""
    closed = []
    calls = []

    class Source:
        def __init__(self, *args):
            """固定可观察序列。"""
            self.index = 0

        def capture(self):
            """依次返回新帧、同帧和错误。"""
            self.index += 1
            if self.index == 3:
                raise RuntimeError("failed capture")
            return b.FrameResult(
                Image.new("RGB", (2, 2)),
                1,
                "complete" if self.index == 1 else "duplicate",
                9.99,
                9.995,
                {"capture_rgb_ms": 7 if self.index == 1 else 2},
                {},
            )

        def close(self):
            """记录是否始终释放源。"""
            closed.append(True)

    def match(*args):
        """记录成功图像被真实消费。"""
        calls.append(True)
        return {"checked": 2, "state": "主页"}

    monkeypatch.setattr(b, "CaptureSource", Source)
    monkeypatch.setattr(b, "match_frame", match)
    r = b.run_case(fake_native(), None, None, "baseline", 3, 0)
    assert (
        r["attempts"] == 3
        and r["successes"] == 2
        and r["new_frame_successes"] == 1
        and r["duplicate_reads"] == 1
    )
    assert r["summary_all"]["capture_rgb_ms"]["count"] == 2
    assert r["summary_warm"]["capture_rgb_ms"]["p95"] == 2
    assert r["first_attempt"]["timings"]["capture_rgb_ms"] == 7
    assert r["unique_sequences"] == 1 and len(calls) == 2 and closed == [True]
    assert r["errors"] == ["failed capture"]


def test_setup_failure_is_not_a_completed_attempt(monkeypatch):
    """没有首帧时保留请求数和启动错误，不伪造成功样本。"""

    class Source:
        def __init__(self, *args):
            """模拟只有idle导致首帧等待失败。"""
            raise TimeoutError("no complete frame; idle only")

    monkeypatch.setattr(b, "CaptureSource", Source)
    r = b.run_case(fake_native(), None, None, "baseline", 3, 0)
    assert r["requested_samples"] == 3 and r["attempts"] == 0 and r["successes"] == 0
    assert (
        r["summary_warm"]["capture_rgb_ms"]["count"] == 0 and r["first_attempt"] is None
    )
    assert "idle only" in r["errors"][0]


def test_stop_failure_is_explicit_even_after_successful_pixels(monkeypatch):
    """停止失败不会被采集成功掩盖。"""

    class Source:
        def __init__(self, *args):
            """无需真实配置。"""

        def capture(self):
            """提供一张受控图像。"""
            return b.FrameResult(
                Image.new("RGB", (2, 2)),
                1,
                "complete",
                None,
                None,
                {"capture_rgb_ms": 1},
                {},
            )

        def close(self):
            """模拟系统未确认退流。"""
            raise TimeoutError("stop timeout")

    monkeypatch.setattr(b, "CaptureSource", Source)
    monkeypatch.setattr(b, "match_frame", lambda *args: {"checked": 1, "state": "未知"})
    r = b.run_case(fake_native(), None, None, "baseline", 1, 0)
    assert (
        r["successes"] == 1
        and r["stop_error"] == "stop timeout"
        and "stop: stop timeout" in r["errors"]
    )


def test_percentiles_do_not_invent_empty_sample_values():
    """空样本保持未知，有样本才计算分位。"""
    assert b.summarize([])["p95"] is None
    assert b.summarize([1, 2, 3, 4, 5])["p95"] == 5


def test_constructor_stop_timeout_survives_missing_source_assignment(monkeypatch):
    """启动失败再停流超时仍传出硬停止标记，防止启动下一条流。"""

    class Sink:
        @classmethod
        def alloc(cls):
            """模拟ObjC分配，不注册真实系统类。"""
            return cls()

        def init(self):
            """返回fake输出接收者。"""
            return self

    class Stream(Sink):
        def initWithFilter_configuration_delegate_(self, *args):
            """返回尚未启动的fake流。"""
            return self

        def addStreamOutput_type_sampleHandlerQueue_error_(self, *args):
            """模拟输出注册成功。"""
            return True, None

    waits = []

    def wait(start):
        """启动和回收均失败，检测构造期传播。"""
        waits.append(True)
        raise TimeoutError("start timeout" if len(waits) == 1 else "stop timeout")

    n = fake_native()
    n.configure = lambda *args: (None, None)
    n.wait = wait
    n.sc = SimpleNamespace(SCStream=Stream, SCStreamOutputTypeScreen=0)
    monkeypatch.setitem(sys.modules, "Foundation", SimpleNamespace(NSObject=object))
    monkeypatch.setattr(b, "_SINK_CLASS", Sink)
    r = b.run_case(n, None, None, "stream_5", 1, 0)
    assert waits == [True, True] and r["attempts"] == 0
    assert r["stop_error"] == "stop timeout" and r["performance_eligible"] is False
    assert r["errors"] == ["start timeout", "stop: stop timeout"]


def test_callback_errors_survive_later_success(monkeypatch):
    """恢复出图不掩盖先前回调错误，性能结论标记不合格。"""

    class Source:
        def __init__(self, *args):
            """模拟发生十次回调错误后恢复一帧。"""
            self.slot = b.LatestSlot()
            self.errors = ["callback error"] * 8
            self.error_count = 10

        def capture(self):
            """返回恢复后的受控图像。"""
            return b.FrameResult(
                Image.new("RGB", (2, 2)),
                1,
                "complete",
                None,
                float("nan"),
                {"capture_rgb_ms": 1},
                {},
            )

        def close(self):
            """关闭fake单槽。"""
            self.slot.close()

    monkeypatch.setattr(b, "StreamSource", Source)
    monkeypatch.setattr(b, "match_frame", lambda *args: {"checked": 1})
    r = b.run_case(fake_native(), None, None, "stream_5", 1, 0)
    assert r["successes"] == 1 and r["errors"] == []
    assert r["callback_error_count"] == 10 and len(r["callback_errors"]) == 8
    assert r["performance_eligible"] is False
    assert r["time_status_counts"]["display"]["invalid"] == 1
    assert r["summary_all"]["display_age_ms"]["count"] == 0
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize(
    "stamp,status",
    [(None, "missing"), (float("inf"), "invalid"), (11, "future"), (9.99, "valid")],
)
def test_age_never_converts_unknown_or_invalid_time_into_latency(stamp, status):
    """未来和无效时间只留诊断，不能污染年龄分位。"""
    age, actual = b.source_age(10, stamp)
    assert actual == status
    assert age == pytest.approx(10) if status == "valid" else age is None


@pytest.mark.parametrize(
    "scale,factor,rect,width",
    [
        (None, 2, [0, 0, 80, 60], 160),
        (1, 2, None, 160),
        (1, 2, [0, 0, 80], 160),
        (1, 2, [0, 0, 80, float("nan")], 160),
        (1, float("nan"), [0, 0, 80, 60], 160),
        (1, 2, [4, 0, 80, 60], 160),
        (0.5, 2, [0, 0, 80, 60], 160),
        (1, 2, [0, 0, 80, 60], 80),
    ],
)
def test_stream_rejects_unproven_geometry(scale, factor, rect, width):
    """未知、错位、缩放及非有限几何都不能假定原生同尺寸。"""
    identity = b.Identity(10, 20, "title", 80, 60, 160, 120)
    b.validate_stream_geometry(identity, 160, 120, 1, 2, [0, 0, 80, 60])
    with pytest.raises(RuntimeError):
        b.validate_stream_geometry(identity, width, 120, scale, factor, rect)
