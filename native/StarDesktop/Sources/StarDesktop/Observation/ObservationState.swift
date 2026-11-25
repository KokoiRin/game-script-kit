import Foundation

struct ObservationState {
    var running = false
    var hz = 2
    var confirm = true
    var state = "未知"
    var candidate = "未知"
    var phase = "未启动"
    var metrics = "暂无检测结果"
    var performanceSummary = "性能：尚无采样"
    var performanceDetails = "统计随每轮采样更新，轮询不重复计数。"
    var evidence = "暂无匹配证据"
    var history = "暂无状态变化"
    var error = ""
    var ruleSummary = "尚未读取状态素材"

    mutating func resetForStart() {
        running = false
        state = "未知"
        candidate = "未知"
        phase = "未启动"
        metrics = "暂无检测结果"
        performanceSummary = "性能：尚无采样"
        performanceDetails = "统计随每轮采样更新，轮询不重复计数。"
        evidence = "暂无匹配证据"
        history = "暂无状态变化"
        error = ""
        ruleSummary = "尚未读取状态素材"
    }

    mutating func markStopping(onlyIfRunning: Bool = false) {
        state = "未知"
        candidate = "未知"
        evidence = "暂无有效画面证据"
        if !onlyIfRunning || running { phase = "正在停止" }
    }

    mutating func markStoppedOnExit() {
        running = false
        state = "未知"
        candidate = "未知"
        evidence = "暂无有效画面证据"
        phase = "后台已停止"
    }

    mutating func markStale() {
        state = "未知"
        candidate = "未知"
        evidence = "暂无有效画面证据"
        phase = "画面已过期"
    }
}

extension DesktopSession {
    var canStopObservation: Bool { phase == .ready && observation.running && !observationStopping }

    func reloadObservationRules() {
        perform("observation.rules") { [weak self] result in
            self?.renderObservationRules(result)
        }
    }

    func startObservation() {
        guard canOperate, requirePermission("accessibility"), requirePermission("screen_recording") else { return }
        observationGeneration = UUID()
        let generation = observationGeneration
        let requested = ProcessInfo.processInfo.systemUptime
        perform("observation.start", ["application": preparation.application, "window_id": preparation.selectedWindow,
                                      "hz": observation.hz, "confirmations": observation.confirm ? 2 : 1]) { [weak self] result in
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
        guard phase == .ready, observation.running, !observationStopping else { return }
        observationGeneration = UUID()
        let generation = observationGeneration
        observationStopping = true; busy = true; observationPolling = false
        observationDeadline = nil
        observation.markStopping()
        observationTimer?.invalidate()
        observationTimer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, self.observationGeneration == generation else { return }
                self.pollObservation()
            }
        }
        let grace = DispatchWorkItem { [weak self] in
            guard let self, self.observationGeneration == generation, self.observation.running else { return }
            self.observation.error = "采集尚未结束，正在回收后台。请等待实际退出后手动重启。"
            self.stop {}
        }
        observationGrace = grace
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: grace)
        let requested = ProcessInfo.processInfo.systemUptime
        call("observation.stop") { [weak self] reply in
            guard let self, self.phase == .ready, self.observationGeneration == generation else { return }
            switch reply {
            case .success(let result): self.renderObservation(result, requested: requested)
            case .failure(let error): self.observation.error = error.localizedDescription
            }
        }
    }

    func pollObservation() {
        if let deadline = observationDeadline, ProcessInfo.processInfo.systemUptime > deadline {
            observation.markStale()
        }
        guard phase == .ready, observation.running, !observationPolling else { return }
        observationPolling = true
        let generation = observationGeneration
        let requested = ProcessInfo.processInfo.systemUptime
        call("observation.status") { [weak self] reply in
            guard let self, self.phase == .ready, self.observationGeneration == generation else { return }
            self.observationPolling = false
            switch reply {
            case .success(let result): self.renderObservation(result, requested: requested)
            case .failure(let error): self.observation.error = error.localizedDescription
            }
        }
    }

    func renderObservationRules(_ result: Object) {
        observation.ruleSummary = ObservationFormatter.rulesSummary(result)
    }

    func renderObservation(_ result: Object, requested: TimeInterval) {
        let perf = ObservationFormatter.performance(result["performance"] as? Object ?? [:])
        observation.performanceSummary = perf.summary
        observation.performanceDetails = perf.details
        observation.running = result["running"] as? Bool ?? false
        observation.state = result["current_state"] as? String ?? "未知"
        observation.candidate = result["candidate_state"] as? String ?? "未知"
        observation.phase = ObservationFormatter.phaseLabel(result["phase"] as? String ?? "idle")
        observation.error = result["error"] as? String ?? ""
        observation.metrics = ObservationFormatter.metrics(result)
        observation.evidence = ObservationFormatter.evidence(result)
        observation.history = ObservationFormatter.history(result)
        let age = result["age_ms"] as? Double
        let hz = result["hz"] as? Double ?? 2
        observationDeadline = requested + max(2, 3 / hz) - (age ?? 0) / 1000
        if observationStopping || ProcessInfo.processInfo.systemUptime > (observationDeadline ?? 0) {
            observation.state = "未知"; observation.candidate = "未知"
            observation.evidence = "暂无有效画面证据"
            if observationStopping { observation.phase = observation.running ? "正在停止" : "已停止" }
            else if observation.running { observation.phase = "画面已过期" }
        }
        if !observation.running {
            observationTimer?.invalidate(); observationTimer = nil
            observationGrace?.cancel(); observationGrace = nil
            observationDeadline = nil
            if observationStopping { busy = false; observationStopping = false }
        }
    }
}
