"""验证 JSON 循环在图片出现时跳过剩余动作，不连接桌面。

通过 loader 和 runner 的公开行为验证中断；fake 设备和屏幕表达外部状态。
"""
import json
from pathlib import Path

import pytest

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.domain import ImageMatch, Rect
from game_automation.portable.engine.runner import ScriptRunner


@pytest.mark.parametrize('leave_at', ['waiting', 'focus', 'paste', 'never', 'locating'])
def test_break_image_skips_remaining_actions_and_continues_outer_loop(tmp_path, leave_at):
    """等待、定位、聚焦和粘贴期间离开均跳过剩余发送，外层继续下一轮。"""
    class World:
        """模拟每轮匹配后页面状态与实际输入行为。"""
        left = False
        pasted = 0
        sent = 0
        rounds = 0

        def locate(self, template, **kwargs):
            """等待中的对象可离开，定位输入目标期间也可能断开。"""
            name = Path(template.path).name
            if name == 'left.png':
                found = self.left
            else:
                if leave_at == 'locating':
                    self.left = True
                found = leave_at != 'waiting' and not self.left
            return ImageMatch(Rect(0, 0, 2, 2), 1) if found else None

        def wait(self, seconds):
            """轮询时模拟对方离开，末尾等待负责标记下一轮。"""
            if seconds == 7:
                self.rounds += 1
                self.left = False
            elif leave_at == 'waiting':
                self.left = True

        def click(self, point):
            """点击输入框后可立刻断开。"""
            assert not self.left
            if leave_at == 'focus':
                self.left = True

        def hotkey(self, keys):
            """检查断开后不会再粘贴或发送。"""
            assert not self.left
            if keys == ('command', 'v'):
                self.pasted += 1
                if leave_at == 'paste':
                    self.left = True
            else:
                self.sent += 1

    steps = ([{'wait_until_image': {'image': 'ready', 'timeout': 1, 'interval': .1}}]
             if leave_at == 'waiting' else [])
    steps += [{'click': {'image': 'ready'}}, {'hotkey': ['command', 'v']}, {'hotkey': ['enter']}]
    (tmp_path / 'test.json').write_text(json.dumps({
        'name': 'test', 'resources': {'images': {'left': 'left.png', 'ready': 'ready.png'}},
        'steps': [{'repeat': {'times': 2, 'steps': [
            {'repeat': {'times': 1, 'break_if_image': {'image': 'left'}, 'steps': steps}},
            {'wait': 7},
        ]}}],
    }))
    script = load_config_scripts(tmp_path, asset_root=tmp_path)[0]
    world = World()
    result = ScriptRunner(world, image_locator=world).run(script)
    assert result.finish_reason == 'completed'
    assert world.rounds == 2
    assert world.sent == (2 if leave_at == 'never' else 0)
    assert world.pasted == (2 if leave_at in ('paste', 'never') else 0)


def test_break_image_is_a_required_resource_even_without_image_actions(tmp_path):
    """只用在中断条件里的图片也必须出现在运行需求和依赖列表里。"""
    from game_automation.portable.engine.script_requirements import inspect_script_requirements
    from game_automation.portable.application.script_dependencies import describe_script_dependencies

    (tmp_path / 'test.json').write_text(json.dumps({
        'name': 'test', 'resources': {'images': {'left': 'missing.png'}},
        'steps': [{'repeat': {'times': 1, 'break_if_image': {'image': 'left'},
                              'steps': [{'wait': 0}]}}],
    }))
    script = load_config_scripts(tmp_path, asset_root=tmp_path)[0]
    assert inspect_script_requirements(script).needs_image_locator
    dependencies = describe_script_dependencies(script, asset_root=tmp_path,
                                                supported_image_suffixes=frozenset({".png"}),
                                                state_names=())
    assert str(tmp_path / "missing.png") in dependencies.image_dependencies
    assert dependencies.readiness
