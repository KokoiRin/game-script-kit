"""通过图像定位端口执行一轮界面状态探测。

本 module 负责把多个界面候选逐个交给 ScreenImageLocator，并汇总为领域结果；
它不读取 assets 目录、不创建真实 adapter，也不处理 HTTP 或 UI 会话。
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)
from game_automation.portable.engine.ports import RunLogger, ScreenImageBatchLocator, ScreenImageLocator


def probe_screen_state(
    candidates: tuple[ScreenStateCandidate, ...],
    *,
    image_locator: ScreenImageLocator | None,
    batch_image_locator: ScreenImageBatchLocator | None = None,
    min_confidence: float = 0.8,
    logger: RunLogger | None = None,
    clock: Callable[[], float] = perf_counter,
) -> ScreenStateProbeResult:
    """逐个匹配界面候选图片并返回一轮探测结果。"""
    if batch_image_locator is None and image_locator is None:
        raise RuntimeError("image locator is required for screen state probe")
    total_started_at = clock()
    if batch_image_locator is not None:
        batch_results = batch_image_locator.locate_many(
            tuple(candidate.template for candidate in candidates),
            min_confidence=min_confidence,
            logger=logger,
            stop_on_first_match=True,
        )
        return ScreenStateProbeResult(
            candidates=_screen_state_results_from_batch(candidates, batch_results),
            elapsed_ms=(clock() - total_started_at) * 1000,
        )

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
        if match is not None:
            # 当前界面候选按优先级排序；命中后剩余候选不再继续截图匹配。
            results.extend(
                ScreenStateCandidateResult(
                    candidate=remaining_candidate,
                    match=None,
                    elapsed_ms=0,
                    skipped=True,
                )
                for remaining_candidate in candidates[len(results) :]
            )
            break
    return ScreenStateProbeResult(
        candidates=tuple(results),
        elapsed_ms=(clock() - total_started_at) * 1000,
    )


def _screen_state_results_from_batch(
    candidates: tuple[ScreenStateCandidate, ...],
    batch_results: tuple[ImageBatchMatchResult, ...],
) -> tuple[ScreenStateCandidateResult, ...]:
    """把同序批量图片匹配结果转换为界面状态候选结果。"""
    if len(candidates) != len(batch_results):
        raise RuntimeError("screen state batch result count must match candidates")
    return tuple(
        ScreenStateCandidateResult(
            candidate=candidate,
            match=batch_result.match,
            elapsed_ms=batch_result.elapsed_ms,
            skipped=batch_result.skipped,
        )
        for candidate, batch_result in zip(candidates, batch_results, strict=True)
    )
