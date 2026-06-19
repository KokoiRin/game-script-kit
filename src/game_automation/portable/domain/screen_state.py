"""定义界面状态探测的领域值对象。

本 module 只表达候选界面、候选匹配结果和一轮探测结果的不变量；它不读取
图片文件、不截图，也不决定 UI 或脚本如何消费探测结果。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.image_matching import ImageMatch, ImageTemplate

UNKNOWN_SCREEN_STATE = "未知"


@dataclass(frozen=True, slots=True)
class ScreenStateCandidate:
    name: str
    template: ImageTemplate

    def __post_init__(self) -> None:
        """校验界面状态候选名称必须非空。"""
        if not self.name.strip():
            raise ValueError("screen state candidate name cannot be empty")


@dataclass(frozen=True, slots=True)
class ScreenStateCandidateResult:
    candidate: ScreenStateCandidate
    match: ImageMatch | None
    elapsed_ms: float

    def __post_init__(self) -> None:
        """校验单个候选探测耗时必须非负。"""
        if self.elapsed_ms < 0:
            raise ValueError("screen state candidate elapsed_ms cannot be negative")

    @property
    def found(self) -> bool:
        """判断该候选界面是否在本轮探测中命中。"""
        return self.match is not None

    @property
    def confidence(self) -> float | None:
        """返回候选命中的置信度，未命中时返回 None。"""
        return None if self.match is None else self.match.confidence


@dataclass(frozen=True, slots=True)
class ScreenStateProbeResult:
    candidates: tuple[ScreenStateCandidateResult, ...]
    elapsed_ms: float

    def __post_init__(self) -> None:
        """校验一轮探测耗时必须非负。"""
        if self.elapsed_ms < 0:
            raise ValueError("screen state probe elapsed_ms cannot be negative")

    @property
    def current_state(self) -> str:
        """返回本轮探测判定的当前界面状态。"""
        selected = self.selected_candidate
        return UNKNOWN_SCREEN_STATE if selected is None else selected.candidate.name

    @property
    def known(self) -> bool:
        """判断本轮探测是否识别出了已知界面。"""
        return self.selected_candidate is not None

    @property
    def selected_candidate(self) -> ScreenStateCandidateResult | None:
        """返回置信度最高的命中候选，全部未命中时返回 None。"""
        found_candidates = tuple(candidate for candidate in self.candidates if candidate.found)
        if not found_candidates:
            return None
        return max(found_candidates, key=lambda candidate: candidate.confidence or 0)
