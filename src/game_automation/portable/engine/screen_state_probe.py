"""通过图像定位端口执行一轮界面状态探测。

本 module 负责把多个界面候选逐个交给 ScreenImageLocator，并汇总为领域结果；
它不读取 assets 目录、不创建真实 adapter，也不处理 HTTP 或 UI 会话。
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from game_automation.portable.domain import (
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)
from game_automation.portable.engine.ports import RunLogger, ScreenImageLocator


def probe_screen_state(
    candidates: tuple[ScreenStateCandidate, ...],
    *,
    image_locator: ScreenImageLocator | None,
    min_confidence: float = 0.8,
    logger: RunLogger | None = None,
    clock: Callable[[], float] = perf_counter,
) -> ScreenStateProbeResult:
    """逐个匹配界面候选图片并返回一轮探测结果。"""
    if image_locator is None:
        raise RuntimeError("image locator is required for screen state probe")
    total_started_at = clock()
    results: list[ScreenStateCandidateResult] = []
    for candidate in candidates:
        candidate_started_at = clock()
        match = image_locator.locate(
            candidate.template,
            min_confidence=min_confidence,
            logger=logger,
        )
        results.append(
            ScreenStateCandidateResult(
                candidate=candidate,
                match=match,
                elapsed_ms=(clock() - candidate_started_at) * 1000,
            )
        )
    return ScreenStateProbeResult(
        candidates=tuple(results),
        elapsed_ms=(clock() - total_started_at) * 1000,
    )
