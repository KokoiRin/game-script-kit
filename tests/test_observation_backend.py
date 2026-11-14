"""验证素材登记到实时观察的协议闭环。

本 module 使用准备端口与探测器替身，覆盖正常启动、互斥、停止和错误输入，
不操作真实桌面或用户工作区。
"""

import pytest

from game_automation.platform.desktop.adapters.preparation import WorkspaceTemplateStore
from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
    DesktopBackend,
)
from game_automation.portable.preparation.service import PreparationService
from tests.test_preparation import PreparationBackend
from tests.test_state_observation import Probe, wait_until


@pytest.fixture
def backend(tmp_path):
    """装配公开准备与观察端口，禁止隐式加载脚本服务。"""
    prep = PreparationBackend()
    probe = Probe()
    session = DesktopBackend(
        tmp_path,
        preparation=PreparationService(
            windows=prep,
            capture=prep,
            images=prep,
            templates=WorkspaceTemplateStore(tmp_path),
        ),
        observation_factory=lambda window, rules: probe,
    )
    try:
        yield session, probe
    finally:
        session.close()


def register(session):
    """通过公开协议创建一份状态素材。"""
    frame = session.dispatch(
        "preparation.capture", {"application": "Game", "window_id": "42:1"}
    )
    session.dispatch(
        "observation.rule.save",
        {
            "frame_id": frame["id"],
            "region": {"left": 10, "top": 20, "width": 20, "height": 20},
            "name": "入口",
            "state": "页面",
        },
    )


def test_material_to_observation_protocol_and_mutual_exclusion(backend):
    """登记后可观察并停止；观察期间拒绝改素材和执行脚本。"""
    session, probe = backend
    register(session)
    assert session.dispatch("observation.rules", {})["rules"][0]["state"] == "页面"
    session.dispatch(
        "observation.start",
        {"application": "Game", "window_id": "42:1", "hz": 5, "confirmations": 1},
    )
    wait_until(
        lambda: session.dispatch("observation.status", {})["current_state"] == "页面"
    )
    metrics = session.dispatch("observation.status", {})["performance"]
    assert metrics["material_count"] == 1
    assert metrics["last_failure_message"] == ""
    assert metrics["last_failure_at"] is None
    assert metrics["attempts"] >= 1
    assert metrics["screenshot_ms"] is None
    assert metrics["recognition_ms"] is None
    assert metrics["sample_count"] <= 120
    assert metrics["p95_ms"] >= 0
    for method in ("preparation.capture", "script.start", "observation.rule.save"):
        with pytest.raises(RuntimeError, match="停止实时识别"):
            session.dispatch(method, {})
    stopped = session.dispatch("observation.stop", {})
    assert stopped["current_state"] == "未知"
    assert stopped["phase"] in ("stopping", "stopped")
    wait_until(lambda: not session.dispatch("observation.status", {})["running"])
    assert probe.closed.is_set()


@pytest.mark.parametrize("hz", [False, 0, 6, "2", float("nan")])
def test_backend_rejects_bad_frequency_before_loading_resources(backend, hz):
    """坏频率在创建探测器之前报错，不触发真实截图。"""
    session, _ = backend
    with pytest.raises(ValueError, match="频率"):
        session.dispatch(
            "observation.start", {"application": "Game", "window_id": "42:1", "hz": hz}
        )


def test_backend_close_releases_observation_resources(backend):
    """退出时取消观察并关闭探测器，不遗留采样循环。"""
    session, probe = backend
    register(session)
    session.dispatch("observation.start", {"application": "Game", "window_id": "42:1"})
    assert session.close()
    assert probe.closed.is_set()


def test_protocol_keeps_last_failure_after_live_error_recovers(backend):
    """性能协议保留最近采样失败，不把恢复后的历史混入实时错误。"""
    from tests.test_state_observation import result

    session, probe = backend
    register(session)
    probe.value = RuntimeError("临时截图错误")
    session.dispatch(
        "observation.start",
        {"application": "Game", "window_id": "42:1", "hz": 5, "confirmations": 1},
    )
    wait_until(
        lambda: (
            session.dispatch("observation.status", {})["performance"]["failures"] >= 1
        )
    )
    failure = session.dispatch("observation.status", {})["performance"]
    assert failure["last_failure_message"] == "临时截图错误"
    assert isinstance(failure["last_failure_at"], float)
    probe.value = result()
    wait_until(
        lambda: session.dispatch("observation.status", {})["current_state"] == "页面"
    )
    recovered = session.dispatch("observation.status", {})
    assert recovered["error"] == ""
    assert recovered["performance"]["last_failure_message"] == "临时截图错误"
    assert recovered["performance"]["last_failure_at"] == failure["last_failure_at"]
