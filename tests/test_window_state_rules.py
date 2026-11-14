"""验证窗口状态素材的登记、坐标与失败回滚。

本 module 使用内存冻结帧与临时工作区，不接触真实窗口或业务素材。
"""

import pytest

from game_automation.portable.application.window_state_rules import (
    list_window_state_rules,
    load_window_state_rules,
    save_window_state_rule,
)
from game_automation.portable.domain import Rect
from game_automation.portable.preparation.service import PreparationService
from tests.test_preparation import PreparationBackend


@pytest.fixture
def preparation(tmp_path):
    """提供带二倍截图像素的准备服务。"""
    backend = PreparationBackend()
    from game_automation.platform.desktop.adapters.preparation import (
        WorkspaceTemplateStore,
    )

    service = PreparationService(
        windows=backend,
        capture=backend,
        images=backend,
        templates=WorkspaceTemplateStore(tmp_path),
    )
    return service, service.capture_window("Game", "42:1")


def test_rule_registration_converts_search_pixels_and_preserves_old_config(
    tmp_path, preparation
):
    """搜索框按截图比例转成窗口坐标，旧状态配置不被改写。"""
    service, frame = preparation
    (tmp_path / "assets").mkdir()
    old = tmp_path / "assets/screen-states.json"
    old.write_text("old")
    save_window_state_rule(
        tmp_path,
        service,
        frame_id=frame.id,
        crop=Rect(20, 40, 10, 10),
        name="入口",
        state="页面",
        search_region=Rect(0, 0, 80, 100),
    )
    rules = load_window_state_rules(tmp_path)
    assert (rules.pixel_width, rules.pixel_height) == (
        frame.image.width,
        frame.image.height,
    )
    assert rules.candidates[0].search.region == Rect(0, 0, 40, 50)
    assert old.read_text() == "old"
    assert list_window_state_rules(tmp_path)["rules"][0]["state"] == "页面"


def test_rule_rejects_invalid_roi_before_saving(tmp_path, preparation):
    """搜索范围未包含模板时拒绝，工作区不产生半份配置。"""
    service, frame = preparation
    with pytest.raises(ValueError, match="包含"):
        save_window_state_rule(
            tmp_path,
            service,
            frame_id=frame.id,
            crop=Rect(20, 40, 10, 10),
            name="入口",
            state="页面",
            search_region=Rect(0, 0, 5, 5),
        )
    assert not (tmp_path / "assets").exists()


def test_missing_configuration_guides_user_to_materials(tmp_path):
    """无素材时提供准备入口，不把所有 PNG 自动当成状态。"""
    assert list_window_state_rules(tmp_path) == {"rules": []}
    with pytest.raises(ValueError, match="素材准备"):
        load_window_state_rules(tmp_path)


def test_legacy_window_rules_request_recapture_without_pixel_provenance(
    tmp_path, preparation
):
    """旧窗口素材缺少像素来源时明确要求重采，不猜测比例。"""
    import json

    service, frame = preparation
    save_window_state_rule(
        tmp_path,
        service,
        frame_id=frame.id,
        crop=Rect(20, 40, 10, 10),
        name="入口",
        state="页面",
    )
    path = tmp_path / "assets/window-states.json"
    data = json.loads(path.read_text())
    del data["pixel_size"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="重新采集"):
        load_window_state_rules(tmp_path)
