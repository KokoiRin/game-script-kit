import AppKit
import Combine
import Foundation
import Darwin

struct WindowChoice: Identifiable {
    let id: String
    let title: String
}

struct PixelRegion: Equatable {
    let left: Int
    let top: Int
    let width: Int
    let height: Int
    var payload: [String: Int] { ["left": left, "top": top, "width": width, "height": height] }
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
    typealias Object = [String: Any]
    typealias Reply = (Result<Object, Error>) -> Void

    @Published var phase: Phase = .idle
    @Published var busy = false
    @Published var status = "请选择任务工作区。"
    @Published var errorMessage = ""
    @Published var diagnostics = ""
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
    @Published var runRunning = false
    @Published var dryRun = true
    @Published var dryRunColor = "#000000"
    @Published var dryRunState = "未知"
    var canOperate: Bool { phase == .ready && !busy && !runRunning }
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
    private var stopCompletions: [() -> Void] = []
    private var python: URL?
    private var sourceRoot: URL?
    private var ownsProcessGroup = false
    private var frameGeneration = UUID()

    func start(workspace: URL, python: URL, sourceRoot: URL) {
        guard !processRunning else { return }
        self.workspace = workspace
        self.python = python
        self.sourceRoot = sourceRoot
        phase = .starting
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
            let data = (try? handle.read(upToCount: 65536)) ?? Data()
            guard !data.isEmpty else { return }
            Task { @MainActor in
                guard let self, let child, self.process === child else { return }
                self.consume(data)
            }
        }
        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self, weak child] handle in
            let data = (try? handle.read(upToCount: 65536)) ?? Data()
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
                guard let self else { return }
                switch reply {
                case .success(let info):
                    guard info["protocol"] as? Int == 1 else {
                        self.failProtocol("后台协议版本不兼容。")
                        return
                    }
                    self.ownsProcessGroup = (info["process_group"] as? Int) == Int(child.processIdentifier)
                    self.phase = .ready
                    self.status = "就绪。素材准备和脚本运行使用同一受管理的后台。"
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

    func restart() {
        guard !processRunning, let workspace, let python, let sourceRoot else { return }
        start(workspace: workspace, python: python, sourceRoot: sourceRoot)
    }

    func stop(completion: @escaping () -> Void) {
        guard let child = process, child.isRunning else {
            completion()
            return
        }
        stopCompletions.append(completion)
        guard phase != .stopping else { return }
        phase = .stopping; busy = true
        status = "正在停止任务并回收后台，请稍候…"
        pollTimer?.invalidate(); pollTimer = nil
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
        deadlines.values.forEach { $0.cancel() }; deadlines.removeAll()
        let replies = pending.values.map { $0 }; pending.removeAll()
        busy = false; polling = false; runRunning = false
        clearFrame()
        record("后台已退出，状态码 \(child.terminationStatus)\n")
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

    private func call(_ method: String, _ params: Object = [:], completion: @escaping Reply) {
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
            DispatchQueue.main.asyncAfter(deadline: .now() + 15, execute: timeout)
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

    func clearFrame() {
        frameGeneration = UUID()
        frame = nil; selection = nil; resourceText = ""
    }

    func readWindows() {
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
        runLog = ""
        perform("script.start", ["name": selectedScript, "dry_run": dryRun,
                                 "dry_run_color": dryRunColor, "dry_run_screen_state": dryRunState]) { [weak self] result in
            self?.renderRun(result)
        }
    }

    func stopScript() {
        guard phase == .ready, runRunning, !busy else { return }
        busy = true
        call("script.stop") { [weak self] reply in
            guard let self else { return }
            self.busy = false
            switch reply {
            case .success(let result): self.renderRun(result); self.status = "已请求停止，正在等待当前操作结束…"
            case .failure(let error): self.errorMessage = error.localizedDescription
            }
        }
    }

    private func pollRun() {
        guard phase == .ready, runRunning, !polling else { return }
        polling = true
        call("script.status") { [weak self] reply in
            guard let self else { return }
            self.polling = false
            if case .success(let result) = reply { self.renderRun(result) }
        }
    }

    private func renderRun(_ result: Object) {
        runRunning = result["running"] as? Bool ?? false
        let stdout = result["stdout"] as? String ?? "", stderr = result["stderr"] as? String ?? ""
        let text = stdout + (stderr.isEmpty ? "" : "\n提示与错误：\n" + stderr)
        if runLog != text { runLog = text }
        let reason = result["finish_reason"] as? String ?? "idle"
        let labels = ["completed": "脚本执行完成", "cancelled": "已取消", "configuration_failed": "配置错误",
                      "setup_failed": "运行环境不可用", "failed": "运行失败", "stopped_unmet_condition": "条件未满足，已停止", "idle": "脚本未运行"]
        status = runRunning ? "脚本运行中…" : (labels[reason] ?? reason)
    }

    private func pretty(_ value: Object) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) else { return "" }
        return String(decoding: data, as: UTF8.self)
    }

    private func record(_ message: String) {
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
