import AppKit
import Combine
import Foundation

struct CompanionTarget: Equatable {
    let pid: Int32
    let windowNumber: UInt32
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
    @Published private(set) var companionTarget: CompanionTarget?
    @Published var permissions = PermissionState()
    @Published var preparation = PreparationState()
    @Published var observation = ObservationState()
    @Published var execution = ExecutionState()

    var canOperate: Bool { phase == .ready && !busy && !execution.isRunning && !observation.running }
    var canSwitchWorkspace: Bool {
        !busy && !execution.isRunning && !observation.running && phase != .starting && phase != .stopping
    }
    var canRestartBackend: Bool {
        !busy && execution.runPhase != .running && !observation.running && phase != .starting && phase != .stopping &&
            workspace != nil && python != nil && sourceRoot != nil
    }
    var showsProgress: Bool { busy || phase == .starting || phase == .stopping || execution.runPhase == .stopping }
    var processRunning: Bool { client.isRunning }

    private let client = BackendClient()
    private var pollTimer: Timer?
    private var companionPolling = false
    private var pendingRestart: UUID?
    private var python: URL?
    private var sourceRoot: URL?

    // 各领域 extension 共享的代次与轮询协调字段。
    var savedPlanBaseline = ""
    var runPolling = false
    var runGeneration = UUID()
    var frameGeneration = UUID()
    var observationPolling = false
    var observationTimer: Timer?
    var observationGeneration = UUID()
    var observationGrace: DispatchWorkItem?
    var observationDeadline: TimeInterval?
    var observationStopping = false

    init() {
        client.onLog = { [weak self] text in self?.record(text) }
        client.onProtocolFailure = { [weak self] message in self?.failProtocol(message) }
        client.onDidExit = { [weak self] status, expected in self?.handleBackendExit(status: status, expected: expected) }
    }

    func start(workspace: URL, python: URL, sourceRoot: URL) {
        guard !client.hasProcess else { return }
        self.workspace = workspace
        self.python = python
        self.sourceRoot = sourceRoot
        phase = .starting
        companionTarget = nil
        companionPolling = false
        runGeneration = UUID()
        runPolling = false
        observationGeneration = UUID()
        observationGrace?.cancel(); observationGrace = nil
        observationDeadline = nil; observationStopping = false
        observationPolling = false
        observation.resetForStart()
        permissions.resetForStart()
        execution.resetForStart()
        savedPlanBaseline = ""
        frameGeneration = UUID()
        preparation.resetWindows()
        errorMessage = ""
        status = "正在启动本地后台…"
        do {
            let generation = try client.start(workspace: workspace, python: python, sourceRoot: sourceRoot)
            call("session.info") { [weak self] reply in
                guard let self, self.client.generation == generation, self.phase == .starting else { return }
                switch reply {
                case .success(let info):
                    guard info["protocol"] as? Int == 1 else {
                        self.failProtocol("后台协议版本不兼容。")
                        return
                    }
                    self.client.configureProcessGroup(info["process_group"] as? Int)
                    self.phase = .ready
                    self.status = "就绪。素材准备和脚本运行使用同一受管理的后台。"
                    self.refreshPermissions()
                    self.refreshCompanionTarget()
                    self.pollTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
                        Task { @MainActor in
                            self?.pollRun()
                            self?.refreshCompanionTarget()
                        }
                    }
                case .failure(let error): self.failProtocol(error.localizedDescription)
                }
            }
        } catch {
            phase = .failed
            errorMessage = "后台启动失败：\(error.localizedDescription)"
            record(errorMessage + "\n")
        }
    }

    func stop(completion: @escaping () -> Void) {
        pendingRestart = nil
        beginStop(completion: completion)
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

    func refreshCompanionTarget() {
        guard phase == .ready, !companionPolling else { return }
        companionPolling = true
        let generation = client.generation
        let name = execution.selectedScript
        let saved = execution.useSavedPlan
        call("companion.target", ["file": name, "use_saved_plan": saved]) { [weak self] reply in
            guard let self, self.client.generation == generation, self.phase == .ready else { return }
            self.companionPolling = false
            guard self.execution.selectedScript == name, self.execution.useSavedPlan == saved else { return }
            if case .success(let result) = reply,
               let target = result["target"] as? Object,
               let pid = target["pid"] as? Int32,
               let number = target["window_number"] as? UInt32 {
                self.companionTarget = CompanionTarget(pid: pid, windowNumber: number)
            } else {
                self.companionTarget = nil
            }
        }
    }

    func call(_ method: String, _ params: Object = [:], timeoutSeconds: TimeInterval = 15, completion: @escaping Reply) {
        guard phase != .stopping else {
            completion(.failure(DesktopError(message: "后台当前不可用。")))
            return
        }
        client.call(method, params, timeoutSeconds: timeoutSeconds, completion: completion)
    }

    func perform(_ method: String, _ params: Object = [:], success: @escaping (Object) -> Void) {
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

    func record(_ message: String) {
        DiagnosticsLog.append(message, to: &diagnostics, workspace: workspace)
    }

    private func beginStop(completion: @escaping () -> Void) {
        guard client.hasProcess else {
            completion()
            return
        }
        if !client.isRunning {
            client.stop(completion: completion)
            return
        }
        if phase != .stopping {
            phase = .stopping; busy = true
            companionTarget = nil
            runGeneration = UUID()
            if execution.isRunning { execution.runPhase = .stopping }
            observationGeneration = UUID()
            observationGrace?.cancel(); observationGrace = nil
            observationDeadline = nil
            observation.markStopping(onlyIfRunning: true)
            status = "正在停止任务并回收后台，请稍候…"
            pollTimer?.invalidate(); pollTimer = nil
            observationTimer?.invalidate(); observationTimer = nil
        }
        client.stop(completion: completion)
    }

    private func handleBackendExit(status exitStatus: Int32, expected: Bool) {
        companionTarget = nil
        companionPolling = false
        pollTimer?.invalidate(); pollTimer = nil
        observationTimer?.invalidate(); observationTimer = nil
        busy = false; runPolling = false
        if execution.isRunning { execution.runPhase = .finished }
        observationGeneration = UUID()
        observationGrace?.cancel(); observationGrace = nil
        observationDeadline = nil; observationStopping = false
        observationPolling = false
        observation.markStoppedOnExit()
        clearFrame()
        if expected {
            phase = .idle; status = "后台已停止。"
        } else {
            phase = .failed
            errorMessage = "后台意外退出（\(exitStatus)），可查看诊断并手动重启。"
        }
    }

    private func failProtocol(_ message: String) {
        guard phase != .stopping else { return }
        errorMessage = message
        record(message + "\n")
        stop { [weak self] in self?.phase = .failed }
    }
}
