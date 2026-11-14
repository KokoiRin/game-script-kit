"""编译真实 Swift 会话并验证后台生命周期。

本 module 通过临时管道后台验证原生调用方可见状态和进程退出屏障，
不创建 GUI、不连接真实桌面，也不替代 Python 执行用例测试。
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="requires macOS Swift SDK"
)


FAKE_BACKEND = '''"""提供隔离的原生协议后台，仅记录请求并模拟运行，不访问桌面。"""
import json
import os
from pathlib import Path
import signal
import sys
import time

root = Path(sys.argv[sys.argv.index('--workspace') + 1])
log = root / 'requests.jsonl'
running = False
name = ''
stale_status = None
stale_stop = None

def record(event, **fields):
    """记录后台实际收到的请求与进程事件。"""
    with log.open('a') as stream:
        stream.write(json.dumps(dict(event=event, pid=os.getpid(), **fields)) + '\\n')

def respond(request, result):
    """返回一条协议结果。"""
    print(json.dumps(dict(jsonrpc='2.0', id=request['id'], result=result)), flush=True)

previous_pid = None
if log.exists():
    for line in log.read_text().splitlines():
        event = json.loads(line)
        if event['event'] == 'started':
            previous_pid = event['pid']
overlap = False
if previous_pid is not None:
    try:
        os.kill(previous_pid, 0)
        overlap = True
    except ProcessLookupError:
        pass
record('started', overlap=overlap)
for line in sys.stdin:
    request = json.loads(line)
    method = request['method']
    record(method)
    if method == 'session.info':
        result = dict(protocol=1, process_group=0)
    elif method == 'permissions.status':
        result = dict(accessibility=True, screen_recording=True)
    elif method == 'script.start':
        name = request['params']['name']
        running = True
        if name == 'forced':
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        result = dict(running=True, finish_reason='running')
        if stale_status is not None and name == 'stuck':
            respond(request, result)
            respond(stale_status, dict(running=False, finish_reason='completed', stdout='stale-run'))
            stale_status = None
            continue
    elif method == 'script.status':
        if name in ('race', 'terminal-race'):
            stale_status = request
            continue
        if name in ('natural', 'timed-out', 'cleanup-error'):
            running = False
        reason = {'timed-out': 'timed_out', 'cleanup-error': 'cleanup_failed'}.get(name, 'running' if running else 'completed')
        result = dict(running=running, finish_reason=reason)
    elif method == 'script.stop':
        if name == 'blocked-stop':
            stale_stop = request
            continue
        if name in ('confirmed', 'race', 'terminal-race'):
            running = False
        result = dict(running=running, finish_reason='running' if running else 'cancelled')
        if name == 'terminal-race':
            respond(request, result)
            respond(stale_status, dict(running=True, finish_reason='running', stdout='stale-run'))
            stale_status = None
            continue
    elif method == 'session.shutdown':
        if name == 'forced':
            time.sleep(60)
        if stale_stop is not None:
            respond(stale_stop, dict(running=False, finish_reason='cancelled', stdout='late-stop'))
        time.sleep(0.4)
        record('exiting')
        break
    else:
        result = {}
    respond(request, result)
'''

SWIFT_HARNESS = """import AppKit
import Foundation

struct CheckFailure: Error {
    let message: String
}

@MainActor
func check(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw CheckFailure(message: message) }
}

@MainActor
func waitFor(_ predicate: () -> Bool, timeout: TimeInterval = 5) {
    let until = Date().addingTimeInterval(timeout)
    while !predicate(), Date() < until {
        RunLoop.current.run(until: Date().addingTimeInterval(0.01))
    }
}

func events(_ root: URL) -> [[String: Any]] {
    guard let text = try? String(contentsOf: root.appendingPathComponent("requests.jsonl")) else { return [] }
    return text.split(separator: "\\n").compactMap {
        try? JSONSerialization.jsonObject(with: Data($0.utf8)) as? [String: Any]
    }
}

func count(_ root: URL, _ event: String) -> Int {
    events(root).filter { $0["event"] as? String == event }.count
}

@MainActor
func exercise() throws {
    let root = URL(fileURLWithPath: CommandLine.arguments[1])
    let python = URL(fileURLWithPath: CommandLine.arguments[2])
    let scenario = CommandLine.arguments[3]
    let session = DesktopSession()
    try check(session.canSwitchWorkspace, "workspace can be chosen before startup")
    session.start(workspace: root, python: python, sourceRoot: root)
    defer {
        var stopped = false
        session.stop { stopped = true }
        waitFor({ stopped }, timeout: 12)
    }
    waitFor({ session.phase == .ready && session.permissionsKnown })
    try check(session.phase == .ready && session.canOperate, "backend becomes ready")
    try check(session.canSwitchWorkspace && session.canRestartBackend, "idle backend permits management")
    session.selectedScript = scenario
    session.startScript()
    waitFor({ session.runRunning })
    try check(session.runPhase == .running, "script starts")
    try check(!session.canOperate && !session.canSwitchWorkspace && !session.canRestartBackend,
              "actual running script retains resource ownership")
    if scenario == "natural" || scenario == "timed-out" || scenario == "cleanup-error" {
        waitFor({ !session.runRunning })
        try check(session.runPhase == .finished && session.canOperate, "normal completion releases execution")
        let expected = scenario == "timed-out" ? "超时" : scenario == "cleanup-error" ? "回收失败" : "完成"
        try check(session.status.contains(expected), "execution outcome has a visible localized status")
        return
    }
    if scenario == "race" || scenario == "terminal-race" {
        waitFor({ count(root, "script.status") == 1 })
        try check(count(root, "script.status") == 1, "a prior status request is in flight")
    }
    session.stopScript()
    session.stopScript()
    try check(session.runPhase == .stopping && !session.canStopScript, "stop intent is immediate and idempotent")
    if scenario == "confirmed" || scenario == "race" || scenario == "terminal-race" {
        waitFor({ !session.runRunning })
        try check(session.runPhase == .finished && session.canOperate, "confirmed stop releases execution")
        try check(session.status == "已取消", "confirmed stop keeps terminal result")
        try check(!session.runLog.contains("stale-run"), "an older running reply cannot replace completion")
        if scenario == "race" {
            session.selectedScript = "stuck"
            session.startScript()
            waitFor({ session.runRunning })
            waitFor({ false }, timeout: 0.8)
            try check(session.runPhase == .running && !session.runLog.contains("stale-run"),
                      "old run responses cannot finish a new run")
        }
        try check(count(root, "script.stop") == 1, "repeated stop sends one command")
        return
    }
    waitFor({ false }, timeout: scenario == "stuck" ? 4 : 0.8)
    try check(session.runRunning && session.runPhase == .stopping, "unconfirmed stop retains actual occupancy")
    try check(session.status.contains("等待"), "polling preserves stop intent")
    try check(!session.canOperate && !session.canSwitchWorkspace && session.canRestartBackend,
              "stopping permits explicit recovery while retaining workspace")
    try check(count(root, "script.stop") == 1, "repeated stop sends one command")
    if scenario == "quit-restart" {
        session.restartBackend()
        var completed = false
        var runningAtCompletion = true
        session.stop {
            runningAtCompletion = session.processRunning
            completed = true
        }
        waitFor({ completed }, timeout: 12)
        try check(completed && !runningAtCompletion && !session.processRunning,
                  "exit supersedes queued restart and completes without a child")
        try check(count(root, "started") == 1, "exit cancels the pending restart")
        return
    }
    session.restartBackend()
    session.restartBackend()
    session.start(workspace: root, python: python, sourceRoot: root)
    try check(session.phase == .stopping && session.runRunning, "restart waits for actual old process exit")
    try check(!session.canRestartBackend && !session.canSwitchWorkspace, "backend shutdown owns management")
    waitFor({ false }, timeout: 0.15)
    try check(session.phase == .stopping && session.runRunning && count(root, "started") == 1,
              "late old replies cannot clear the exit barrier")
    waitFor({ session.phase == .ready && session.permissionsKnown }, timeout: 12)
    try check(session.phase == .ready && session.runPhase == .idle && session.canOperate,
              "explicit restart creates a fresh idle backend")
    try check(count(root, "started") == 2 && count(root, "script.start") == 1,
              "restart is single and never replays tasks")
    try check(events(root).allSatisfy { ($0["overlap"] as? Bool) != true }, "new process starts after old process exits")
    if scenario == "forced" {
        try check(session.diagnostics.contains("终止信号") && session.diagnostics.contains("强制回收"),
                  "unresponsive shutdown uses the existing TERM and KILL supervision")
    }
}

MainActor.assumeIsolated {
    do { try exercise() }
    catch {
        FileHandle.standardError.write(Data("\\(error)\\n".utf8))
        exit(1)
    }
}
"""


@pytest.fixture(scope="module")
def lifecycle_binary(tmp_path_factory):
    """将真实会话和无窗口入口编译为可运行验证程序。"""
    folder = tmp_path_factory.mktemp("native-lifecycle-build")
    source = (
        Path(__file__).resolve().parents[1] / "native/StarDesktop/Sources/StarDesktop"
    )
    harness = folder / "main.swift"
    harness.write_text(SWIFT_HARNESS)
    binary = folder / "lifecycle"
    result = subprocess.run(
        [
            "swiftc",
            "-module-cache-path",
            str(folder / "cache"),
            str(source / "CanvasGeometry.swift"),
            str(source / "Session.swift"),
            str(harness),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return binary


@pytest.mark.parametrize(
    "scenario",
    [
        "natural",
        "timed-out",
        "cleanup-error",
        "confirmed",
        "stuck",
        "blocked-stop",
        "race",
        "terminal-race",
        "forced",
        "quit-restart",
    ],
)
def test_native_session_lifecycle(lifecycle_binary, tmp_path, scenario):
    """通过会话公开入口验证运行、停止、代次隔离和实际进程退出。"""
    backend = (
        tmp_path
        / "src/game_automation/platform/local_desktop/entrypoints/desktop_backend.py"
    )
    backend.parent.mkdir(parents=True)
    backend.write_text(FAKE_BACKEND)
    for package in backend.parents:
        if package == tmp_path / "src":
            break
        (package / "__init__.py").touch()
    result = subprocess.run(
        [str(lifecycle_binary), str(tmp_path), sys.executable, scenario],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
