import AppKit
import SwiftUI

struct TargetWindowPicker: View {
    @ObservedObject var session: DesktopSession
    var showCapture = false
    var compact = false

    var body: some View {
        Group {
            if compact {
                VStack(alignment: .leading, spacing: 8) {
                    applicationControls
                    windowControl
                }
            } else {
                HStack {
                    applicationControls
                    windowControl
                    if showCapture {
                        Button("截取画面", action: session.capture).disabled(session.preparation.selectedWindow.isEmpty)
                    }
                }
            }
        }.disabled(!session.canOperate)
    }

    private var applicationControls: some View {
        HStack {
            TextField("目标应用名", text: $session.preparation.application)
                .onChange(of: session.preparation.application) { _ in
                    session.preparation.windows = []; session.preparation.selectedWindow = ""; session.clearFrame()
                }
            Button("读取窗口", action: session.readWindows).disabled(session.preparation.application.isEmpty)
        }
    }

    private var windowControl: some View {
        Picker("窗口", selection: $session.preparation.selectedWindow) {
            Text("请选择窗口").tag("")
            ForEach(session.preparation.windows) { Text($0.title).tag($0.id) }
        }.frame(minWidth: 180)
            .onChange(of: session.preparation.selectedWindow) { _ in session.clearFrame() }
    }
}

struct ObservationView: View {
    @ObservedObject var session: DesktopSession
    var compact = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TargetWindowPicker(session: session, compact: compact)
            if compact {
                VStack(alignment: .leading, spacing: 8) {
                    settings
                    actions
                }
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        currentState
                        captureError
                        performance
                        evidence
                        history
                        DisclosureGroup("已登记的状态素材") { rules }
                        observationHint
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
            } else {
                HStack { settings; Spacer(); actions }
                currentState
                captureError
                performance
                HStack(alignment: .top) { evidence; history.frame(width: 280) }
                GroupBox("已登记的状态素材") { rules }
                observationHint
            }
        }.padding(compact ? 0 : 14)
    }

    private var settings: some View {
        HStack {
            Picker("检测频率", selection: $session.observation.hz) {
                Text("每秒 1 次").tag(1)
                Text("每秒 2 次").tag(2)
                Text("每秒 5 次").tag(5)
            }.frame(width: compact ? 190 : 200)
            Toggle("连续两次确认", isOn: $session.observation.confirm).toggleStyle(.checkbox)
        }.disabled(!session.canOperate)
    }

    private var actions: some View {
        HStack {
            Button("开始观察", action: session.startObservation)
                .disabled(!session.canOperate || session.preparation.selectedWindow.isEmpty)
            Button("停止观察", action: session.stopObservation)
                .disabled(!session.observation.running || session.phase != .ready)
        }
    }

    private var currentState: some View {
        GroupBox("当前状态") {
            VStack(alignment: .leading, spacing: 8) {
                Text(session.observation.state).font(.system(size: compact ? 28 : 30, weight: .semibold))
                    .fixedSize(horizontal: false, vertical: true)
                Text(session.observation.phase).foregroundStyle(.secondary)
                Text("本帧候选：" + session.observation.candidate).foregroundStyle(.secondary)
                Text(session.observation.metrics).font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }.frame(maxWidth: .infinity, alignment: .leading).padding(8)
        }
    }

    @ViewBuilder private var captureError: some View {
        if !session.observation.error.isEmpty {
            Label(session.observation.error, systemImage: "exclamationmark.triangle")
                .foregroundStyle(.orange).font(.callout).textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var performance: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(session.observation.performanceSummary).font(.caption).foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            DisclosureGroup("性能") {
                Text(session.observation.performanceDetails).font(.caption).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var evidence: some View {
        GroupBox("匹配证据 · 窗口相对坐标") {
            ScrollView { evidenceText(session.observation.evidence) }
                .frame(minHeight: compact ? 100 : 140, maxHeight: compact ? 170 : .infinity)
        }
    }

    private var history: some View {
        GroupBox("状态变化") {
            ScrollView { evidenceText(session.observation.history) }
                .frame(minHeight: compact ? 80 : 140, maxHeight: compact ? 140 : .infinity)
        }
    }

    private var rules: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("在素材准备页登记状态。").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("重新加载", action: session.reloadObservationRules).disabled(!session.canOperate)
            }
            ScrollView { evidenceText(session.observation.ruleSummary) }.frame(height: 65)
        }
    }

    private func evidenceText(_ text: String) -> some View {
        Text(text).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading).fixedSize(horizontal: false, vertical: true)
    }

    private var observationHint: some View {
        Text("仅采集所选窗口，不执行操作。窗口关闭、尺寸变化或截图失败时，状态会失效。")
            .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
    }
}
