"""验证用户可编辑 JSON 脚本文件 loader。

这些测试只关心公开行为：项目脚本目录中的 JSON 能否转换成标准 Script，
以及错误是否可读；不绑定具体解析函数的内部拆分方式。
"""

from __future__ import annotations

import json

import pytest

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.domain import (
    Click,
    ImageRef,
    ImageTarget,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    Point,
    PointRef,
    Rect,
    RegionRef,
    Repeat,
    ScreenStateIs,
    ScreenWindow,
    SearchRef,
    Wait,
    WaitUntil,
    If,
    ImageSearchSpec,
    ImageTemplate,
)


def test_load_config_script_parses_steps_and_resources(tmp_path) -> None:
    """验证 JSON 脚本可以描述常用步骤和局部资源别名。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    (script_dir / "打图.json").write_text(
        json.dumps(
            {
                "name": "打图",
                "resources": {
                    "points": {"头像": {"x": 242, "y": 92}},
                    "images": {"离开图": "离开.png"},
                    "regions": {
                        "右上弹窗": {
                            "left": 1800,
                            "top": 120,
                            "width": 700,
                            "height": 500,
                        }
                    },
                    "searches": {
                        "离开按钮": {
                            "image": "离开图",
                            "region": "右上弹窗",
                            "min_confidence": 0.8,
                        }
                    },
                },
                "steps": [
                    {"wait": 1.5},
                    {"click": {"point": "头像"}},
                    {"click": {"search": "离开按钮", "offset": {"x": 5, "y": -2}}},
                    {"repeat": {"times": 2, "steps": [{"wait": 0.25}]}},
                    {
                        "if_state": {
                            "state": "主页",
                            "min_confidence": 0.7,
                            "then": [{"click": {"search": "离开按钮"}}],
                            "else": [{"wait": 0.1}],
                        }
                    },
                    {
                        "wait_until_state": {
                            "state": "主页",
                            "min_confidence": 0.75,
                            "timeout": 3,
                            "interval": 0.5,
                        }
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    scripts = load_config_scripts(script_dir, asset_root=asset_root)

    assert len(scripts) == 1
    script = scripts[0]
    assert script.name == "打图"
    assert script.window == ScreenWindow()
    assert script.resources.points == (NamedPoint("头像", Point(242, 92)),)
    assert script.resources.images == (NamedImage("离开图", ImageTemplate(str(asset_root / "离开.png"))),)
    assert script.resources.regions == (NamedRegion("右上弹窗", Rect(1800, 120, 700, 500)),)
    assert script.resources.searches == (
        NamedImageSearch(
            "离开按钮",
            ImageSearchSpec(ImageRef("离开图"), region=RegionRef("右上弹窗"), min_confidence=0.8),
        ),
    )
    assert script.steps == (
        Wait(1.5),
        Click(PointRef("头像")),
        Click(ImageTarget(SearchRef("离开按钮"), offset=Point(5, -2))),
        Repeat(times=2, steps=(Wait(0.25),)),
        If(
            condition=ScreenStateIs("主页", min_confidence=0.7),
            then_steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
            else_steps=(Wait(0.1),),
        ),
        WaitUntil(
            condition=ScreenStateIs("主页", min_confidence=0.75),
            timeout_seconds=3,
            interval_seconds=0.5,
        ),
    )


def test_load_config_scripts_returns_empty_when_directory_missing(tmp_path) -> None:
    """验证项目脚本目录不存在时返回空集合。"""
    scripts = load_config_scripts(tmp_path / "scripts", asset_root=tmp_path / "assets")

    assert scripts == ()


def test_load_config_script_rejects_unknown_step(tmp_path) -> None:
    """验证未知步骤类型会返回带文件名的可读错误。"""
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "bad.json").write_text(
        json.dumps({"name": "bad", "steps": [{"drag": {"x": 1}}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bad.json: unsupported step type: drag"):
        load_config_scripts(script_dir, asset_root=tmp_path / "assets")
