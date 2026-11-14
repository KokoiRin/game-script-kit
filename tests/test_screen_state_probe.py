"""验证界面状态探测的领域规则和 application 用例。

这些测试从公开模型和 application seam 观察行为；它们不绑定 UI、HTTP 或真实截图
实现，也不直接测试 OpenCV adapter。
"""

import json

from game_automation.portable.application.screen_state_config import (
    load_screen_state_target_catalog,
)
from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ImageMatch,
    ImageSearchRequest,
    ImageSearchSpec,
    ImageTemplate,
    Rect,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
    SearchRef,
)
from game_automation.portable.engine.screen_state_probe import probe_screen_state


def test_screen_state_probe_result_uses_found_candidate_as_current_state() -> None:
    """验证单个候选命中时当前状态为该候选名称。"""
    result = ScreenStateProbeResult(
        candidates=(
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "装备",
                    ImageTemplate("assets/equipment.png"),
                    search_name="装备标题",
                ),
                match=ImageMatch(Rect(10, 20, 30, 40), confidence=0.88),
                elapsed_ms=12.5,
            ),
        ),
        elapsed_ms=12.5,
    )

    assert result.current_state == "装备"
    assert result.candidates[0].candidate.search_name == "装备标题"
    assert result.known is True


def test_screen_state_probe_result_is_unknown_when_no_candidate_matches() -> None:
    """验证所有候选都未命中时当前状态为未知。"""
    result = ScreenStateProbeResult(
        candidates=(
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "人物", ImageTemplate("assets/character.png")
                ),
                match=None,
                elapsed_ms=8.0,
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "装备", ImageTemplate("assets/equipment.png")
                ),
                match=None,
                elapsed_ms=9.0,
            ),
        ),
        elapsed_ms=17.0,
    )

    assert result.current_state == "未知"
    assert result.known is False


def test_screen_state_probe_result_hints_when_all_best_confidences_are_zero() -> None:
    """验证候选最佳置信度全为零时提示排查截图能力。"""
    result = ScreenStateProbeResult(
        candidates=(
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "主页", ImageTemplate("assets/home.png")
                ),
                match=None,
                elapsed_ms=4.0,
                best_confidence=0.0,
                best_rect=Rect(10, 20, 30, 40),
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "人物", ImageTemplate("assets/character.png")
                ),
                match=None,
                elapsed_ms=5.0,
                best_confidence=0.0,
                best_rect=Rect(50, 60, 30, 40),
            ),
        ),
        elapsed_ms=9.0,
    )

    assert len(result.hints) == 1
    assert "屏幕录制权限" in result.hints[0]
    assert "前台窗口" in result.hints[0]
    assert "桌面会话" in result.hints[0]


def test_screen_state_probe_result_does_not_hint_for_low_nonzero_confidence() -> None:
    """验证普通低置信度未命中不会提示截图能力不可用。"""
    result = ScreenStateProbeResult(
        candidates=(
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "主页", ImageTemplate("assets/home.png")
                ),
                match=None,
                elapsed_ms=4.0,
                best_confidence=0.12,
                best_rect=Rect(10, 20, 30, 40),
            ),
        ),
        elapsed_ms=4.0,
    )

    assert result.hints == ()


def test_screen_state_probe_result_chooses_highest_confidence_match() -> None:
    """验证多个候选命中时选择置信度最高的候选作为当前状态。"""
    result = ScreenStateProbeResult(
        candidates=(
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "人物", ImageTemplate("assets/character.png")
                ),
                match=ImageMatch(Rect(0, 0, 10, 10), confidence=0.71),
                elapsed_ms=7.0,
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate(
                    "装备", ImageTemplate("assets/equipment.png")
                ),
                match=ImageMatch(Rect(10, 10, 10, 10), confidence=0.93),
                elapsed_ms=9.0,
            ),
        ),
        elapsed_ms=16.0,
    )

    assert result.current_state == "装备"


def test_screen_state_config_loads_shared_target_catalog(tmp_path) -> None:
    """验证状态配置可转换成脚本可复用的共享资源目录。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "window-states.json").write_text(
        json.dumps(
            {
                "regions": {
                    "右上弹窗": {"left": 100, "top": 20, "width": 300, "height": 120},
                },
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [
                            {
                                "name": "离开按钮",
                                "image": "离开.png",
                                "region": "右上弹窗",
                                "min_confidence": 0.75,
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    catalog = load_screen_state_target_catalog(
        assets / "window-states.json",
        asset_root=assets,
        supported_suffixes=frozenset({".png"}),
    )

    assert catalog is not None
    search = catalog.resolve_search(SearchRef("离开按钮"))
    assert search.image == ImageTemplate(str(assets / "离开.png"))
    assert search.region == Rect(100, 20, 300, 120)
    assert search.min_confidence == 0.75


def test_probe_screen_state_prefers_batch_locator_and_preserves_candidate_order() -> (
    None
):
    """验证界面探测优先使用批量定位并按候选顺序映射结果。"""
    candidates = (
        ScreenStateCandidate(
            "人物",
            ImageSearchSpec(
                ImageTemplate("assets/character.png"),
                region=Rect(10, 20, 300, 120),
                min_confidence=0.85,
            ),
        ),
        ScreenStateCandidate("装备", ImageTemplate("assets/equipment.png")),
    )

    class FailingSingleLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """batch 可用时不应回退到单图定位。"""
            raise AssertionError("single image locator should not be called")

    class FakeBatchLocator:
        def __init__(self) -> None:
            """初始化 fake batch 请求记录。"""
            self.requests = []

        def locate_requests(
            self,
            requests,
            *,
            logger=None,
            stop_on_first_match=False,
        ):
            """记录批量搜索请求并返回同序结果。"""
            self.requests.append((requests, stop_on_first_match))
            return (
                (
                    ImageBatchMatchResult(
                        requests[0].template,
                        ImageMatch(Rect(1, 2, 3, 4), confidence=0.9),
                        elapsed_ms=3.0,
                    ),
                    ImageBatchMatchResult.skipped_result(requests[1].template),
                )
                if stop_on_first_match
                else (
                    ImageBatchMatchResult(requests[0].template, None, elapsed_ms=3.0),
                    ImageBatchMatchResult(
                        requests[1].template,
                        ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                        elapsed_ms=4.0,
                    ),
                )
            )

    batch_locator = FakeBatchLocator()

    result = probe_screen_state(
        candidates,
        image_locator=FailingSingleLocator(),
        batch_image_locator=batch_locator,
        min_confidence=0.8,
    )

    assert result.current_state == "人物"
    assert [candidate.candidate.name for candidate in result.candidates] == [
        "人物",
        "装备",
    ]
    assert [candidate.skipped for candidate in result.candidates] == [False, True]
    first_request = batch_locator.requests[0][0][0]
    assert first_request == ImageSearchRequest(
        ImageTemplate("assets/character.png"),
        region=Rect(10, 20, 300, 120),
        min_confidence=0.85,
    )
    assert batch_locator.requests == [
        (
            (
                ImageSearchRequest(
                    ImageTemplate("assets/character.png"),
                    region=Rect(10, 20, 300, 120),
                    min_confidence=0.85,
                ),
                ImageSearchRequest(
                    ImageTemplate("assets/equipment.png"), min_confidence=0.8
                ),
            ),
            True,
        )
    ]


def test_probe_screen_state_preserves_batch_best_diagnostics_for_missed_candidate() -> (
    None
):
    """验证批量界面探测会保留未命中候选的最佳诊断信息。"""
    candidates = (ScreenStateCandidate("人物", ImageTemplate("assets/character.png")),)

    class FailingSingleLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """batch 可用时不应回退到单图定位。"""
            raise AssertionError("single image locator should not be called")

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """返回低于阈值但带最佳置信度的批量结果。"""
            return (
                ImageBatchMatchResult(
                    requests[0].template,
                    None,
                    elapsed_ms=3.0,
                    best_confidence=0.62,
                    best_rect=Rect(10, 20, 30, 40),
                ),
            )

    result = probe_screen_state(
        candidates,
        image_locator=FailingSingleLocator(),
        batch_image_locator=FakeBatchLocator(),
        min_confidence=0.8,
    )

    assert result.current_state == "未知"
    assert result.candidates[0].found is False
    assert result.candidates[0].confidence is None
    assert result.candidates[0].best_confidence == 0.62
    assert result.candidates[0].best_rect == Rect(10, 20, 30, 40)
