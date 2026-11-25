import Darwin
import Foundation

/// 管理单个受监督的 Python 后台子进程、标准管道拆帧、JSON-RPC 请求超时与分级回收。
@MainActor
final class BackendClient {
    typealias Object = [String: Any]
    typealias Reply = (Result<Object, Error>) -> Void

    private static let maxBufferBytes = 2_097_152

    private var process: Process?
    private var input: FileHandle?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?
    private var buffer = Data()
    private var requestID = 0
    private var pending: [Int: Reply] = [:]
    private var deadlines: [Int: DispatchWorkItem] = [:]
    private var stopCompletions: [() -> Void] = []
    private var ownsProcessGroup = false
    private var stopping = false

    private(set) var generation = UUID()
    var hasProcess: Bool { process != nil }
    var isRunning: Bool { process?.isRunning ?? false }
    var isStopping: Bool { stopping }

    var onLog: ((String) -> Void)?
    var onProtocolFailure: ((String) -> Void)?
    var onDidExit: ((_ status: Int32, _ expected: Bool) -> Void)?

    /// 启动绑定指定工作区的后台子进程并返回本次进程的唯一代次标识。
    func start(workspace: URL, python: URL, sourceRoot: URL) throws -> UUID {
        guard process == nil else { return generation }
        ownsProcessGroup = false
        stopping = false
        buffer.removeAll(keepingCapacity: false)
        let currentGeneration = UUID()
        generation = currentGeneration

        let child = Process(), stdinPipe = Pipe(), stdoutPipe = Pipe(), stderrPipe = Pipe()
        child.executableURL = python
        child.arguments = [
            "-u", "-m", "game_automation.platform.local_desktop.entrypoints.desktop_backend",
            "--workspace", workspace.path,
        ]
        child.currentDirectoryURL = sourceRoot
        var environment = ProcessInfo.processInfo.environment
        let source = sourceRoot.appendingPathComponent("src").path
        environment["PYTHONPATH"] = source + (environment["PYTHONPATH"].map { ":" + $0 } ?? "")
        child.environment = environment
        child.standardInput = stdinPipe
        child.standardOutput = stdoutPipe
        child.standardError = stderrPipe
        input = stdinPipe.fileHandleForWriting
        outputPipe = stdoutPipe
        errorPipe = stderrPipe

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
                self.onLog?(String(decoding: data, as: UTF8.self))
            }
        }
        child.terminationHandler = { [weak self] child in
            Task { @MainActor in self?.didExit(child) }
        }
        process = child

        do {
            try child.run()
            onLog?("后台已启动，PID \(child.processIdentifier)\n")
            return currentGeneration
        } catch {
            releasePipes()
            process = nil
            throw error
        }
    }

    /// 根据握手返回的进程组编号确认是否拥有独立进程组。
    func configureProcessGroup(_ reportedGroup: Int?) {
        guard let child = process else { return }
        ownsProcessGroup = reportedGroup == Int(child.processIdentifier)
    }

    /// 发送一条 JSON-RPC 2.0 请求并在超时或通信故障时通知协议失败。
    func call(_ method: String, _ params: Object = [:], timeoutSeconds: TimeInterval = 15, completion: @escaping Reply) {
        guard let input, isRunning, !stopping else {
            completion(.failure(DesktopError(message: "后台当前不可用。")))
            return
        }
        requestID += 1
        let id = requestID
        do {
            let data = try JSONSerialization.data(
                withJSONObject: ["jsonrpc": "2.0", "id": id, "method": method, "params": params]
            )
            pending[id] = completion
            let timeout = DispatchWorkItem { [weak self] in
                guard let self, let reply = self.pending.removeValue(forKey: id) else { return }
                self.deadlines.removeValue(forKey: id)
                self.reportProtocolFailure("操作超时：\(method)。后台将停止，不自动重复执行。")
                reply(.failure(DesktopError(message: "操作超时，正在回收后台。")))
            }
            deadlines[id] = timeout
            DispatchQueue.main.asyncAfter(deadline: .now() + timeoutSeconds, execute: timeout)
            try input.write(contentsOf: data + Data([10]))
        } catch {
            deadlines.removeValue(forKey: id)?.cancel()
            pending.removeValue(forKey: id)
            completion(.failure(error))
            reportProtocolFailure("后台通信失败：\(error.localizedDescription)")
        }
    }

    /// 先走协作式关闭，7 秒无响应发 SIGTERM，再等 2 秒发 SIGKILL 回收进程组。
    func stop(completion: @escaping () -> Void) {
        guard let child = process else {
            completion()
            return
        }
        stopCompletions.append(completion)
        if !child.isRunning {
            didExit(child)
            return
        }
        guard !stopping else { return }
        stopping = true
        sendShutdown()
        DispatchQueue.main.asyncAfter(deadline: .now() + 7) { [weak self, weak child] in
            guard let self, let child, child.isRunning, self.process === child else { return }
            self.onLog?("后台未及时退出，发送终止信号。\n")
            self.sendSignal(child, SIGTERM)
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self, weak child] in
                guard let self, let child, child.isRunning, self.process === child else { return }
                self.onLog?("平台调用仍未返回，强制回收后台；最后一次操作需独立核对。\n")
                self.sendSignal(child, SIGKILL)
            }
        }
    }

    private func sendSignal(_ child: Process, _ signal: Int32) {
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

    private func consume(_ data: Data) {
        buffer.append(data)
        guard buffer.count <= Self.maxBufferBytes else {
            reportProtocolFailure("后台响应超出上限。")
            return
        }
        while let end = buffer.firstIndex(of: 10) {
            let line = Data(buffer[..<end])
            buffer.removeSubrange(...end)
            do {
                guard let reply = try JSONSerialization.jsonObject(with: line) as? Object,
                      let id = reply["id"] as? Int else {
                    throw DesktopError(message: "无法识别后台响应。")
                }
                guard let completion = pending.removeValue(forKey: id) else { continue }
                deadlines.removeValue(forKey: id)?.cancel()
                if let error = reply["error"] as? Object {
                    completion(.failure(DesktopError(message: error["message"] as? String ?? "后台操作失败。")))
                } else if let result = reply["result"] as? Object {
                    completion(.success(result))
                } else {
                    completion(.failure(DesktopError(message: "后台返回了无效结果。")))
                }
            } catch {
                reportProtocolFailure("后台协议错误：\(error.localizedDescription)")
            }
        }
    }

    private func reportProtocolFailure(_ message: String) {
        guard !stopping else { return }
        onProtocolFailure?(message)
    }

    private func didExit(_ child: Process) {
        guard process === child else { return }
        let expected = stopping
        releasePipes()
        process = nil
        ownsProcessGroup = false
        stopping = false
        deadlines.values.forEach { $0.cancel() }
        deadlines.removeAll()
        let replies = pending.values.map { $0 }
        pending.removeAll()
        let reason = child.terminationReason == .uncaughtSignal ? "信号终止" : "正常退出"
        onLog?("后台已退出，状态码 \(child.terminationStatus)，\(reason)\n")
        onDidExit?(child.terminationStatus, expected)
        if !expected {
            replies.forEach { $0(.failure(DesktopError(message: "后台已退出。"))) }
        }
        let callbacks = stopCompletions
        stopCompletions.removeAll()
        callbacks.forEach { $0() }
    }

    private func releasePipes() {
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil
        try? outputPipe?.fileHandleForReading.close()
        try? errorPipe?.fileHandleForReading.close()
        try? input?.close()
        input = nil
        outputPipe = nil
        errorPipe = nil
    }
}
