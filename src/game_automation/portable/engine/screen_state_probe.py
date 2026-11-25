"""通过图像定位端口执行一轮界面状态探测。

调用方提供候选序列和图像定位端口。本模块优先批量定位，仅有单图端口时逐项查找，
再将匹配和跳过的候选汇总为领域结果。截图与模板匹配由定位端口负责。
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ImageSearchRequest,
    ImageTemplate,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)
from game_automation.portable.engine.ports import (
    RunLogger,
    ScreenImageBatchLocator,
    ScreenImageLocator,
)


def probe_screen_state(
    candidates: tuple[ScreenStateCandidate, ...],
    *,
    image_locator: ScreenImageLocator | None,
    batch_image_locator: ScreenImageBatchLocator | None = None,
    min_confidence: float = 0.8,
    logger: RunLogger | None = None,
    clock: Callable[[], float] = perf_counter,
) -> ScreenStateProbeResult:
    """按传入顺序探测候选，首次命中后将剩余候选标为跳过。"""
    if batch_image_locator is None and image_locator is None:
        raise RuntimeError("image locator is required for screen state probe")
    total_started_at = clock()
    if batch_image_locator is not None:
        batch_results = batch_image_locator.locate_requests(
            tuple(
                _search_request_from_candidate(candidate, min_confidence)
                for candidate in candidates
            ),
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
            region=candidate.search.region,
            min_confidence=candidate.search.min_confidence or min_confidence,
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
            best_confidence=batch_result.best_confidence,
            best_rect=batch_result.best_rect,
        )
        for candidate, batch_result in zip(candidates, batch_results, strict=True)
    )


def _search_request_from_candidate(
    candidate: ScreenStateCandidate,
    default_min_confidence: float,
) -> ImageSearchRequest:
    """把状态候选的搜索规格转换为批量图片定位请求。"""
    if not isinstance(candidate.search.image, ImageTemplate):
        raise RuntimeError(
            "screen state candidate image must be resolved before probing"
        )
    return ImageSearchRequest(
        template=candidate.search.image,
        region=candidate.search.region,
        min_confidence=candidate.search.min_confidence or default_min_confidence,
    )
