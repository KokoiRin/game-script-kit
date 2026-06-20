"""验证界面状态探测的领域规则和 application 用例。

这些测试从公开模型和 application seam 观察行为；它们不绑定 UI、HTTP 或真实截图
实现，也不直接测试 OpenCV adapter。
"""

import json
import time

import pytest

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.screen_state_config import load_screen_state_target_catalog
from game_automation.portable.domain import (
    ImageMatch,
    ImageBatchMatchResult,
    ImageSearchRequest,
    ImageSearchSpec,
    ImageTemplate,
    Rect,
    SearchRef,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
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
                candidate=ScreenStateCandidate("人物", ImageTemplate("assets/character.png")),
                match=None,
                elapsed_ms=8.0,
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate("装备", ImageTemplate("assets/equipment.png")),
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
                candidate=ScreenStateCandidate("主页", ImageTemplate("assets/home.png")),
                match=None,
                elapsed_ms=4.0,
                best_confidence=0.0,
                best_rect=Rect(10, 20, 30, 40),
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate("人物", ImageTemplate("assets/character.png")),
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
                candidate=ScreenStateCandidate("主页", ImageTemplate("assets/home.png")),
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
                candidate=ScreenStateCandidate("人物", ImageTemplate("assets/character.png")),
                match=ImageMatch(Rect(0, 0, 10, 10), confidence=0.71),
                elapsed_ms=7.0,
            ),
            ScreenStateCandidateResult(
                candidate=ScreenStateCandidate("装备", ImageTemplate("assets/equipment.png")),
                match=ImageMatch(Rect(10, 10, 10, 10), confidence=0.93),
                elapsed_ms=9.0,
            ),
        ),
        elapsed_ms=16.0,
    )

    assert result.current_state == "装备"


def test_local_control_probes_screen_state_from_image_assets(tmp_path) -> None:
    """验证 UI application 可从 assets 生成候选并探测当前界面。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "人物.png").write_bytes(b"fake")
    (assets / "装备.webp").write_bytes(b"fake")
    requested_templates = []

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """按模板文件名返回固定匹配结果。"""
            requested_templates.append((template.path, min_confidence))
            if template.path.endswith("装备.webp"):
                return ImageMatch(Rect(10, 20, 30, 40), confidence=0.91)
            return None

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_locator_factory=FakeImageLocator,
    )

    result = app.probe_screen_state_once(min_confidence=0.8)

    assert result.current_state == "装备"
    assert [candidate.candidate.name for candidate in result.candidates] == ["人物", "装备"]
    assert requested_templates == [
        (str(assets / "人物.png"), 0.8),
        (str(assets / "装备.webp"), 0.8),
    ]


def test_local_control_screen_state_probe_uses_batch_locator_when_configured(tmp_path) -> None:
    """验证 UI application 装配 batch locator 后一轮探测只走批量定位。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "人物.png").write_bytes(b"fake")
    (assets / "装备.webp").write_bytes(b"fake")
    batch_requests = []

    class FailingSingleLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """batch 已装配时 application 不应调用单图定位。"""
            raise AssertionError("single image locator should not be called")

    class FakeBatchLocator:
        def locate_requests(
            self,
            requests,
            *,
            logger=None,
            stop_on_first_match=False,
        ):
            """记录批量请求并返回装备命中。"""
            batch_requests.append((requests, stop_on_first_match))
            return (
                ImageBatchMatchResult(requests[0].template, None, elapsed_ms=3.0),
                ImageBatchMatchResult(
                    requests[1].template,
                    ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                    elapsed_ms=4.0,
                ),
            )

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_locator_factory=FailingSingleLocator,
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    result = app.probe_screen_state_once(min_confidence=0.8)

    assert result.current_state == "装备"
    assert len(batch_requests) == 1
    assert batch_requests[0][1] is True
    assert [request.min_confidence for request in batch_requests[0][0]] == [0.8, 0.8]


def test_local_control_probes_screen_state_from_configured_groups(tmp_path) -> None:
    """验证 application 可从状态组配置生成带区域的搜索请求。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "重来.png").write_bytes(b"fake")
    (assets / "主页.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "regions": {
                    "右上弹窗": {"left": 100, "top": 20, "width": 300, "height": 120},
                    "主页标题": {"left": 0, "top": 0, "width": 200, "height": 80},
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
                            {
                                "name": "重来按钮",
                                "image": "重来.png",
                                "region": "右上弹窗",
                                "min_confidence": 0.8,
                            },
                        ],
                    },
                    {
                        "state": "主页",
                        "searches": [
                            {"name": "主页标题", "image": "主页.png", "region": "主页标题"}
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    captured_requests = []

    class FailingSingleLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """batch 已装配时不应调用单图定位。"""
            raise AssertionError("single image locator should not be called")

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """记录状态组配置生成的搜索请求，并让第二个搜索项命中。"""
            captured_requests.append((requests, stop_on_first_match))
            return (
                ImageBatchMatchResult(requests[0].template, None, elapsed_ms=3.0),
                ImageBatchMatchResult(
                    requests[1].template,
                    ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                    elapsed_ms=4.0,
                ),
                ImageBatchMatchResult.skipped_result(requests[2].template),
            )

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_locator_factory=FailingSingleLocator,
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    result = app.probe_screen_state_once(min_confidence=0.8)

    assert result.current_state == "战斗失败"
    assert [candidate.candidate.name for candidate in result.candidates] == [
        "战斗失败",
        "战斗失败",
        "主页",
    ]
    assert [candidate.candidate.search_name for candidate in result.candidates] == [
        "离开按钮",
        "重来按钮",
        "主页标题",
    ]
    requests, stop_on_first_match = captured_requests[0]
    assert stop_on_first_match is True
    assert [request.region for request in requests] == [
        Rect(100, 20, 300, 120),
        Rect(100, 20, 300, 120),
        Rect(0, 0, 200, 80),
    ]
    assert [request.min_confidence for request in requests] == [0.75, 0.8, 0.8]


def test_screen_state_config_loads_shared_target_catalog(tmp_path) -> None:
    """验证状态配置可转换成脚本可复用的共享资源目录。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
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
        assets / "screen-states.json",
        asset_root=assets,
        supported_suffixes=frozenset({".png"}),
    )

    assert catalog is not None
    search = catalog.resolve_search(SearchRef("离开按钮"))
    assert search.image == ImageTemplate(str(assets / "离开.png"))
    assert search.region == Rect(100, 20, 300, 120)
    assert search.min_confidence == 0.75


def test_local_control_rejects_invalid_screen_state_config(tmp_path) -> None:
    """验证状态组配置中的非法图片路径会被拒绝。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "坏配置",
                        "searches": [{"name": "逃逸图片", "image": "../outside.png"}],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    app = LocalControlApplication(project_root=tmp_path)

    with pytest.raises(ValueError, match="screen state search image must stay inside assets folder"):
        app.probe_screen_state_once(min_confidence=0.8)


@pytest.mark.parametrize(
    ("config", "error_type", "message"),
    [
        ({"groups": []}, ValueError, "screen state config groups must be a non-empty list"),
        (
            {"groups": [{"state": "空场景", "searches": []}]},
            ValueError,
            "screen state group searches must be non-empty: 空场景",
        ),
        (
            {
                "groups": [
                    {
                        "state": "未知区域",
                        "searches": [
                            {"name": "按钮", "image": "按钮.png", "region": "不存在区域"}
                        ],
                    }
                ]
            },
            LookupError,
            "unknown region target: 不存在区域",
        ),
    ],
)
def test_local_control_rejects_malformed_screen_state_config(
    tmp_path,
    config,
    error_type,
    message,
) -> None:
    """验证状态组配置中的空组、空搜索和未知区域会被拒绝。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "按钮.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(config, ensure_ascii=False),
        encoding="utf-8",
    )
    app = LocalControlApplication(project_root=tmp_path)

    with pytest.raises(error_type, match=message):
        app.probe_screen_state_once(min_confidence=0.8)


def test_probe_screen_state_prefers_batch_locator_and_preserves_candidate_order() -> None:
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
                ImageBatchMatchResult(
                    requests[0].template,
                    ImageMatch(Rect(1, 2, 3, 4), confidence=0.9),
                    elapsed_ms=3.0,
                ),
                ImageBatchMatchResult.skipped_result(requests[1].template),
            ) if stop_on_first_match else (
                ImageBatchMatchResult(requests[0].template, None, elapsed_ms=3.0),
                ImageBatchMatchResult(
                    requests[1].template,
                    ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                    elapsed_ms=4.0,
                ),
            )

    batch_locator = FakeBatchLocator()

    result = probe_screen_state(
        candidates,
        image_locator=FailingSingleLocator(),
        batch_image_locator=batch_locator,
        min_confidence=0.8,
    )

    assert result.current_state == "人物"
    assert [candidate.candidate.name for candidate in result.candidates] == ["人物", "装备"]
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
                ImageSearchRequest(ImageTemplate("assets/equipment.png"), min_confidence=0.8),
            ),
            True,
        )
    ]


def test_probe_screen_state_preserves_batch_best_diagnostics_for_missed_candidate() -> None:
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


def test_local_control_runs_background_screen_state_probe(tmp_path) -> None:
    """验证 application 可后台循环探测界面状态并追加日志。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "装备.png").write_bytes(b"fake")

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """总是返回装备界面命中。"""
            return ImageMatch(Rect(10, 20, 30, 40), confidence=0.91)

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_locator_factory=FakeImageLocator,
    )

    started = app.start_screen_state_probe(min_confidence=0.8, interval_seconds=0.01)
    assert started.running is True

    running = _wait_until_probe_output_contains(app, "current_state=装备")
    assert running.current_state == "装备"
    assert "screen state probe round" in running.stdout
    assert "candidate=装备 found=True confidence=0.91" in running.stdout

    app.stop_screen_state_probe()
    final = _wait_until_probe_finished(app)
    assert final.running is False
    assert final.exit_code == 0


def test_local_control_background_screen_state_probe_tracks_stats(tmp_path) -> None:
    """验证后台界面探测会按已完成轮次累计结构化统计。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "主页.png").write_bytes(b"fake")
    (assets / "技能.png").write_bytes(b"fake")
    call_count = 0

    class FakeBatchLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """第一轮命中主页并跳过技能，后续轮次全部未知。"""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (
                    ImageBatchMatchResult(
                        requests[0].template,
                        ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                        elapsed_ms=3.0,
                    ),
                    ImageBatchMatchResult.skipped_result(requests[1].template),
                )
            return (
                ImageBatchMatchResult(requests[0].template, None, elapsed_ms=4.0),
                ImageBatchMatchResult(requests[1].template, None, elapsed_ms=5.0),
            )

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_batch_locator_factory=FakeBatchLocator,
    )

    started = app.start_screen_state_probe(min_confidence=0.8, interval_seconds=0.01)
    assert started.running is True

    running = _wait_until_probe_stats_rounds(app, 2)
    app.stop_screen_state_probe()
    final = _wait_until_probe_finished(app)

    assert running.stats.rounds >= 2
    assert final.stats.rounds >= 2
    assert final.stats.last_elapsed_ms is not None
    assert final.stats.matched_counts == (("主页", 1),)
    assert final.stats.skipped_counts == (("技能", 1),)


def test_local_control_rejects_second_screen_state_probe_while_running(tmp_path) -> None:
    """验证已有后台探测运行时不会启动第二个探测会话。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "装备.png").write_bytes(b"fake")

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """短暂等待，让第二次启动能观察到运行中状态。"""
            time.sleep(0.02)
            return ImageMatch(Rect(10, 20, 30, 40), confidence=0.91)

    app = LocalControlApplication(
        project_root=tmp_path,
        real_image_locator_factory=FakeImageLocator,
    )

    app.start_screen_state_probe(min_confidence=0.8, interval_seconds=0.01)
    duplicate = app.start_screen_state_probe(min_confidence=0.8, interval_seconds=0.01)
    app.stop_screen_state_probe()

    final = _wait_until_probe_finished(app)
    assert duplicate.running is True
    assert "screen state probe is already running" in duplicate.stderr
    assert final.exit_code == 0


def _wait_until_probe_output_contains(app: LocalControlApplication, text: str):
    """轮询等待后台界面探测产生指定输出。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_screen_state_probe()
        if text in status.stdout:
            return status
        time.sleep(0.01)
    raise AssertionError(f"screen state probe output did not contain {text!r}")


def _wait_until_probe_finished(app: LocalControlApplication):
    """轮询等待后台界面探测结束，避免测试绑定线程调度。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_screen_state_probe()
        if not status.running:
            return status
        time.sleep(0.01)
    raise AssertionError("screen state probe did not finish")


def _wait_until_probe_stats_rounds(app: LocalControlApplication, rounds: int):
    """轮询等待后台界面探测统计达到指定轮数。"""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = app.current_screen_state_probe()
        if status.stats.rounds >= rounds:
            return status
        time.sleep(0.01)
    raise AssertionError(f"screen state probe stats did not reach {rounds} rounds")
