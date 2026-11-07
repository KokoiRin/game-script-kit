"""管理只读窗口观察的生命周期、样本时效与连续确认。

本 module 只持有一个采样线程和不可变快照，不采集平台画面或序列化协议；
平台 probe 提供领域结果，桌面入口负责把快照转换成线协议。
"""

from dataclasses import dataclass, replace
from enum import StrEnum
import math
import threading
import time
from typing import Callable, Protocol

from game_automation.portable.domain import ScreenStateProbeResult


@dataclass(frozen=True)
class ObservationSettings:
    """集中验证观察频率与确认次数。"""
    hz: float = 2
    confirmations: int = 2

    def __post_init__(self) -> None:
        """在输入边界拒绝不支持的选项。"""
        if type(self.hz) not in (int, float) or not math.isfinite(self.hz) or not 1 <= self.hz <= 5:
            raise ValueError('观察频率必须在每秒 1 到 5 次之间')
        if type(self.confirmations) is not int or not 1 <= self.confirmations <= 5:
            raise ValueError('连续确认次数必须为 1 到 5')

    @property
    def freshness_seconds(self) -> float:
        """返回首帧与后续画面共用的新鲜度预算。"""
        return max(2, 3 / self.hz)


class ObservationPhase(StrEnum):
    """规定有效状态只属于 observing 阶段。"""
    IDLE = 'idle'
    WAITING = 'waiting'
    OBSERVING = 'observing'
    STALE = 'stale'
    UNAVAILABLE = 'unavailable'
    STOPPING = 'stopping'
    STOPPED = 'stopped'


@dataclass(frozen=True)
class ObservationSample:
    """源时间衡量画面年龄，读取开始时间独立衡量处理成本。"""
    capture_started: float
    completed: float
    observed_at: float
    result: ScreenStateProbeResult
    actual_hz: float
    read_started: float | None = None


@dataclass(frozen=True)
class ObservationTransition:
    """保存历史转换，不能作为实时状态。"""
    at: float
    previous: str
    state: str


@dataclass(frozen=True)
class ObservationPerformance:
    """拥有本次观察的完成轮次计数及最近120轮整轮耗时。"""
    attempts: int = 0
    failures: int = 0
    over_budget: int = 0
    stale_results: int = 0
    material_count: int | None = None
    screenshot_ms: float | None = None
    recognition_ms: float | None = None
    round_ms: float | None = None
    rounds_ms: tuple[float, ...] = ()
    last_failure_message: str = ''
    last_failure_at: float | None = None
    duplicate_results: int = 0
    capture_mode: str | None = None
    source_age_ms: float | None = None
    source_ages_ms: tuple[float, ...] = ()
    checked_count: int | None = None
    skipped_count: int | None = None

    def record(self, elapsed_ms: float, *, budget_ms: float, failed: bool = False,
               stale: bool = False, result: ScreenStateProbeResult | None = None,
               failure_message: str = '', failure_at: float | None = None,
               duplicate: bool = False, source_age_ms: float | None = None) -> 'ObservationPerformance':
        """只在完成结果获准发布时累加，失败阶段未知则保留为空。"""
        timing = None if result is None else result.timing
        return ObservationPerformance(self.attempts + 1, self.failures + int(failed),
            self.over_budget + int(elapsed_ms > budget_ms), self.stale_results + int(stale),
            self.material_count if result is None else len(result.candidates),
            None if timing is None else timing.screenshot_ms,
            None if timing is None else timing.recognition_ms, elapsed_ms,
            (*self.rounds_ms, elapsed_ms)[-120:],
            failure_message[:1024] if failed else self.last_failure_message,
            failure_at if failed else self.last_failure_at,
            self.duplicate_results + int(duplicate),
            self.capture_mode if timing is None else timing.capture_mode,
            source_age_ms,
            self.source_ages_ms if source_age_ms is None else (*self.source_ages_ms, source_age_ms)[-120:],
            None if result is None else sum(not c.skipped for c in result.candidates),
            None if result is None else sum(c.skipped for c in result.candidates))

    def percentile(self, fraction: float) -> float | None:
        """以 nearest-rank 计算明确样本窗口内的分位数。"""
        values = sorted(self.rounds_ms)
        return None if not values else values[max(0, math.ceil(len(values) * fraction) - 1)]


@dataclass(frozen=True)
class ObservationSnapshot:
    """保存有界历史及单时点状态，并统一撤销无效阶段的状态。"""
    phase: ObservationPhase = ObservationPhase.IDLE
    settings: ObservationSettings = ObservationSettings()
    sequence: int = 0
    sample: ObservationSample | None = None
    age_ms: float | None = None
    current_state: str = '未知'
    candidate_state: str = '未知'
    error: str = ''
    history: tuple[ObservationTransition, ...] = ()
    performance: ObservationPerformance = ObservationPerformance()

    def __post_init__(self) -> None:
        """保证等待、失效和停止阶段绝不携带实时值。"""
        if self.phase != ObservationPhase.OBSERVING:
            object.__setattr__(self, 'current_state', '未知')
            object.__setattr__(self, 'candidate_state', '未知')
            object.__setattr__(self, 'sample', None)

    @property
    def running(self) -> bool:
        """从阶段派生运行槽占用，停止回收前保持占用。"""
        return self.phase not in (ObservationPhase.IDLE, ObservationPhase.STOPPED)


class StateProbe(Protocol):
    """仅向观察线程提供一帧结果与资源回收接口。"""
    def read(self) -> ScreenStateProbeResult:
        """采集一次窗口并返回这一帧的全部证据。"""
        ...

    def close(self) -> None:
        """回收本探测器拥有的临时资源。"""
        ...


class StateObservation:
    """集中拥有发布屏障、工作线程和不可变记录。"""
    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 wall_clock: Callable[[], float] = time.time) -> None:
        """创建空闲会话，允许测试注入单调时钟。"""
        self._clock = clock
        self._wall_clock = wall_clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._value = ObservationSnapshot()
        self._started = 0.0
        self._cleanup_failed = False

    def start(self, probe: StateProbe, *, settings: ObservationSettings | None = None,
              hz: float = 2, confirmations: int = 2) -> ObservationSnapshot:
        """启动唯一采样线程，不在调用线程读取画面。"""
        options = settings if settings is not None else ObservationSettings(hz, confirmations)
        with self._lock:
            if self._cleanup_failed or self._thread is not None and self._thread.is_alive():
                raise RuntimeError('state observation is already running')
            self._stop = threading.Event()
            self._started = self._clock()
            self._value = ObservationSnapshot(ObservationPhase.WAITING, options,
                performance=ObservationPerformance(material_count=getattr(probe, 'candidate_count', None)))
            self._thread = threading.Thread(target=self._run, args=(probe, options, self._stop), daemon=True)
            self._thread.start()
        return self.snapshot()

    def snapshot(self) -> ObservationSnapshot:
        """不等待平台调用，按采集时间投影首帧超时与画面过期。"""
        with self._lock:
            value = self._value
            anchor = value.sample.capture_started if value.sample else self._started
            age = max(0.0, self._clock() - anchor)
            if value.phase in (ObservationPhase.WAITING, ObservationPhase.OBSERVING) and age > value.settings.freshness_seconds:
                return replace(value, phase=ObservationPhase.STALE, age_ms=age * 1000,
                               error='画面已过期，正在等待新的采集结果')
            return replace(value, age_ms=age * 1000 if value.running else None)

    def request_stop(self) -> ObservationSnapshot:
        """立即撤销实时状态，关闭资源由工作线程完成。"""
        with self._lock:
            self._stop.set()
            phase = ObservationPhase.STOPPING if self._cleanup_failed or self._thread and self._thread.is_alive() else ObservationPhase.STOPPED
            self._value = replace(self._value, phase=phase)
        return self.snapshot()

    def stop(self, timeout: float = 3) -> bool:
        """供后台关闭时有界等待，交互停止使用非阻塞请求。"""
        self.request_stop()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return not self._cleanup_failed and (thread is None or not thread.is_alive())

    def _run(self, probe: StateProbe, options: ObservationSettings, stop: threading.Event) -> None:
        """逐轮采集，失败、慢帧和长间隔均重置确认。"""
        previous, consecutive, last_started = None, 0, None
        last_proof = None
        try:
            while not stop.is_set():
                started = self._clock()
                observed_at = self._wall_clock()
                if last_started is not None and started - last_started > options.freshness_seconds:
                    previous, consecutive = None, 0
                try:
                    result = probe.read()
                    completed = self._clock()
                    source_started = started if result.proof is None else result.proof.captured_at
                    if source_started > completed:
                        raise ValueError('采集源时间无效，请重新开始观察')
                    duplicate = result.proof is not None and last_proof == result.proof.sequence
                    if result.proof is not None:
                        if last_proof is not None and result.proof.sequence < last_proof:
                            raise ValueError('采集源序号倒退，请重新开始观察')
                        last_proof = result.proof.sequence
                    if completed - source_started > options.freshness_seconds:
                        previous, consecutive = None, 0
                        outcome = None
                    else:
                        candidate = result.current_state
                        if not duplicate:
                            consecutive = consecutive + 1 if candidate == previous else 1
                            previous = candidate
                        outcome = ObservationSample(source_started, completed,
                            observed_at - (started - source_started), result,
                            0.0 if last_started is None else 1 / max(0.000001, started - last_started), started)
                    with self._lock:
                        if stop.is_set():
                            break
                        old = self._value
                        stable = result.current_state if outcome and consecutive >= options.confirmations else '未知'
                        history = old.history
                        if stable != old.current_state:
                            history = (ObservationTransition(self._wall_clock(), old.current_state, stable), *history)[:64]
                        self._value = ObservationSnapshot(
                            ObservationPhase.OBSERVING if outcome else ObservationPhase.STALE,
                            options, old.sequence + 1, outcome, (completed - source_started) * 1000,
                            stable, result.current_state, '' if outcome else '画面采集耗时过长，结果已过期', history,
                            old.performance.record((completed - started) * 1000, budget_ms=1000 / options.hz,
                                                   stale=outcome is None, result=result, duplicate=duplicate,
                                                   source_age_ms=None if result.proof is None else (completed-source_started)*1000))
                except Exception as exc:
                    previous, consecutive = None, 0
                    with self._lock:
                        if stop.is_set():
                            break
                        self._value = replace(self._value, phase=ObservationPhase.UNAVAILABLE, error=str(exc)[:2048],
                            performance=self._value.performance.record((self._clock() - started) * 1000,
                                budget_ms=1000 / options.hz, failed=True,
                                failure_message=str(exc), failure_at=self._wall_clock()))
                last_started = started
                stop.wait(max(0.0, 1 / options.hz - (self._clock() - started)))
        finally:
            try:
                probe.close()
            except Exception as exc:
                with self._lock:
                    self._cleanup_failed = True
                    self._value = replace(self._value, phase=ObservationPhase.STOPPING,
                        error='采集资源未能回收，请重启后台：' + str(exc)[:1024])
            else:
                with self._lock:
                    self._value = replace(self._value, phase=ObservationPhase.STOPPED)
