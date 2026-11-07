"""验证持续窗口采集的单槽、身份与停流契约，不访问真实窗口或权限。

原生工作队列另做实机smoke，这里以driver替身覆盖失败和迟到发布。
"""

from contextlib import nullcontext
from types import SimpleNamespace
import time

import pytest

from game_automation.platform.macos.adapters.window_stream import LatestWindowFrame, StreamPixels, WindowStreamSource, NativeWindowStream
from game_automation.portable.domain import Rect
from game_automation.portable.preparation.models import DesktopWindow


def pixels():
    """提供独立BGRA红色像素，检验通道及实际输出。"""
    return StreamPixels(bytes([0, 0, 255, 255])*16, 4, 4, 16)


def test_slot_only_latest_and_idle_needs_real_new_source_time():
    """系统idle可以确认未变化；无时间与重复时间不制造新证据。"""
    slot = LatestWindowFrame()
    slot.publish('idle', 1)
    with pytest.raises(RuntimeError, match='完整画面'):
        slot.take(0)
    slot.publish('complete', 2, pixels())
    first = slot.take(0)
    slot.publish('idle', None)
    slot.publish('idle', 2)
    assert slot.take(0) == first
    slot.publish('idle', 3)
    frame, proof = slot.take(0)
    assert frame is first[0]
    assert proof.sequence == 2 and proof.kind == 'idle' and proof.captured_at == 3
    slot.publish('complete', 4, pixels())
    assert slot.take(0)[1].sequence == 3


def test_invalidated_or_closed_slot_never_replays_pixels():
    """空白或停止后的迟到回调不能恢复缓存证据。"""
    slot = LatestWindowFrame()
    slot.publish('complete', 1, pixels())
    slot.invalidate('窗口暂停')
    slot.publish('idle', 2)
    with pytest.raises(RuntimeError, match='窗口暂停'):
        slot.take(0)
    slot.publish('complete', 3, pixels())
    assert slot.take(0)[1].captured_at == 3
    slot.close()
    slot.publish('complete', 4, pixels())
    with pytest.raises(RuntimeError, match='已停止'):
        slot.take(0)


@pytest.mark.parametrize('stamp', [None, float('nan'), float('inf'), -1])
def test_invalid_complete_source_time_revokes_old_pixels(stamp):
    """不能把未知系统时间替换为回调时间或零年龄。"""
    slot = LatestWindowFrame()
    slot.publish('complete', 1, pixels())
    slot.publish('complete', stamp, pixels())
    with pytest.raises(RuntimeError, match='源时间'):
        slot.take(0)


class Binding:
    """模拟固定窗口身份，允许显式注入失效。"""
    window = DesktopWindow('42:1', 'App', '页面', Rect(0, 0, 2, 2))

    def __init__(self):
        """保存窗口可用性。"""
        self.error = None

    def check(self):
        """只返回同一个窗口或明确失败。"""
        if self.error:
            raise RuntimeError(self.error)


class Driver:
    """隔离原生启动与停止，并保留实际配置。"""

    def __init__(self):
        """初始化可检查的生命周期。"""
        self.started = self.closed = False

    def start(self, binding, size, hz, slot):
        """提供一张完整帧并记录用户频率。"""
        self.started = True
        self.hz, self.slot = hz, slot
        slot.publish('complete', time.monotonic(), pixels())

    def close(self):
        """模拟停止时仍存在迟到回调。"""
        self.slot.publish('complete', time.monotonic(), pixels())
        self.closed = True


@pytest.mark.parametrize('hz', [2, 5])
def test_source_starts_lazily_at_selected_hz_and_preserves_proof(hz):
    """工作线程首次读才启动，频率不偷偷提升到15且RGB与源时间同槽。"""
    binding, driver = Binding(), Driver()
    source = WindowStreamSource(binding.window, (4, 4), hz=hz, binding=binding, driver_factory=lambda: driver)
    assert not driver.started
    try:
        with source.screenshot() as image:
            assert image.size == (4, 4) and image.getpixel((0, 0)) == (255, 0, 0)
        first = source.proof
        with source.screenshot():
            assert source.proof == first
        assert driver.hz == hz
        binding.error = '窗口尺寸已变化'
        with pytest.raises(RuntimeError, match='尺寸已变化'):
            source.screenshot()
    finally:
        source.close()
    assert driver.closed
    with pytest.raises(RuntimeError, match='已停止'):
        source.screenshot()


def test_startup_failure_is_not_silently_restarted_and_still_closes():
    """失败启动不另开并行流，保留已创建driver供统一回收。"""
    class Failing(Driver):
        def start(self, binding, size, hz, slot):
            """模拟系统部分创建成功后失败。"""
            super().start(binding, size, hz, slot)
            raise RuntimeError('启动超时')
    binding, driver = Binding(), Failing()
    source = WindowStreamSource(binding.window, (4, 4), binding=binding, driver_factory=lambda: driver)
    for _ in range(2):
        with pytest.raises(RuntimeError, match='启动超时'):
            source.screenshot()
    source.close()
    assert driver.closed


def test_native_close_waits_for_stop_and_callback_barrier():
    """系统停流未确认或队列未排空时不释放委托。"""
    native = NativeWindowStream.__new__(NativeWindowStream)
    native.closed = False
    native.objc = SimpleNamespace(autorelease_pool=nullcontext)
    native.stream = SimpleNamespace(stopCaptureWithCompletionHandler_=lambda cb: cb(None))
    native.sink = SimpleNamespace(owner=native)
    sink = native.sink
    native.queue = object()
    native.dispatch = SimpleNamespace(dispatch_async=lambda queue, cb: cb())
    native.close()
    assert native.closed and sink.owner is None and native.stream is None


def test_native_stop_failure_is_visible_and_keeps_resources_owned():
    """系统停止报错不能被当成STOPPED或提前解绑回调。"""
    native = NativeWindowStream.__new__(NativeWindowStream)
    native.closed = False
    native.objc = SimpleNamespace(autorelease_pool=nullcontext)
    native.stream = SimpleNamespace(stopCaptureWithCompletionHandler_=lambda cb: cb('停止失败'))
    native.sink = SimpleNamespace(owner=native)
    with pytest.raises(RuntimeError, match='停止失败'):
        native.close()
    assert not native.closed and native.sink.owner is native


def test_repeated_raw_system_timestamp_cannot_gain_new_proof_from_clock_jitter():
    """跨时钟换算抖动不能把同一系统事件变成第二次确认。"""
    native = NativeWindowStream.__new__(NativeWindowStream)
    native._last_display_time = 0
    native.objc = SimpleNamespace(autorelease_pool=nullcontext)
    native.sc = SimpleNamespace(SCStreamOutputTypeScreen=0, SCStreamFrameInfoStatus='status', SCStreamFrameInfoDisplayTime='time')
    native.cm = SimpleNamespace(CMSampleBufferGetSampleAttachmentsArray=lambda *args: [{'status': 0, 'time': 200}])
    values = iter([10.0001, 10.0002])
    native._source_time = lambda meta: next(values)
    native._copy_pixels = lambda *args: pixels()
    native.slot = LatestWindowFrame()
    native.receive(None, 0)
    first = native.slot.take(0)
    native.receive(None, 0)
    assert native.slot.take(0) == first


@pytest.mark.parametrize('change', ['scale', 'factor', 'rect', 'pixels'])
def test_stream_rejects_fixed_surface_that_hides_changed_content_geometry(change):
    """输出像素固定时仍拒绝内容范围和缩放变化。"""
    native = NativeWindowStream.__new__(NativeWindowStream)
    native.binding = Binding()
    native.pixel_size = (4, 4)
    native.sc = SimpleNamespace(SCStreamFrameInfoContentRect='rect', SCStreamFrameInfoContentScale='scale', SCStreamFrameInfoScaleFactor='factor')
    native.cm = SimpleNamespace(CMSampleBufferGetImageBuffer=lambda sample: object())
    native.q = SimpleNamespace(CVPixelBufferGetWidth=lambda image: 5 if change == 'pixels' else 4,
                              CVPixelBufferGetHeight=lambda image: 4)
    meta = {'rect': {'X': 0, 'Y': 0, 'Width': 2, 'Height': 2}, 'scale': 1, 'factor': 2}
    if change in ('scale', 'factor'):
        meta[change] = 1.5
    elif change == 'rect':
        meta['rect']['Width'] = 20
    with pytest.raises(RuntimeError, match='范围|比例'):
        native._copy_pixels(None, meta)
