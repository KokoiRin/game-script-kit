"""验证文件脚本的无上限循环和等待；使用 fake 时间，不执行桌面操作。

通过 loader 和 runner 观察循环次数、等待及用户取消，不依赖执行器内部结构。
"""
import json

import pytest

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.engine.runner import ScriptCancelledError, ScriptRunner


@pytest.mark.parametrize('step,limit', [
    ({'repeat': {'times': None, 'steps': [{'wait': .5}]}}, 12),
    ({'wait_until_image': {'image': 'end', 'timeout': None, 'interval': 50000}}, 3),
])
def test_unbounded_execution_continues_until_user_cancels(tmp_path, step, limit):
    """超过十轮或一天仍继续等待，用户停止后立即退出。"""
    class World:
        """提供可计数等待、始终未命中的屏幕和外部取消信号。"""
        waits = 0

        def wait(self, seconds):
            """推进模拟等待次数。"""
            self.waits += 1

        def locate(self, template, **kwargs):
            """模拟目标尚未出现。"""
            return None

        def is_cancelled(self):
            """达到指定次数时模拟用户按下停止。"""
            return self.waits >= limit

    (tmp_path / 'test.json').write_text(json.dumps({
        'name': 'test', 'resources': {'images': {'end': 'end.png'}}, 'steps': [step],
    }))
    script = load_config_scripts(tmp_path, asset_root=tmp_path)[0]
    world = World()
    with pytest.raises(ScriptCancelledError):
        ScriptRunner(world, image_locator=world, cancellation_token=world).run(script)
    assert world.waits == limit
