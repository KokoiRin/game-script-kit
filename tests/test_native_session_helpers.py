"""验证从原生会话拆出的纯格式化、编排草稿与诊断日志模块。

本 module 只编译 Foundation 纯模块，不启动 Python 子进程或 GUI；
非 macOS 环境跳过本机 Swift SDK 验证。
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS Swift SDK")
def test_plan_draft_observation_formatter_and_diagnostics_log(tmp_path):
    """验证编排草稿校验与排序、观察文案格式化及日志落盘截断。"""
    source = (
        Path(__file__).resolve().parents[1] / "native/StarDesktop/Sources/StarDesktop"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = tmp_path / "main.swift"
    harness.write_text(f"""import Foundation

// 1. PlanDraft：解析、排序、指纹与校验
let parsed = PlanDraft.parse(["name": "日常", "items": [["name": "任务A", "wait_after_seconds": 60], ["name": "任务B"]]])
precondition(parsed.name == "日常")
precondition(parsed.entries.map(\\.name) == ["任务A", "任务B"])
precondition(parsed.entries[0].waitSeconds == "60" && parsed.entries[1].waitSeconds == "0")

var entries = parsed.entries
let secondID = entries[1].id
PlanDraft.move(&entries, id: secondID, by: -1)
precondition(entries.map(\\.name) == ["任务B", "任务A"])
PlanDraft.move(&entries, id: secondID, by: -1)
precondition(entries.map(\\.name) == ["任务B", "任务A"])

let fp1 = PlanDraft.fingerprint(name: "日常", entries: entries)
entries[0].waitSeconds = "15"
let fp2 = PlanDraft.fingerprint(name: "日常", entries: entries)
precondition(fp1 != fp2)

if case .failure(let err) = PlanDraft.buildPayload(name: "   ", entries: entries) {{
    precondition(err.message.contains("流程名称"))
}} else {{ preconditionFailure("empty name must fail") }}

entries[0].waitSeconds = "-1"
if case .failure(let err) = PlanDraft.buildPayload(name: "日常", entries: entries) {{
    precondition(err.message.contains("任务B"))
}} else {{ preconditionFailure("negative wait must fail") }}

entries[0].waitSeconds = "15"
if case .success(let payload) = PlanDraft.buildPayload(name: "日常", entries: entries) {{
    let items = payload["items"] as? [[String: Any]] ?? []
    precondition(items.count == 2 && (items[0]["wait_after_seconds"] as? Double) == 15)
}} else {{ preconditionFailure("valid draft must succeed") }}

// 2. ObservationFormatter：规则、阶段、证据与性能文案
precondition(ObservationFormatter.rulesSummary(["rules": []]).contains("还没有状态素材"))
let rulesText = ObservationFormatter.rulesSummary([
    "rules": [["state": "主页", "priority": 10, "method": "points", "point_count": 8, "offset_radius": 1, "image": "home.png"]]
])
precondition(rulesText.contains("主页") && rulesText.contains("多点 · 8 点") && rulesText.contains("±1"))
precondition(ObservationFormatter.phaseLabel("observing") == "正在观察")
precondition(ObservationFormatter.evidence(["evidence": []]) == "暂无有效画面证据")
let perf = ObservationFormatter.performance(["material_count": 3, "checked_count": 2, "skipped_count": 1, "round_ms": 12.5, "p95_ms": 16.0, "capture_mode": "window_stream"])
precondition(perf.summary.contains("素材 3") && perf.summary.contains("16.0 ms"))
precondition(perf.details.contains("窗口流取帧"))

// 3. DiagnosticsLog：内存截断与工作区 desktop.log 写入
var buffer = ""
let workspaceURL = URL(fileURLWithPath: "{workspace}")
DiagnosticsLog.append("hello\\n", to: &buffer, workspace: workspaceURL)
precondition(buffer.contains("hello"))
let logFile = workspaceURL.appendingPathComponent(".star/desktop.log")
let disk = try String(contentsOf: logFile, encoding: .utf8)
precondition(disk.contains("hello"))
""")
    binary = tmp_path / "helpers"
    subprocess.run(
        [
            "swiftc",
            "-module-cache-path",
            str(tmp_path / "cache"),
            str(source / "Backend/DiagnosticsLog.swift"),
            str(source / "Observation/ObservationFormatter.swift"),
            str(source / "Execution/PlanDraft.swift"),
            str(harness),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(binary)], check=True)
