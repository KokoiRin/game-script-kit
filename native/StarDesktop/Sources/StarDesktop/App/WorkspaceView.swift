import AppKit
import SwiftUI

struct WorkspaceView: View {
    @ObservedObject var session: DesktopSession
    @State var tab = "observe"
    @State var floating = true
    let chooseWorkspace: () -> Void
    let changeCompactLayout: (Bool) -> Void
    let changeFloating: (Bool) -> Void

    private var compact: Bool { usesCompactLayout(for: tab) }

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 10 : 16) {
            HStack {
                Label("Star", systemImage: "sparkle").font(.title2.bold())
                Spacer()
                Text((compact ? session.workspace?.lastPathComponent : session.workspace?.path) ?? "尚未选择工作区").foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle).help(session.workspace?.path ?? "请选择任务工作区")
                Button("选择工作区…", action: chooseWorkspace)
                    .disabled(!session.canSwitchWorkspace)
            }
            HStack {
                Picker("页面", selection: $tab) {
                    Text("素材准备").tag("prepare")
                    Text("实时识别").tag("observe")
                    Text("脚本运行").tag("run")
                }.pickerStyle(.segmented).labelsHidden()
                Spacer()
                Toggle("置顶", isOn: $floating).toggleStyle(.checkbox)
                    .onChange(of: floating) { changeFloating($0) }
            }
            permissions
            Group {
                switch tab {
                case "run": ExecutionView(session: session, compact: compact)
                case "observe": ObservationView(session: session, compact: true)
                default: PreparationView(session: session)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .onChange(of: compact) { changeCompactLayout($0) }
            .onChange(of: tab) { value in
                if value == "run" && session.execution.scripts.isEmpty && session.canOperate { session.reloadScripts() }
                if value == "observe" && session.canOperate { session.reloadObservationRules() }
            }
            .onChange(of: session.phase) { value in
                if value == .ready && session.canOperate {
                    if tab == "run" { session.reloadScripts() }
                    if tab == "observe" { session.reloadObservationRules() }
                }
            }
            HStack {
                if session.showsProgress {
                    ProgressView().controlSize(.small)
                }
                Text(session.status).font(.callout).foregroundStyle(.secondary)
                    .lineLimit(compact ? 2 : nil).help(session.status)
                Spacer()
                if session.observation.running {
                    Button("停止识别", action: session.stopObservation).disabled(!session.canStopObservation)
                }
                if session.execution.isRunning {
                    Button(session.execution.runPhase == .stopping ? "正在停止" : "停止脚本", action: session.stopScript)
                        .disabled(!session.canStopScript)
                }
                if session.execution.runPhase == .stopping || session.phase == .failed {
                    Button("重启后台", action: session.restartBackend).disabled(!session.canRestartBackend)
                }
            }
            if !session.errorMessage.isEmpty {
                Label(session.errorMessage, systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.orange).textSelection(.enabled).font(.callout)
                    .fixedSize(horizontal: false, vertical: true)
            }
            DisclosureGroup("诊断") {
                ScrollView { Text(session.diagnostics.isEmpty ? "暂无后台诊断。" : session.diagnostics)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                    .frame(height: 90)
            }.font(.caption)
        }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            session.refreshPermissions()
        }
        .padding(compact ? 12 : 20)
        .frame(minWidth: compact ? 440 : 980, minHeight: compact ? 580 : 720)
    }

    @ViewBuilder private var permissions: some View {
        if compact && session.permissions.allGranted {
            HStack {
                Label("窗口与截图已授权", systemImage: "checkmark.circle").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("检测", action: session.refreshPermissions)
                    .disabled(!session.canCheckPermissions)
            }
        } else {
            GroupBox("系统权限") {
                VStack(alignment: .leading, spacing: 8) {
                    permissionControls
                    if !session.permissions.accessibilityAllowed || !session.permissions.screenRecordingAllowed {
                        Text("读取窗口需要窗口控制，截取画面需要录屏权限。请按系统提示为 Star 授权。")
                            .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                        HStack {
                            Button("打开隐私设置", action: session.openPrivacySettings)
                            Button("重启后台", action: session.restartBackend).disabled(!session.canRestartBackend)
                        }
                    }
                }.padding(4)
            }
        }
    }

    @ViewBuilder private var permissionControls: some View {
        if compact {
            VStack(alignment: .leading, spacing: 8) {
                accessibilityControl
                screenRecordingControl
                Button("重新检测", action: session.refreshPermissions)
            }.disabled(!session.canCheckPermissions)
        } else {
            HStack {
                accessibilityControl
                Spacer()
                screenRecordingControl
                Spacer()
                Button("重新检测", action: session.refreshPermissions)
            }.disabled(!session.canCheckPermissions)
        }
    }

    private var accessibilityControl: some View {
        HStack {
            Label("窗口控制：" + permissionLabel(session.permissions.accessibilityAllowed),
                  systemImage: session.permissions.accessibilityAllowed ? "checkmark.circle" : "lock")
            if !session.permissions.accessibilityAllowed {
                Button("申请窗口控制") { session.requestPermission("accessibility") }
            }
        }
    }

    private var screenRecordingControl: some View {
        HStack {
            Label("屏幕截图：" + permissionLabel(session.permissions.screenRecordingAllowed),
                  systemImage: session.permissions.screenRecordingAllowed ? "checkmark.circle" : "lock")
            if !session.permissions.screenRecordingAllowed {
                Button("申请屏幕截图") { session.requestPermission("screen_recording") }
            }
        }
    }

    private func permissionLabel(_ allowed: Bool) -> String {
        session.permissions.known ? (allowed ? "已授权" : "未授权") : "待检测"
    }
}
