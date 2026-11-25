import AppKit
import Foundation

enum RunPhase { case idle, running, stopping, finished }

struct ExecutionState {
    var scripts: [String] = []
    var selectedScript = ""
    var useSavedPlan = false
    var savedPlanName = ""
    var planEntries: [PlanEntry] = []
    var runArtifactsPath = ""
    var scriptDetails = ""
    var runLog = ""
    var runPhase: RunPhase = .idle
    var dryRun = true
    var dryRunColor = "#000000"
    var dryRunState = "未知"

    var isRunning: Bool { runPhase == .running || runPhase == .stopping }

    mutating func resetForStart() {
        runPhase = .idle
        scripts = []
        selectedScript = ""
        scriptDetails = ""
        runLog = ""
        useSavedPlan = false
        savedPlanName = ""
        planEntries = []
        runArtifactsPath = ""
    }
}

extension DesktopSession {
    var canStopScript: Bool { phase == .ready && execution.runPhase == .running && !busy }

    var draftFingerprint: String {
        PlanDraft.fingerprint(name: execution.savedPlanName, entries: execution.planEntries)
    }

    func reloadScripts() {
        perform("script.reload") { [weak self] result in
            guard let self else { return }
            self.execution.scripts = result["scripts"] as? [String] ?? []
            if !self.execution.scripts.contains(self.execution.selectedScript) {
                self.execution.selectedScript = self.execution.scripts.first ?? ""
            }
            let plan = result["plan"] as? Object ?? [:]
            if self.savedPlanBaseline.isEmpty || self.draftFingerprint == self.savedPlanBaseline {
                let parsed = PlanDraft.parse(plan)
                self.execution.savedPlanName = parsed.name
                self.execution.planEntries = parsed.entries
                self.savedPlanBaseline = self.draftFingerprint
            }
            if let error = result["plan_error"] as? String, !error.isEmpty { self.errorMessage = error }
            let errors = result["errors"] as? [Object] ?? []
            self.execution.scriptDetails = errors.compactMap { $0["message"] as? String }.joined(separator: "\n")
            if !errors.isEmpty { self.errorMessage = self.execution.scriptDetails }
            self.describeScript()
        }
    }

    func describeScript() {
        refreshCompanionTarget()
        if execution.useSavedPlan { execution.scriptDetails = ""; return }
        guard !execution.selectedScript.isEmpty else { return }
        perform("script.details", ["name": execution.selectedScript]) { [weak self] result in
            guard self?.execution.useSavedPlan == false else { return }
            let steps = result["steps"] as? [String] ?? []
            let checks = (result["readiness"] as? [[String]] ?? []).map { $0.joined(separator: " · ") }
            self?.execution.scriptDetails = (steps + [""] + checks).joined(separator: "\n")
        }
    }

    func startScript() {
        guard canOperate, execution.dryRun || requirePermission("accessibility") else { return }
        if execution.useSavedPlan {
            guard let payload = planPayload() else { return }
            beginRun(plan: payload)
        } else {
            beginRun()
        }
    }

    func addPlanEntry() {
        guard canOperate, !execution.selectedScript.isEmpty else { return }
        execution.planEntries.append(PlanEntry(name: execution.selectedScript))
    }

    func movePlanEntry(_ id: UUID, by offset: Int) {
        guard canOperate else { return }
        PlanDraft.move(&execution.planEntries, id: id, by: offset)
    }

    func removePlanEntry(_ id: UUID) {
        guard canOperate else { return }
        execution.planEntries.removeAll { $0.id == id }
    }

    func savePlan() {
        guard let payload = planPayload() else { return }
        let fingerprint = draftFingerprint
        perform("plan.save", ["plan": payload]) { [weak self] _ in
            self?.savedPlanBaseline = fingerprint
            self?.status = "流程已保存"
        }
    }

    func planPayload() -> Object? {
        switch PlanDraft.buildPayload(name: execution.savedPlanName, entries: execution.planEntries) {
        case .success(let payload):
            return payload
        case .failure(let error):
            errorMessage = error.message
            return nil
        }
    }

    func openRunRecords() {
        guard let workspace else { return }
        let folder = execution.runArtifactsPath.isEmpty
            ? workspace.appendingPathComponent(".star/runs")
            : URL(fileURLWithPath: execution.runArtifactsPath)
        if FileManager.default.fileExists(atPath: folder.path) { NSWorkspace.shared.open(folder) }
        else { errorMessage = "当前工作区还没有保存的运行记录。" }
    }

    func beginRun(plan: Object? = nil) {
        guard canOperate else { return }
        runGeneration = UUID()
        let generation = runGeneration
        runPolling = false
        execution.runPhase = .idle
        execution.runLog = ""
        execution.runArtifactsPath = ""
        var params: Object = ["name": execution.selectedScript, "dry_run": execution.dryRun,
                              "dry_run_color": execution.dryRunColor, "dry_run_screen_state": execution.dryRunState]
        if let plan { params["plan"] = plan }
        let fingerprint = draftFingerprint
        perform(execution.useSavedPlan ? "plan.start" : "script.start", params) { [weak self] result in
            guard let self, self.runGeneration == generation, self.phase == .ready else { return }
            if plan != nil, result["finish_reason"] as? String != "configuration_failed", result["finish_reason"] as? String != "task_not_found" {
                self.savedPlanBaseline = fingerprint
            }
            self.renderRun(result)
        }
    }

    func stopScript() {
        guard canStopScript else { return }
        execution.runPhase = .stopping
        status = "已请求停止，正在等待当前操作结束。等待期间可重启后台回收进程。"
        let generation = runGeneration
        call("script.stop") { [weak self] reply in
            guard let self, self.runGeneration == generation, self.phase == .ready else { return }
            switch reply {
            case .success(let result): self.renderRun(result)
            case .failure(let error): self.errorMessage = error.localizedDescription
            }
        }
    }

    func pollRun() {
        guard phase == .ready, execution.isRunning, !runPolling else { return }
        runPolling = true
        let generation = runGeneration
        call("script.status") { [weak self] reply in
            guard let self, self.runGeneration == generation, self.phase == .ready else { return }
            self.runPolling = false
            if case .success(let result) = reply { self.renderRun(result) }
        }
    }

    func renderRun(_ result: Object) {
        let running = result["running"] as? Bool ?? false
        // 已确认结束的同次运行不能被更早发出的在途状态恢复为运行中。
        guard execution.runPhase != .finished else { return }
        if !running { execution.runPhase = .finished }
        else if execution.runPhase != .stopping { execution.runPhase = .running }
        let stdout = result["stdout"] as? String ?? "", stderr = result["stderr"] as? String ?? ""
        let text = stdout + (stderr.isEmpty ? "" : "\n提示与错误：\n" + stderr)
        if execution.runLog != text { execution.runLog = text }
        execution.runArtifactsPath = result["artifacts_path"] as? String ?? ""
        let reason = result["finish_reason"] as? String ?? "idle"
        let labels = ["completed": "脚本执行完成", "skipped": "已跳过", "cancelled": "已取消", "configuration_failed": "配置错误",
                      "setup_failed": "运行环境不可用", "failed": "运行失败", "timed_out": "任务等待超时",
                      "cleanup_failed": "运行资源回收失败", "stopped_unmet_condition": "条件未满足，已停止", "idle": "脚本未运行"]
        switch execution.runPhase {
        case .stopping: status = "已请求停止，正在等待当前操作结束。等待期间可重启后台回收进程。"
        case .running: status = "脚本运行中…"
        case .idle, .finished: status = labels[reason] ?? reason
        }
    }
}
