"""用ScreenCaptureKit维护指定窗口的最新画面，不解释状态或执行输入。

系统回调只复制像素并更新单槽；观察工作线程读取RGB及同槽源证明。
身份边界复用BoundWindow，源时间经CoreMedia映射到Python单调时钟。
"""

from dataclasses import dataclass
import math
import threading
import time

from PIL import Image

from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.domain.screen_state import FrameProof
from game_automation.platform.macos.adapters.window_identity import BoundWindow, WindowPresentationUnavailable


class WindowFramePending(WindowCaptureError):
    """首帧尚未到达，需要调用方按当前窗口状态决定是否可恢复。"""


@dataclass(frozen=True)
class StreamPixels:
    """只保存独立复制的BGRA字节，不持有系统surface。"""
    data: bytes
    width: int
    height: int
    stride: int


class LatestWindowFrame:
    """一个锁保护最新像素和系统证据，关闭后迟到回调无效。"""

    def __init__(self):
        """初始化空槽和独立源事件序号。"""
        self._condition = threading.Condition()
        self._pixels = self._proof = None
        self._sequence = 0
        self._last_time = -math.inf
        self._closed = False
        self._error = None
        self._terminal_error = False

    def publish(self, kind, stamp, pixels=None):
        """新complete或带新源时间的idle可确认，缓存读取不能续期。"""
        with self._condition:
            if self._closed or self._terminal_error:
                return
            if stamp is None or not math.isfinite(stamp) or stamp < 0:
                if kind == 'complete':
                    self._pixels = self._proof = None
                    self._error = WindowCaptureError('窗口流缺少有效源时间，请重新开始观察')
                    self._condition.notify_all()
                return
            if stamp <= self._last_time:
                return
            if kind == 'complete' and pixels is not None:
                self._pixels = pixels
            elif kind != 'idle' or self._pixels is None:
                return
            self._last_time = stamp
            self._sequence += 1
            self._proof = FrameProof(self._sequence, stamp, kind)
            self._error = None
            self._condition.notify_all()

    def invalidate(self, message, *, terminal=False):
        """blank、暂停、系统错误撤销像素，idle不能恢复失效槽。"""
        with self._condition:
            if not self._closed and not self._terminal_error:
                self._pixels = self._proof = None
                self._error = message if isinstance(message, WindowCaptureError) else WindowCaptureError(str(message)[:1024])
                self._terminal_error = self._terminal_error or terminal
                self._condition.notify_all()

    def take(self, timeout=2):
        """有界等首帧，原样返回同槽源证明而不制造新事件。"""
        with self._condition:
            self._condition.wait_for(lambda: self._pixels is not None or self._error or self._closed, timeout)
            if self._closed:
                raise WindowCaptureError('窗口采集已停止')
            if self._error:
                raise self._error
            if self._pixels is None:
                raise WindowFramePending('尚未收到窗口完整画面，请检查目标窗口与截图权限')
            return self._pixels, self._proof

    def close(self):
        """先关闭发布屏障，再由所有者停止系统采集。"""
        with self._condition:
            self._closed = True
            self._pixels = self._proof = None
            self._condition.notify_all()


class WindowStreamSource:
    """只在观察工作线程首次读取时启动系统流，频率跟随观察选项。"""
    capture_mode = 'window_stream'

    def __init__(self, window, pixel_size, *, hz=2, binding=None, driver_factory=None):
        """固定目标窗口，原生启动与等待不占用协议线程。"""
        if type(hz) not in (int, float) or not math.isfinite(hz) or not 1 <= hz <= 5:
            raise ValueError('窗口采集频率必须在每秒1到5次之间')
        self._binding = BoundWindow(window) if binding is None else binding
        self._size = (window.rect.width, window.rect.height)
        self._pixel_size = pixel_size
        self._hz = hz
        self._factory = NativeWindowStream if driver_factory is None else driver_factory
        self._slot = LatestWindowFrame()
        self._driver = None
        self._startup_error = None
        self._closed = False
        self.proof = None

    def _take_pixels(self):
        """核对窗口与像素槽，供轻量可用性检查和RGB读取共用。"""
        if self._closed:
            raise WindowCaptureError('窗口采集已停止')
        self._binding.check()
        if self._startup_error:
            raise WindowCaptureError(self._startup_error)
        if self._driver is None:
            try:
                self._driver = self._factory()
                self._driver.start(self._binding, self._pixel_size, self._hz, self._slot)
            except Exception as exc:
                self._startup_error = '窗口流启动失败：' + str(exc)[:1024]
                raise WindowCaptureError(self._startup_error) from exc
        try:
            pixels, proof = self._slot.take()
        except WindowFramePending:
            self._binding.check()
            raise
        if (pixels.width, pixels.height) != self._pixel_size:
            raise WindowPresentationUnavailable('窗口截图像素尺寸已变化，请恢复显示缩放或重新采集素材')
        self._binding.check()
        return pixels, proof

    def check_available(self):
        """读取同槽证明检查展示状态，不转换或复制RGB图像。"""
        _, proof = self._take_pixels()
        return proof

    def screenshot(self):
        """复制最新独立RGB并绑定真实源证据，前后核对窗口。"""
        pixels, proof = self._take_pixels()
        image = Image.frombytes('RGBA', self._pixel_size, pixels.data, 'raw', 'BGRA', pixels.stride).convert('RGB')
        try:
            self._binding.check()
        except BaseException:
            image.close()
            raise
        self.proof = proof
        return image

    def size(self):
        """保留原始逻辑尺寸供匹配器换算ROI。"""
        return self._size

    def close(self):
        """关闭槽并等待系统停流及串行回调屏障，失败向上报告。"""
        if self._closed:
            return
        self._slot.close()
        if self._driver is not None:
            self._driver.close()
        self._closed = True
        self.proof = None


_SINK_CLASS = None


class NativeWindowStream:
    """隔离PyObjC、dispatch及系统surface生命周期，支持fake driver替换。"""

    def __init__(self):
        """只在明确启动真实观察时加载macOS接口。"""
        try:
            import Quartz, ScreenCaptureKit, CoreMedia, dispatch, objc
        except ImportError as exc:
            raise WindowCaptureError('缺少macOS窗口流依赖，请安装项目的macos可选依赖') from exc
        self.q, self.sc, self.cm, self.dispatch, self.objc = Quartz, ScreenCaptureKit, CoreMedia, dispatch, objc
        self.stream = self.sink = None
        self._last_display_time = 0
        self.queue = dispatch.dispatch_queue_create(b'com.kokoirin.star.window-observation', None)
        self.closed = False

    def _wait(self, begin):
        """在工作线程有界等系统完成，回调不依赖协议主线程轮询。"""
        event, values = threading.Event(), []

        def finished(*args):
            """只传递完成结果，不向状态会话发布画面。"""
            values.extend(args)
            event.set()

        begin(finished)
        if not event.wait(3):
            raise WindowCaptureError('系统窗口采集调用超时')
        if values and values[-1] is not None:
            raise WindowCaptureError(str(values[-1]))
        return values[0] if len(values) > 1 else None

    def start(self, binding, pixel_size, hz, slot):
        """配置指定窗口的原像素流，串行回调只做字节复制。"""
        self.binding, self.pixel_size, self.slot = binding, pixel_size, slot
        sc, q, cm = self.sc, self.q, self.cm
        if not q.CGPreflightScreenCaptureAccess():
            raise WindowCaptureError('缺少屏幕截图权限，请在控制台检查授权')
        with self.objc.autorelease_pool():
            content = self._wait(lambda cb: sc.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(True, True, cb))
            pid = int(binding.window.id.split(':', 1)[0])
            matches = [w for w in content.windows() if w.windowID() == binding.number and w.owningApplication().processID() == pid]
            if len(matches) != 1:
                raise WindowCaptureError('所选窗口不可采集，请重新读取窗口')
            filt = sc.SCContentFilter.alloc().initWithDesktopIndependentWindow_(matches[0])
            config = sc.SCStreamConfiguration.alloc().init()
            if not hasattr(config, 'setIgnoreShadowsSingleWindow_'):
                raise WindowCaptureError('窗口流观察需要macOS14或更新系统')
            config.setWidth_(pixel_size[0]); config.setHeight_(pixel_size[1])
            config.setShowsCursor_(False); config.setCapturesAudio_(False)
            config.setPixelFormat_(q.kCVPixelFormatType_32BGRA)
            config.setIgnoreShadowsSingleWindow_(True); config.setColorSpaceName_(q.kCGColorSpaceSRGB)
            config.setMinimumFrameInterval_(cm.CMTimeMakeWithSeconds(1 / hz, 1_000_000)); config.setQueueDepth_(3)
            self.sink = _sink_class(self.objc).alloc().init()
            self.sink.owner = self
            self.stream = sc.SCStream.alloc().initWithFilter_configuration_delegate_(filt, config, self.sink)
            ok, error = self.stream.addStreamOutput_type_sampleHandlerQueue_error_(self.sink, sc.SCStreamOutputTypeScreen, self.queue, None)
            if not ok:
                raise WindowCaptureError(str(error))
            self._wait(lambda cb: self.stream.startCaptureWithCompletionHandler_(cb))

    def _source_time(self, meta):
        """以系统事件时刻计算年龄，再映射到Python单调时钟。"""
        stamp = meta.get(self.sc.SCStreamFrameInfoDisplayTime)
        if stamp is None or int(stamp) <= 0:
            return None
        cm = self.cm
        source = cm.CMTimeGetSeconds(cm.CMClockMakeHostTimeFromSystemUnits(int(stamp)))
        host = cm.CMTimeGetSeconds(cm.CMClockGetTime(cm.CMClockGetHostTimeClock()))
        age = host - source
        if not math.isfinite(age) or age < 0:
            return None
        return time.monotonic() - age

    def receive(self, sample, kind):
        """处理完整、未变化与失效事件，绝不以回调到达时间给缓存续期。"""
        if kind != self.sc.SCStreamOutputTypeScreen:
            return
        try:
            with self.objc.autorelease_pool():
                items = self.cm.CMSampleBufferGetSampleAttachmentsArray(sample, False)
                meta = dict(items[0]) if items else {}
                status = int(meta.get(self.sc.SCStreamFrameInfoStatus, -1))
                stamp = self._source_time(meta) if status in (0, 1) else None
                if stamp is not None:
                    raw_time = int(meta[self.sc.SCStreamFrameInfoDisplayTime])
                    # 跨时钟换算有微小抖动；原始系统时间才是事件去重依据。
                    if raw_time <= self._last_display_time:
                        return
                    self._last_display_time = raw_time
                if status == 0:
                    self.slot.publish('complete', stamp, self._copy_pixels(sample, meta))
                elif status == 1:
                    self.slot.publish('idle', stamp)
                else:
                    self.slot.invalidate(WindowPresentationUnavailable('窗口画面已暂停或不可用，正在等待新的完整画面'))
        except WindowPresentationUnavailable as exc:
            self.slot.invalidate(exc)
        except Exception as exc:
            self.slot.invalidate('窗口流采集失败：' + str(exc), terminal=True)

    def _copy_pixels(self, sample, meta):
        """核对surface的内容几何和比例，复制后立即释放系统缓冲。"""
        q, sc = self.q, self.sc
        image = self.cm.CMSampleBufferGetImageBuffer(sample)
        if image is None:
            raise WindowPresentationUnavailable('系统未返回完整窗口像素')
        w, h = q.CVPixelBufferGetWidth(image), q.CVPixelBufferGetHeight(image)
        raw = meta.get(sc.SCStreamFrameInfoContentRect)
        if hasattr(raw, 'rectValue'):
            raw = raw.rectValue()
        if hasattr(raw, 'origin'):
            rect = (raw.origin.x, raw.origin.y, raw.size.width, raw.size.height)
        elif raw is not None and all(k in raw for k in ('X', 'Y', 'Width', 'Height')):
            rect = tuple(float(raw[k]) for k in ('X', 'Y', 'Width', 'Height'))
        else:
            raise WindowCaptureError('无法核对窗口流内容范围')
        logical = self.binding.window.rect
        expected = (0, 0, logical.width, logical.height)
        scale, factor = meta.get(sc.SCStreamFrameInfoContentScale), meta.get(sc.SCStreamFrameInfoScaleFactor)
        values = (*rect, scale, factor)
        if any(v is None or not math.isfinite(v) for v in values) or any(abs(a-b) > 1 for a,b in zip(rect, expected)):
            raise WindowPresentationUnavailable('窗口流内容范围已变化，请恢复窗口尺寸')
        if abs(scale-1) > .001 or abs(factor-self.pixel_size[0]/logical.width) > .001 or abs(factor-self.pixel_size[1]/logical.height) > .001 or (w,h) != self.pixel_size:
            raise WindowPresentationUnavailable('窗口流像素比例已变化，请恢复窗口尺寸与显示缩放')
        if q.CVPixelBufferGetPixelFormatType(image) != q.kCVPixelFormatType_32BGRA:
            raise WindowCaptureError('窗口流像素格式不受支持')
        if q.CVPixelBufferLockBaseAddress(image, q.kCVPixelBufferLock_ReadOnly):
            raise WindowCaptureError('无法读取窗口流像素')
        try:
            stride = q.CVPixelBufferGetBytesPerRow(image)
            data = bytes(q.CVPixelBufferGetBaseAddress(image).as_buffer(stride*h))
        finally:
            q.CVPixelBufferUnlockBaseAddress(image, q.kCVPixelBufferLock_ReadOnly)
        return StreamPixels(data, w, h, stride)

    def close(self):
        """确认系统停止后排空串行队列，失败由宿主回收整个后台。"""
        if self.closed:
            return
        with self.objc.autorelease_pool():
            if self.stream is not None:
                self._wait(lambda cb: self.stream.stopCaptureWithCompletionHandler_(cb))
            drained = threading.Event()

            def barrier(*args):
                """回调队列屏障证明先前交付已结束。"""
                drained.set()

            self.dispatch.dispatch_async(self.queue, barrier)
            if not drained.wait(3):
                raise WindowCaptureError('窗口流回调尚未回收')
            if self.sink is not None:
                self.sink.owner = None
            self.stream = self.sink = self.queue = None
            self.closed = True


def _sink_class(objc):
    """每个进程只注册一次ObjC委托，重复启停复用类定义。"""
    global _SINK_CLASS
    if _SINK_CLASS is None:
        from Foundation import NSObject

        class StarWindowStreamSink(NSObject, protocols=[objc.protocolNamed('SCStreamOutput'), objc.protocolNamed('SCStreamDelegate')]):
            def stream_didOutputSampleBuffer_ofType_(self, stream, sample, kind):
                """已释放的委托拒绝迟到交付。"""
                owner = self.owner
                if owner is not None:
                    owner.receive(sample, kind)

            def stream_didStopWithError_(self, stream, error):
                """系统失败立即使单槽失效，不能保留旧画面。"""
                owner = self.owner
                if owner is not None:
                    owner.slot.invalidate('窗口流已停止：' + str(error), terminal=True)

        _SINK_CLASS = StarWindowStreamSink
    return _SINK_CLASS
