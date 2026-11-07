"""验证长期运行的后台在查询窗口前接收新应用的系统事件。

本 module 模拟应用在标准输入等待期间启动，检查后续协议请求看到新窗口；
不启动真实应用、不请求系统权限，也不依赖内部会话字段。
"""

import io
import json
from types import SimpleNamespace

from game_automation.platform.local_desktop.entrypoints.desktop_backend import DesktopBackend, run_stdio
from game_automation.portable.domain.geometry import Rect
from game_automation.portable.preparation.models import DesktopWindow


def test_window_query_sees_application_started_after_backend_initial_query(tmp_path):
    """后启动应用的窗口应在同一后台的新查询中出现，不要求重启。"""
    visible = []
    pending = []
    window = DesktopWindow('42:1', 'LateApp', '任务窗口', Rect(10, 20, 800, 600))
    preparation = SimpleNamespace(list_windows=lambda application: tuple(visible))
    session = DesktopBackend(tmp_path, preparation=preparation)
    requests = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'preparation.windows', 'params': {'application': 'LateApp'}},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'preparation.windows', 'params': {'application': 'LateApp'}},
        {'jsonrpc': '2.0', 'id': 3, 'method': 'session.shutdown'},
    ]

    class Source(io.StringIO):
        def __init__(self, text):
            """创建请求流和读取次数。"""
            super().__init__(text)
            self.reads = 0

        def readline(self, size=-1):
            """模拟首个查询后，宿主等待下一请求期间有新应用启动。"""
            self.reads += 1
            if self.reads == 2:
                pending.append(window)
            return super().readline(size)

    def process_events():
        """模拟只有系统事件被处理后才更新的运行应用快照。"""
        visible.extend(pending)
        pending.clear()

    output = io.StringIO()
    source = Source('\n'.join(map(json.dumps, requests)) + '\n')
    assert run_stdio(session, source, output, io.StringIO(), process_events=process_events) == 0
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[0]['result']['windows'] == []
    assert replies[1]['result']['windows'][0]['title'] == '任务窗口'
    assert replies[2]['result']['stopping'] is True
