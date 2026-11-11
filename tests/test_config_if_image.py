"""验证JSON图片条件分支到既有领域、runner和模拟入口的公开行为。"""
import json

import pytest

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain import If, ImageExists, ImageMatch, ImageRef, Point, Rect, SearchRef, Wait


def load_branch(tmp_path, payload):
    """加载包含通用图片搜索与两个点位的文件脚本。"""
    scripts = tmp_path / 'scripts'
    assets = tmp_path / 'assets'
    scripts.mkdir()
    assets.mkdir()
    data = {'name':'branch', 'resources':{
        'points':{'primary':{'x':1,'y':2}, 'secondary':{'x':3,'y':4}},
        'images':{'marker':'marker.png'},
        'searches':{'marker-search':{'image':'marker','region':{'left':10,'top':20,'width':30,'height':40},'min_confidence':0.8}},
    }, 'steps':[{'if_image':payload}]}
    (scripts / 'branch.json').write_text(json.dumps(data))
    return load_config_scripts(scripts, asset_root=assets)[0]


def branches():
    """提供可观察的两个分支动作。"""
    return {'then':[{'click':{'point':'primary'}}], 'else':[{'click':{'point':'secondary'}}]}


def test_if_image_maps_search_and_nested_image_conditions(tmp_path):
    """搜索别名、内联ROI、阈值和嵌套都映射为既有If/ImageExists。"""
    script = load_branch(tmp_path, {'search':'marker-search', 'min_confidence':0.93,
        'then':[{'if_image':{'image':'marker','region':{'left':1,'top':2,'width':3,'height':4},'min_confidence':0.7,'then':[{'wait':0}]}}],
        'else':[{'wait':1}]})
    outer = script.steps[0]
    assert isinstance(outer, If)
    assert outer.condition == ImageExists(SearchRef('marker-search'), min_confidence=0.93)
    assert outer.else_steps == (Wait(1),)
    inner = outer.then_steps[0]
    assert inner.condition == ImageExists(ImageRef('marker'), region=Rect(1,2,3,4), min_confidence=0.7)
    assert inner.then_steps == (Wait(0),)
    assert inner.else_steps == ()


@pytest.mark.parametrize('payload', [None, [], {'image':'marker'}, {'image':'marker','then':[]},
    {'image':'marker','then':[{'wait':0}],'else':[]}, {'image':'marker','min_confidence':0,'then':[{'wait':0}]}])
def test_invalid_if_image_payload_is_rejected(tmp_path, payload):
    """对象、非空分支和阈值校验遵守既有JSON步骤约束。"""
    with pytest.raises(ValueError):
        load_branch(tmp_path, payload)


@pytest.mark.parametrize('found,point', [(True, Point(1,2)), (False, Point(3,4))])
def test_if_image_then_else_execute_with_fake_ports(tmp_path, found, point):
    """真实入口只执行本次图像条件选择的分支，不触碰设备。"""
    script = load_branch(tmp_path, {'search':'marker-search','min_confidence':0.93, **branches()})
    calls, clicks = [], []
    class Locator:
        def locate(self, template, **kwargs):
            """记录解析后的区域和阈值，并返回固定图像结果。"""
            calls.append((template.path, kwargs['region'], kwargs['min_confidence']))
            return ImageMatch(Rect(10,20,3,4), 0.95) if found else None
    class Device:
        def click(self, target):
            """保存选中的实际动作。"""
            clicks.append(target)
    result = run_script(script, dry_run=False, real_device_factory=Device, real_image_locator_factory=Locator)
    assert result.finish_reason == 'completed'
    assert clicks == [point]
    assert calls == [(str(tmp_path/'assets'/'marker.png'), Rect(10,20,30,40), 0.93)]


@pytest.mark.parametrize('found,point', [(True, Point(1,2)), (False, Point(3,4))])
def test_if_image_then_else_work_in_dry_run(tmp_path, capsys, found, point):
    """模拟入口按固定图片集选择分支，不申请真实端口。"""
    script = load_branch(tmp_path, {'image':'marker', **branches()})
    images = (str(tmp_path/'assets'/'marker.png'),) if found else ()
    def forbidden():
        """模拟模式不得初始化真实设备。"""
        raise AssertionError('real port initialized')
    result = run_script(script, dry_run=True, dry_run_images=images, real_device_factory=forbidden, real_image_locator_factory=forbidden)
    assert result.finish_reason == 'completed'
    assert capsys.readouterr().out == f'click {point}\n'


@pytest.mark.parametrize('payload', [
    {'image':'missing','then':[{'click':{'point':'primary'}}]},
    {'image':'marker','then':[{'click':{'point':'primary'}}],'else':[{'click':{'image':'missing'}}]},
    {'search':'missing-search','then':[{'wait':0}]},
])
def test_if_image_missing_resources_fail_before_runner_side_effects(tmp_path, payload):
    """条件和未选中分支的坏资源都沿现有运行前校验失败。"""
    script = load_branch(tmp_path, payload)
    calls = []
    result = run_script(script, dry_run=False, real_device_factory=lambda: calls.append('device'), real_image_locator_factory=lambda: calls.append('image'))
    assert result.finish_reason == 'configuration_failed'
    assert result.exit_code == 2
    assert 'missing' in result.error_message
    assert calls == []


def test_if_image_is_visible_in_control_details(tmp_path):
    """新JSON入口沿用现有图片依赖和分支摘要，无需特殊UI解释。"""
    from game_automation.portable.application.local_control import LocalControlApplication
    from game_automation.portable.scripts_manager.catalog import ScriptCatalog
    script = load_branch(tmp_path, {'image':'marker', **branches()})
    (tmp_path/'assets'/'marker.png').write_bytes(b'file presence for details')
    details = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path).describe_script('branch')
    assert details.exit_code == 0
    assert details.steps[0].startswith('If ImageExists(')
    assert any('then' in line and 'primary' in line for line in details.steps)
    assert any('else' in line and 'secondary' in line for line in details.steps)
    assert any('marker' in dependency for dependency in details.image_dependencies)


def test_if_image_details_work_through_workspace_cli(tmp_path, capsys):
    """真实CLI从工作区JSON加载并展示同一个通用分支摘要。"""
    from game_automation.platform.local_desktop.entrypoints.cli import main
    load_branch(tmp_path, {'image':'marker', **branches()})
    (tmp_path/'assets'/'marker.png').write_bytes(b'file presence for details')
    assert main(['--workspace', str(tmp_path), 'details', 'branch']) == 0
    output = capsys.readouterr().out
    assert 'If ImageExists(' in output
    assert 'primary' in output and 'secondary' in output
