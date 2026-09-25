"""验证点击后的连续键盘输入；通过设备和识图端口观察延迟边界。

本文件不操作真实桌面，通过 JSON loader 和 runner 验证连续动作和取消。
"""
import json

import pytest

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.domain import ImageMatch, Rect
from game_automation.portable.engine.runner import ScriptCancelledError, ScriptRunner


@pytest.mark.parametrize('cancel_after_click', [False, True])
def test_click_paste_enter_has_no_intermediate_screen_reads(tmp_path, cancel_after_click):
    """点击、粘贴、回车之间不再截图，但用户停止仍能阻止后续按键。"""
    class World:
        """将屏幕读取和输入汇总为外部可观察的事件。"""
        def __init__(self):
            """初始化事件序列。"""
            self.events = []

        def locate(self, template, **kwargs):
            """模拟输入框可见、离开按钮不可见。"""
            self.events.append('screen')
            return None if template.path.endswith('left.png') else ImageMatch(Rect(0, 0, 2, 2), 1)

        def click(self, point):
            """记录点击。"""
            self.events.append('click')

        def hotkey(self, keys):
            """记录粘贴或发送按键。"""
            self.events.append('+'.join(keys))

        def is_cancelled(self):
            """模拟用户在点击后按下停止。"""
            return cancel_after_click and 'click' in self.events

    (tmp_path / 'test.json').write_text(json.dumps({
        'name': 'test', 'resources': {'images': {'input': 'input.png', 'left': 'left.png'}},
        'steps': [{'repeat': {'times': 1, 'break_if_image': {'image': 'left'}, 'steps': [
            {'click': {'image': 'input', 'then_hotkeys': [['command', 'v'], ['enter']]}}
        ]}}],
    }))
    script = load_config_scripts(tmp_path, asset_root=tmp_path)[0]
    world = World()
    runner = ScriptRunner(world, image_locator=world, cancellation_token=world)
    if cancel_after_click:
        with pytest.raises(ScriptCancelledError):
            runner.run(script)
        assert world.events[-1] == 'click'
    else:
        assert runner.run(script).finish_reason == 'completed'
        start = world.events.index('click')
        assert world.events[start:start + 3] == ['click', 'command+v', 'enter']


@pytest.mark.parametrize('hotkeys', ['enter', ['enter'], [[]], [['unknown-key']]])
def test_invalid_click_hotkeys_fail_during_loading(tmp_path, hotkeys):
    """不合法的连续按键配置必须在实际点击之前被拒绝。"""
    (tmp_path / 'test.json').write_text(json.dumps({
        'name': 'test', 'resources': {'images': {'input': 'input.png'}},
        'steps': [{'click': {'image': 'input', 'then_hotkeys': hotkeys}}],
    }))
    with pytest.raises(ValueError):
        load_config_scripts(tmp_path, asset_root=tmp_path)
