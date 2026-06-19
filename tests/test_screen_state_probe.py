"""验证界面状态探测的领域规则和 application 用例。

这些测试从公开模型和 application seam 观察行为；它们不绑定 UI、HTTP 或真实截图
实现，也不直接测试 OpenCV adapter。
"""

import time

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.domain import (
    ImageMatch,
    ImageBatchMatchResult,
    ImageTemplate,
    Rect,
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
                candidate=ScreenStateCandidate("装备", ImageTemplate("assets/equipment.png")),
                match=ImageMatch(Rect(10, 20, 30, 40), confidence=0.88),
                elapsed_ms=12.5,
            ),
        ),
        elapsed_ms=12.5,
    )

    assert result.current_state == "装备"
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
        def locate_many(
            self,
            templates,
            *,
            region=None,
            min_confidence=1.0,
            logger=None,
            stop_on_first_match=False,
        ):
            """记录批量请求并返回装备命中。"""
            batch_requests.append((templates, min_confidence, stop_on_first_match))
            return (
                ImageBatchMatchResult(templates[0], None, elapsed_ms=3.0),
                ImageBatchMatchResult(
                    templates[1],
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
    assert batch_requests[0][2] is True


def test_probe_screen_state_prefers_batch_locator_and_preserves_candidate_order() -> None:
    """验证界面探测优先使用批量定位并按候选顺序映射结果。"""
    candidates = (
        ScreenStateCandidate("人物", ImageTemplate("assets/character.png")),
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

        def locate_many(
            self,
            templates,
            *,
            region=None,
            min_confidence=1.0,
            logger=None,
            stop_on_first_match=False,
        ):
            """记录批量模板请求并返回同序结果。"""
            self.requests.append((templates, min_confidence, stop_on_first_match))
            return (
                ImageBatchMatchResult(
                    templates[0],
                    ImageMatch(Rect(1, 2, 3, 4), confidence=0.9),
                    elapsed_ms=3.0,
                ),
                ImageBatchMatchResult.skipped_result(templates[1]),
            ) if stop_on_first_match else (
                ImageBatchMatchResult(templates[0], None, elapsed_ms=3.0),
                ImageBatchMatchResult(
                    templates[1],
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
    assert batch_locator.requests == [
        ((ImageTemplate("assets/character.png"), ImageTemplate("assets/equipment.png")), 0.8, True)
    ]


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
