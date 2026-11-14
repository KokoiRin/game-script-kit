import AppKit
import Combine
import Foundation
import Darwin

struct WindowChoice: Identifiable {
    let id: String
    let title: String
}


struct FrozenFrame {
    let id: String
    let title: String
    let width: Int
    let height: Int
    let image: NSImage
}

struct DesktopError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

@MainActor
final class DesktopSession: ObservableObject {
    enum Phase { case idle, starting, ready, stopping, failed }
    enum RunPhase { case idle, running, stopping, finished }
    typealias Object = [String: Any]
    typealias Reply = (Result<Object, Error>) -> Void

    @Published var phase: Phase = .idle
    @Published var busy = false
    @Published var status = "请选择任务工作区。"
    @Published var errorMessage = ""
    @Published var diagnostics = ""
    @Published var permissionsKnown = false
    @Published var accessibilityAllowed = false
    @Published var screenRecordingAllowed = false
    @Published var checkingPermissions = false
    @Published var workspace: URL?
    @Published var application = ""
    @Published var windows: [WindowChoice] = []
    @Published var selectedWindow = ""
    @Published var frame: FrozenFrame?
    @Published var selection: PixelRegion?
    @Published var targetName = ""
    @Published var resourceText = ""
    @Published var scripts: [String] = []
    @Published var selectedScript = ""
    @Published var scriptDetails = ""
    @Published var runLog = ""
    @Published private(set) var runPhase: RunPhase = .idle
    @Published var observationRunning = false
    @Published var observationHz = 2
    @Published var confirmObservation = true
    @Published var observationState = "未知"
    @Published var observationCandidate = "未知"
    @Published var observationPhase = "未启动"
    @Published var observationMetrics = "暂无检测结果"
    @Published var observationPerformanceSummary = "性能：尚无采样"
    @Published var observationPerformanceDetails = "统计随每轮采样更新，轮询不重复计数。"
    @Published var observationEvidence = "暂无匹配证据"
    @Published var observationHistory = "暂无状态变化"
    @Published var observationError = ""
    @Published var observationRuleSummary = "尚未读取状态素材"
    @Published var stateName = ""
    @Published var stateConfidence = "0.90"
    @Published var searchRegion: PixelRegion?
    @Published var dryRun = true
    @Published var dryRunColor = "#000000"
    @Published var dryRunState = "未知"
    var runRunning: Bool { runPhase == .running || runPhase == .stopping }
    var canOperate: Bool { phase == .ready && !busy && !runRunning && !observationRunning }
    var canSwitchWorkspace: Bool {
        !busy && !runRunning && !observationRunning && phase != .starting && phase != .stopping
    }
    var canRestartBackend: Bool {
        !busy && runPhase != .running && !observationRunning && phase != .starting && phase != .stopping &&
            workspace != nil && python != nil && sourceRoot != nil
    }
    var canStopScript: Bool { phase == .ready && runPhase == .running && !busy }
    var canStopObservation: Bool { phase == .ready && observationRunning && !observationStopping }
    var canCheckPermissions: Bool { canOperate && !checkingPermissions }
    var showsProgress: Bool { busy || phase == .starting || phase == .stopping || runPhase == .stopping }
    var processRunning: Bool { process?.isRunning ?? false }

    private var process: Process?
    private var input: FileHandle?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?
    private var buffer = Data()
    private var requestID = 0
    private var pending: [Int: Reply] = [:]
    private var deadlines: [Int: DispatchWorkItem] = [:]
    private var pollTimer: Timer?
    private var polling = false
    private var runGeneration = UUID()
    private var observationPolling = false
    private var observationTimer: Timer?
    private var stopCompletions: [() -> Void] = []
    private var pendingRestart: UUID?
    private var python: URL?
    private var sourceRoot: URL?
    private var ownsProcessGroup = false
    private var frameGeneration = UUID()
    private var observationGeneration = UUID()
    private var observationGrace: DispatchWorkItem?
    private var observationDeadline: TimeInterval?
    private var observationStopping = false

    func start(workspace: URL, python: URL, sourceRoot: URL) {
        guard process == nil else { return }
        self.workspace = workspace
        self.python = python
        self.sourceRoot = sourceRoot
        phase = .starting
        runGeneration = UUID()
        runPhase = .idle
        polling = false
        ownsProcessGroup = false
        observationGeneration = UUID()
        observationGrace?.cancel(); observationGrace = nil
        observationDeadline = nil; observationStopping = false
        observationPerformanceSummary = "性能：尚无采样"
        observationPerformanceDetails = "统计随每轮采样更新，轮询不重复计数。"
        observationMetrics = "暂无检测结果"; observationRuleSummary = "尚未读取状态素材"
        observationRunning = false
        observationPhase = "未启动"; observationState = "未知"; observationCandidate = "未知"
        observationEvidence = "暂无匹配证据"; observationHistory = "暂无状态变化"; observationError = ""
        observationPolling = false
        permissionsKnown = false
        checkingPermissions = false
        errorMessage = ""
        status = "正在启动本地后台…"
        scripts = []; selectedScript = ""; scriptDetails = ""; runLog = ""
        windows = []; selectedWindow = ""; clearFrame()
        buffer.removeAll(keepingCapacity: false)
        let child = Process(), stdinPipe = Pipe(), stdoutPipe = Pipe(), stderrPipe = Pipe()
        child.executableURL = python
        child.arguments = ["-u", "-m", "game_automation.platform.local_desktop.entrypoints.desktop_backend", "--workspace", workspace.path]
        child.currentDirectoryURL = sourceRoot
        var environment = ProcessInfo.processInfo.environment
        let source = sourceRoot.appendingPathComponent("src").path
        environment["PYTHONPATH"] = source + (environment["PYTHONPATH"].map { ":" + $0 } ?? "")
        child.environment = environment
        child.standardInput = stdinPipe; child.standardOutput = stdoutPipe; child.standardError = stderrPipe
        input = stdinPipe.fileHandleForWriting
        outputPipe = stdoutPipe; errorPipe = stderrPipe
        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self, weak child] handle in
            // 只读取当前可用字节，固定长度读取会让短响应等待后续数据或 EOF。
            let data = handle.availableData
            guard !data.isEmpty else { return }
            Task { @MainActor in
                guard let self, let child, self.process === child else { return }
                self.consume(data)
            }
        }
        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self, weak child] handle in
            // 只读取当前可用字节，固定长度读取会让短响应等待后续数据或 EOF。
            let data = handle.availableData
            guard !data.isEmpty else { return }
            Task { @MainActor in
                guard let self, let child, self.process === child else { return }
                self.record(String(decoding: data, as: UTF8.self))
            }
        }
        child.terminationHandler = { [weak self] child in
            Task { @MainActor in self?.didExit(child) }
        }
        process = child
        do {
            try child.run()
            record("后台已启动，PID \(child.processIdentifier)\n")
            call("session.info") { [weak self] reply in
                guard let self, self.process === child, self.phase == .starting else { return }
                switch reply {
                case .success(let info):
                    guard info["protocol"] as? Int == 1 else {
                        self.failProtocol("后台协议版本不兼容。")
                        return
                    }
                    self.ownsProcessGroup = (info["process_group"] as? Int) == Int(child.processIdentifier)
                    self.phase = .ready
                    self.status = "就绪。素材准备和脚本运行使用同一受管理的后台。"
                    self.refreshPermissions()
                    self.pollTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                        Task { @MainActor in self?.pollRun() }
                    }
                case .failure(let error): self.failProtocol(error.localizedDescription)
                }
            }
        } catch {
            phase = .failed
            errorMessage = "后台启动失败：\(error.localizedDescription)"
            record(errorMessage + "\n")
            releasePipes()
            process = nil
        }
    }

    func stop(completion: @escaping () -> Void) {
        pendingRestart = nil
        beginStop(completion: completion)
    }

    private func beginStop(completion: @escaping () -> Void) {
        guard let child = process else {
            completion()
            return
        }
        stopCompletions.append(completion)
        if !child.isRunning {
            didExit(child)
            return
        }
        guard phase != .stopping else { return }
        phase = .stopping; busy = true
        runGeneration = UUID()
        if runRunning { runPhase = .stopping }
        observationGeneration = UUID()
        observationGrace?.cancel(); observationGrace = nil
        observationDeadline = nil
        observationState = "未知"; observationCandidate = "未知"
        observationEvidence = "暂无有效画面证据"
        if observationRunning { observationPhase = "正在停止" }
        status = "正在停止任务并回收后台，请稍候…"
        pollTimer?.invalidate(); pollTimer = nil
        observationTimer?.invalidate(); observationTimer = nil
        // 先走协作式停止，只有后台无响应时才终止属于本应用的进程组。
        sendShutdown()
        DispatchQueue.main.asyncAfter(deadline: .now() + 7) { [weak self, weak child] in
            guard let self, let child, child.isRunning, self.process === child else { return }
            self.record("后台未及时退出，发送终止信号。\n")
            self.signal(child, SIGTERM)
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self, weak child] in
                guard let self, let child, child.isRunning, self.process === child else { return }
                self.record("平台调用仍未返回，强制回收后台；最后一次操作需独立核对。\n")
                self.signal(child, SIGKILL)
            }
        }
    }

    private func signal(_ child: Process, _ signal: Int32) {
        let pid = child.processIdentifier
        Darwin.kill(ownsProcessGroup ? -pid : pid, signal)
    }

    private func sendShutdown() {
        requestID += 1
        let message: Object = ["jsonrpc": "2.0", "id": requestID, "method": "session.shutdown", "params": Object()]
        if let data = try? JSONSerialization.data(withJSONObject: message), let input {
            try? input.write(contentsOf: data + Data([10]))
        }
        try? input?.close()
        input = nil
    }

    private func didExit(_ child: Process) {
        guard process === child else { return }
        let expected = phase == .stopping
        releasePipes()
        process = nil
        ownsProcessGroup = false
        pollTimer?.invalidate(); pollTimer = nil
        observationTimer?.invalidate(); observationTimer = nil
        deadlines.values.forEach { $0.cancel() }; deadlines.removeAll()
        let replies = pending.values.map { $0 }; pending.removeAll()
        busy = false; polling = false
        if runRunning { runPhase = .finished }
        observationGeneration = UUID()
        observationGrace?.cancel(); observationGrace = nil
        observationDeadline = nil; observationStopping = false
        observationRunning = false; observationPolling = false; observationState = "未知"
        observationCandidate = "未知"; observationEvidence = "暂无有效画面证据"
        observationPhase = "后台已停止"
        clearFrame()
        let reason = child.terminationReason == .uncaughtSignal ? "信号终止" : "正常退出"
        record("后台已退出，状态码 \(child.terminationStatus)，\(reason)\n")
        if expected {
            phase = .idle; status = "后台已停止。"
        } else {
            phase = .failed
            errorMessage = "后台意外退出（\(child.terminationStatus)），可查看诊断并手动重启。"
        }
        if !expected { replies.forEach { $0(.failure(DesktopError(message: "后台已退出。"))) } }
        let callbacks = stopCompletions; stopCompletions.removeAll()
        callbacks.forEach { $0() }
    }

    private func releasePipes() {
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil
        try? outputPipe?.fileHandleForReading.close()
        try? errorPipe?.fileHandleForReading.close()
        try? input?.close()
        input = nil; outputPipe = nil; errorPipe = nil
    }

    private func call(_ method: String, _ params: Object = [:], timeoutSeconds: TimeInterval = 15, completion: @escaping Reply) {
        guard let input, processRunning, phase != .stopping else {
            completion(.failure(DesktopError(message: "后台当前不可用。")))
            return
        }
        requestID += 1
        let id = requestID
        do {
            let data = try JSONSerialization.data(withJSONObject: ["jsonrpc": "2.0", "id": id, "method": method, "params": params])
            pending[id] = completion
            let timeout = DispatchWorkItem { [weak self] in
                guard let self, let reply = self.pending.removeValue(forKey: id) else { return }
                self.deadlines.removeValue(forKey: id)
                self.failProtocol("操作超时：\(method)。后台将停止，不自动重复执行。")
                reply(.failure(DesktopError(message: "操作超时，正在回收后台。")))
            }
            deadlines[id] = timeout
            DispatchQueue.main.asyncAfter(deadline: .now() + timeoutSeconds, execute: timeout)
            try input.write(contentsOf: data + Data([10]))
        } catch {
            deadlines.removeValue(forKey: id)?.cancel()
            pending.removeValue(forKey: id)
            completion(.failure(error))
            failProtocol("后台通信失败：\(error.localizedDescription)")
        }
    }

    private func consume(_ data: Data) {
        buffer.append(data)
        guard buffer.count <= 2_097_152 else { failProtocol("后台响应超出上限。"); return }
        while let end = buffer.firstIndex(of: 10) {
            let line = Data(buffer[..<end]); buffer.removeSubrange(...end)
            do {
                guard let reply = try JSONSerialization.jsonObject(with: line) as? Object,
                      let id = reply["id"] as? Int else { throw DesktopError(message: "无法识别后台响应。") }
                guard let completion = pending.removeValue(forKey: id) else { continue }
                deadlines.removeValue(forKey: id)?.cancel()
                if let error = reply["error"] as? Object {
                    completion(.failure(DesktopError(message: error["message"] as? String ?? "后台操作失败。")))
                } else if let result = reply["result"] as? Object {
                    completion(.success(result))
                } else { completion(.failure(DesktopError(message: "后台返回了无效结果。"))) }
            } catch { failProtocol("后台协议错误：\(error.localizedDescription)") }
        }
    }

    private func failProtocol(_ message: String) {
        guard phase != .stopping else { return }
        errorMessage = message
        record(message + "\n")
        stop { [weak self] in self?.phase = .failed }
    }

    private func perform(_ method: String, _ params: Object = [:], success: @escaping (Object) -> Void) {
        guard canOperate else { return }
        busy = true; errorMessage = ""
        call(method, params) { [weak self] reply in
            guard let self else { return }
            self.busy = false
            switch reply {
            case .success(let value): success(value)
            case .failure(let error):
                self.errorMessage = error.localizedDescription
                self.record(error.localizedDescription + "\n")
            }
        }
    }

    // 权限由实际执行后台查询，界面不以自身授权代替子进程授权。
    func refreshPermissions() {
        guard canCheckPermissions else { return }
        checkingPermissions = true
        call("permissions.status") { [weak self] reply in
            guard let self else { return }
            self.checkingPermissions = false
            switch reply {
            case .success(let value): self.renderPermissions(value)
            case .failure(let error): self.errorMessage = "权限检测失败：\(error.localizedDescription)"
            }
        }
    }

    func requestPermission(_ kind: String) {
        guard canCheckPermissions else { return }
        busy = true; errorMessage = ""
        status = "请按 macOS 提示确认权限，完成后返回 Star。"
        // 截图权限提示可能等待用户选择，不能套用普通操作的短超时。
        call("permissions.request", ["kind": kind], timeoutSeconds: 120) { [weak self] reply in
            guard let self else { return }
            self.busy = false
            switch reply {
            case .success(let value):
                self.renderPermissions(value)
                self.status = "权限申请已发出。请在系统设置中确认，然后重新检测；必要时重启后台。"
            case .failure(let error): self.errorMessage = "权限申请失败：\(error.localizedDescription)"
            }
        }
    }

    func openPrivacySettings() {
        guard let url = URL(string: "x-apple.systempreferences:com.apple.preference.security") else { return }
        NSWorkspace.shared.open(url)
    }

    func restartBackend() {
        guard canRestartBackend, let workspace, let python, let sourceRoot else { return }
        let request = UUID()
        pendingRestart = request
        beginStop { [weak self] in
            guard let self, self.pendingRestart == request else { return }
            self.pendingRestart = nil
            self.start(workspace: workspace, python: python, sourceRoot: sourceRoot)
        }
    }

    private func renderPermissions(_ value: Object) {
        guard let accessibility = value["accessibility"] as? Bool,
              let screenRecording = value["screen_recording"] as? Bool else {
            errorMessage = "后台返回了无效的权限状态。"
            return
        }
        accessibilityAllowed = accessibility
        screenRecordingAllowed = screenRecording
        permissionsKnown = true
    }

    private func requirePermission(_ kind: String) -> Bool {
        let allowed = kind == "accessibility" ? accessibilityAllowed : screenRecordingAllowed
        guard permissionsKnown, allowed else {
            errorMessage = kind == "accessibility"
                ? "需要窗口控制权限，请点击上方“申请窗口控制”。"
                : "需要屏幕截图权限，请点击上方“申请屏幕截图”。"
            refreshPermissions()
            return false
        }
        return true
    }

    func clearFrame() {
        frameGeneration = UUID()
        frame = nil; selection = nil; searchRegion = nil; resourceText = ""
    }

    func readWindows() {
        guard requirePermission("accessibility") else { return }
        clearFrame(); windows = []; selectedWindow = ""
        perform("preparation.windows", ["application": application]) { [weak self] result in
            guard let self else { return }
            self.windows = (result["windows"] as? [Object] ?? []).compactMap { value in
                guard let id = value["id"] as? String, let title = value["title"] as? String else { return nil }
                return WindowChoice(id: id, title: title)
            }
            self.selectedWindow = self.windows.first?.id ?? ""
            self.status = self.windows.isEmpty ? "没有可用窗口，请检查应用名、窗口与辅助功能权限。" : "选择目标窗口后截取画面。"
        }
    }

    func capture() {
        guard requirePermission("accessibility"), requirePermission("screen_recording") else { return }
        clearFrame()
        let generation = frameGeneration
        perform("preparation.capture", ["application": application, "window_id": selectedWindow]) { [weak self] result in
            guard let self else { return }
            do {
                guard let id = result["id"] as? String, let window = result["window"] as? Object,
                      let image = result["image"] as? Object, let path = image["path"] as? String,
                      let width = image["width"] as? Int, let height = image["height"] as? Int,
                      let title = window["title"] as? String else { throw DesktopError(message: "截图元数据不完整。") }
                self.busy = true
                Task { [weak self] in
                    do {
                        let data = try await Task.detached(priority: .userInitiated) {
                            try Data(contentsOf: URL(fileURLWithPath: path))
                        }.value
                        guard let self, self.frameGeneration == generation, self.phase == .ready else { return }
                        guard let preview = NSImage(data: data) else { throw DesktopError(message: "截图无法解码。") }
                        self.frame = FrozenFrame(id: id, title: title, width: width, height: height, image: preview)
                        self.busy = false
                        self.status = "画面已冻结：点击取点，拖动框选模板。"
                        NSApp.activate(ignoringOtherApps: true)
                    } catch {
                        guard let self, self.frameGeneration == generation, self.phase == .ready else { return }
                        self.busy = false
                        self.errorMessage = error.localizedDescription
                    }
                }
            } catch { self.errorMessage = error.localizedDescription }
        }
    }

    func point(_ point: CGPoint) {
        guard let frame else { return }
        selection = nil
        perform("preparation.point", ["frame_id": frame.id, "x": Int(point.x), "y": Int(point.y)]) { [weak self] result in
            guard let self else { return }
            let name = self.targetName.isEmpty ? "目标" : self.targetName
            self.resourceText = self.pretty(["resources": ["points": [name: result["window_relative"] ?? [:]]], "screen": result["screen"] ?? [:]])
        }
    }

    func saveCrop() {
        guard let frame, let selection else { return }
        perform("preparation.crop", ["frame_id": frame.id, "region": selection.payload, "name": targetName]) { [weak self] result in
            guard let self else { return }
            self.resourceText = self.pretty(["resources": result["resources"] ?? [:]])
            self.status = "已保存 assets/\(result["image"] as? String ?? "")"
        }
    }

    func reloadObservationRules() {
        perform("observation.rules") { [weak self] result in
            self?.renderObservationRules(result)
        }
    }

    func useSelectionAsSearchRegion() {
        guard canOperate, let selection else { return }
        searchRegion = selection
    }

    func saveStateMaterial() {
        guard let frame, let selection, let threshold = Double(stateConfidence), threshold.isFinite else {
            errorMessage = "请框选素材并填写有效的匹配阈值。"
            return
        }
        var params: Object = ["frame_id": frame.id, "region": selection.payload, "name": targetName,
                              "state": stateName, "min_confidence": threshold]
        if let searchRegion { params["search_region"] = searchRegion.payload }
        perform("observation.rule.save", params) { [weak self] result in
            self?.renderObservationRules(result)
            self?.status = "状态素材已保存，可进入实时识别页开始观察。"
        }
    }

    func startObservation() {
        guard canOperate, requirePermission("accessibility"), requirePermission("screen_recording") else { return }
        observationGeneration = UUID()
        let generation = observationGeneration
        let requested = ProcessInfo.processInfo.systemUptime
        perform("observation.start", ["application": application, "window_id": selectedWindow,
                                      "hz": observationHz, "confirmations": confirmObservation ? 2 : 1]) { [weak self] result in
            guard let self else { return }
            guard self.phase == .ready, self.observationGeneration == generation else { return }
            self.observationStopping = false
            self.renderObservation(result, requested: requested)
            self.observationTimer?.invalidate()
            self.observationTimer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.observationGeneration == generation else { return }
                    self.pollObservation()
                }
            }
        }
    }

    func stopObservation() {
        guard phase == .ready, observationRunning, !observationStopping else { return }
        observationGeneration = UUID()
        let generation = observationGeneration
        observationStopping = true; busy = true; observationPolling = false
        observationDeadline = nil
        observationState = "未知"; observationCandidate = "未知"
        observationEvidence = "暂无有效画面证据"; observationPhase = "正在停止"
        observationTimer?.invalidate()
        observationTimer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.observationGeneration == generation else { return }
                self.pollObservation()
            }
        }
        let grace = DispatchWorkItem { [weak self] in
            guard let self, self.observationGeneration == generation, self.observationRunning else { return }
            self.observationError = "采集尚未结束，正在回收后台。请等待实际退出后手动重启。"
            self.stop {}
        }
        observationGrace = grace
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: grace)
        let requested = ProcessInfo.processInfo.systemUptime
        call("observation.stop") { [weak self] reply in
            guard let self, self.phase == .ready, self.observationGeneration == generation else { return }
            switch reply {
            case .success(let result): self.renderObservation(result, requested: requested)
            case .failure(let error): self.observationError = error.localizedDescription
            }
        }
    }

    private func pollObservation() {
        if let deadline = observationDeadline, ProcessInfo.processInfo.systemUptime > deadline {
            observationState = "未知"; observationCandidate = "未知"
            observationEvidence = "暂无有效画面证据"; observationPhase = "画面已过期"
        }
        guard phase == .ready, observationRunning, !observationPolling else { return }
        observationPolling = true
        let generation = observationGeneration
        let requested = ProcessInfo.processInfo.systemUptime
        call("observation.status") { [weak self] reply in
            guard let self, self.phase == .ready, self.observationGeneration == generation else { return }
            self.observationPolling = false
            switch reply {
            case .success(let result): self.renderObservation(result, requested: requested)
            case .failure(let error): self.observationError = error.localizedDescription
            }
        }
    }

    private func renderObservationRules(_ result: Object) {
        let rules = result["rules"] as? [Object] ?? []
        observationRuleSummary = rules.isEmpty ? "还没有状态素材，请到素材准备页框选并登记。" : rules.map { rule in
            let state = rule["state"] as? String ?? ""
            let image = rule["image"] as? String ?? ""
            let region = (rule["region"] as? Object).map { self.pretty($0) } ?? "整个窗口"
            let isPoints = rule["method"] as? String == "points"
            let method = isPoints ? "多点 · \(rule["point_count"] as? Int ?? 0) 点" : "模板"
            let location = isPoints ? "固定截图像素点位 · 整体偏移 ±\(rule["offset_radius"] as? Int ?? 0) 像素" : "搜索范围：\(region)"
            return "\(state) · 优先级 \(rule["priority"] as? Int ?? 0) · \(method) · \(image) · \(location)"
        }.joined(separator: "\n")
    }

    private func renderObservation(_ result: Object, requested: TimeInterval) {
        renderPerformance(result["performance"] as? Object ?? [:])
        observationRunning = result["running"] as? Bool ?? false
        observationState = result["current_state"] as? String ?? "未知"
        observationCandidate = result["candidate_state"] as? String ?? "未知"
        let phase = result["phase"] as? String ?? "idle"
        observationPhase = ["idle": "未启动", "waiting": "等待首帧", "observing": "正在观察", "unavailable": "画面不可用",
                            "stale": "画面已过期", "stopping": "正在停止", "stopped": "已停止"][phase] ?? phase
        observationError = result["error"] as? String ?? ""
        let sequence = result["sequence"] as? Int ?? 0
        let elapsed = result["elapsed_ms"] as? Double ?? 0
        let actual = result["actual_hz"] as? Double ?? 0
        let age = result["age_ms"] as? Double
        observationMetrics = "第 \(sequence) 轮 · 耗时 \(String(format: "%.0f", elapsed)) ms · 实际 \(String(format: "%.1f", actual)) 次/秒" +
            (age.map { " · 画面距今 \(String(format: "%.0f", $0)) ms" } ?? "")
        let evidence = result["evidence"] as? [Object] ?? []
        observationEvidence = evidence.isEmpty ? "暂无有效画面证据" : evidence.map { item in
            let skipped = item["skipped"] as? Bool ?? false
            let priority = item["priority"] as? Int ?? 0
            let status = skipped ? "未检测" : ((item["found"] as? Bool ?? false) ? "命中" : "未命中")
            let score = (item["score"] as? Double).map { String(format: "%.3f", $0) } ?? "—"
            let rect = (item["rect"] as? Object).map { self.pretty($0) } ?? "无位置"
            let detail = item["method"] as? String == "points" ? "多点 · 匹配 \((item["matched_points"] as? Int).map(String.init) ?? "—")/\(item["point_count"] as? Int ?? 0) 点" : "相似度 \(score)"
            return "\(item["state"] as? String ?? "") / \(item["name"] as? String ?? "") · 优先级 \(priority) · \(status) · \(detail) · \(rect)"
        }.joined(separator: "\n\n")
        let formatter = DateFormatter(); formatter.dateFormat = "HH:mm:ss"
        let history = result["history"] as? [Object] ?? []
        observationHistory = history.isEmpty ? "暂无状态变化" : "历史记录（不代表当前画面）\n" + history.prefix(32).map { item in
            let time = formatter.string(from: Date(timeIntervalSince1970: item["at"] as? Double ?? 0))
            return "\(time)  \(item["previous"] as? String ?? "") → \(item["state"] as? String ?? "")"
        }.joined(separator: "\n")
        let hz = result["hz"] as? Double ?? 2
        observationDeadline = requested + max(2, 3 / hz) - (age ?? 0) / 1000
        if observationStopping || ProcessInfo.processInfo.systemUptime > (observationDeadline ?? 0) {
            observationState = "未知"; observationCandidate = "未知"
            observationEvidence = "暂无有效画面证据"
            if observationStopping { observationPhase = observationRunning ? "正在停止" : "已停止" }
            else if observationRunning { observationPhase = "画面已过期" }
        }
        if !observationRunning {
            observationTimer?.invalidate(); observationTimer = nil
            observationGrace?.cancel(); observationGrace = nil
            observationDeadline = nil
            if observationStopping { busy = false; observationStopping = false }
        }
    }

    private func renderPerformance(_ value: Object) {
        func milliseconds(_ key: String) -> String {
            guard let number = value[key] as? Double else { return "—" }
            return String(format: "%.1f", number) + " ms"
        }
        let materials = (value["material_count"] as? Int).map(String.init) ?? "—"
        let attempts = value["attempts"] as? Int ?? 0
        let failures = value["failures"] as? Int ?? 0
        let overBudget = value["over_budget"] as? Int ?? 0
        let stale = value["stale_results"] as? Int ?? 0
        let samples = value["sample_count"] as? Int ?? 0
        let limit = value["window_limit"] as? Int ?? 120
        let recentFailure: String
        if let at = value["last_failure_at"] as? Double {
            let formatter = DateFormatter()
            formatter.dateStyle = .short; formatter.timeStyle = .medium
            let message = value["last_failure_message"] as? String ?? ""
            recentFailure = formatter.string(from: Date(timeIntervalSince1970: at)) + " " +
                (message.isEmpty ? "未提供错误详情" : message)
        } else {
            recentFailure = "无"
        }
        let streaming = value["capture_mode"] as? String == "window_stream"
        let captureLabel = streaming ? "窗口流取帧" : "截图"
        let duplicates = value["duplicate_results"] as? Int ?? 0
        let checked = (value["checked_count"] as? Int).map(String.init) ?? "—"
        let skipped = (value["skipped_count"] as? Int).map(String.init) ?? "—"
        observationPerformanceSummary = "素材 \(materials) · 本轮检查 \(checked) · 跳过 \(skipped) · 最近轮 \(milliseconds("round_ms")) · p95 \(milliseconds("p95_ms"))"
        observationPerformanceDetails = "\(captureLabel) \(milliseconds("screenshot_ms")) · 识别 \(milliseconds("recognition_ms"))\n" +
            "高优先级先检查，命中后跳过低层素材。\n" +
            "源画面年龄 p95 \(milliseconds("source_age_p95_ms")) · 重复读取 \(duplicates) 次（不增加连续确认）\n" +
            "本次累计 \(attempts) 轮 · 成功 \(attempts - failures) · 失败 \(failures) · 超频率预算 \(overBudget) · 超龄结果 \(stale)\n" +
            "最近失败（历史，不代表当前不可用）：\(recentFailure)\n" +
            "最近最多 \(limit) 轮，当前 \(samples) 个样本（含失败）\n" +
            "整轮 p50 \(milliseconds("p50_ms")) · p95 \(milliseconds("p95_ms")) · max \(milliseconds("max_ms"))\n" +
            (streaming ? "采集频率跟随检测频率。取帧含窗口核对和内存转换，首轮含启动等待；源画面年龄单独统计，重复缓存不会续期。" : "截图含窗口核对和 PNG 读取。") +
            "识别含 OpenCV 加载、图像转换、模板加载与匹配。整轮不含调频等待或界面刷新；超过 1000/目标频率 ms 记一次超预算。停止保留统计。"
    }

    func reloadScripts() {
        perform("script.reload") { [weak self] result in
            guard let self else { return }
            self.scripts = result["scripts"] as? [String] ?? []
            self.selectedScript = self.scripts.first ?? ""
            let errors = result["errors"] as? [Object] ?? []
            self.scriptDetails = errors.compactMap { $0["message"] as? String }.joined(separator: "\n")
            if !errors.isEmpty { self.errorMessage = self.scriptDetails }
            self.describeScript()
        }
    }

    func describeScript() {
        guard !selectedScript.isEmpty else { return }
        perform("script.details", ["name": selectedScript]) { [weak self] result in
            let steps = result["steps"] as? [String] ?? []
            let checks = (result["readiness"] as? [[String]] ?? []).map { $0.joined(separator: " · ") }
            self?.scriptDetails = (steps + [""] + checks).joined(separator: "\n")
        }
    }

    func startScript() {
        guard canOperate, dryRun || requirePermission("accessibility") else { return }
        runGeneration = UUID()
        let generation = runGeneration
        polling = false
        runPhase = .idle
        runLog = ""
        perform("script.start", ["name": selectedScript, "dry_run": dryRun,
                                 "dry_run_color": dryRunColor, "dry_run_screen_state": dryRunState]) { [weak self] result in
            guard let self, self.runGeneration == generation, self.phase == .ready else { return }
            self.renderRun(result)
        }
    }

    func stopScript() {
        guard canStopScript else { return }
        runPhase = .stopping
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

    private func pollRun() {
        guard phase == .ready, runRunning, !polling else { return }
        polling = true
        let generation = runGeneration
        call("script.status") { [weak self] reply in
            guard let self, self.runGeneration == generation, self.phase == .ready else { return }
            self.polling = false
            if case .success(let result) = reply { self.renderRun(result) }
        }
    }

    private func renderRun(_ result: Object) {
        let running = result["running"] as? Bool ?? false
        // 已确认结束的同次运行不能被更早发出的在途状态恢复为运行中。
        guard runPhase != .finished else { return }
        if !running { runPhase = .finished }
        else if runPhase != .stopping { runPhase = .running }
        let stdout = result["stdout"] as? String ?? "", stderr = result["stderr"] as? String ?? ""
        let text = stdout + (stderr.isEmpty ? "" : "\n提示与错误：\n" + stderr)
        if runLog != text { runLog = text }
        let reason = result["finish_reason"] as? String ?? "idle"
        let labels = ["completed": "脚本执行完成", "cancelled": "已取消", "configuration_failed": "配置错误",
                      "setup_failed": "运行环境不可用", "failed": "运行失败", "timed_out": "任务等待超时",
                      "cleanup_failed": "运行资源回收失败", "stopped_unmet_condition": "条件未满足，已停止", "idle": "脚本未运行"]
        switch runPhase {
        case .stopping: status = "已请求停止，正在等待当前操作结束。等待期间可重启后台回收进程。"
        case .running: status = "脚本运行中…"
        case .idle, .finished: status = labels[reason] ?? reason
        }
    }

    private func pretty(_ value: Object) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) else { return "" }
        return String(decoding: data, as: UTF8.self)
    }

    private func record(_ message: String) {
        let message = ISO8601DateFormatter().string(from: Date()) + " " + message
        diagnostics = String((diagnostics + message).suffix(32768))
        guard let workspace else { return }
        let folder = workspace.appendingPathComponent(".star")
        let log = folder.appendingPathComponent("desktop.log")
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: log.path) { FileManager.default.createFile(atPath: log.path, contents: nil) }
        if let handle = try? FileHandle(forWritingTo: log) {
            defer { try? handle.close() }
            let size = (try? handle.seekToEnd()) ?? 0
            if size > 1_048_576 { try? handle.truncate(atOffset: 0); try? handle.seek(toOffset: 0) }
            try? handle.write(contentsOf: Data(message.utf8))
        }
    }
}
