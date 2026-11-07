import AppKit
import SwiftUI

struct WorkspaceView: View {
    @ObservedObject var session: DesktopSession
    @State var tab = "observe"
    @State var compact = true
    @State var floating = true
    let chooseWorkspace: () -> Void
    let changeObservationMode: (Bool) -> Void
    let changeFloating: (Bool) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 10 : 16) {
            HStack {
                Label("Star", systemImage: "sparkle").font(.title2.bold())
                Spacer()
                Text((compact ? session.workspace?.lastPathComponent : session.workspace?.path) ?? "尚未选择工作区").foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle).help(session.workspace?.path ?? "请选择任务工作区")
                Button("选择工作区…", action: chooseWorkspace)
                    .disabled(session.busy || session.runRunning || session.observationRunning || session.phase == .starting || session.phase == .stopping)
            }
            HStack {
                Button(compact ? "展开准备" : "并排观察") {
                    compact.toggle()
                    tab = compact ? "observe" : "prepare"
                    floating = compact
                    changeObservationMode(compact)
                    changeFloating(floating)
                    if compact && session.canOperate { session.reloadObservationRules() }
                }
                Spacer()
                Toggle("置顶", isOn: $floating).toggleStyle(.checkbox)
                    .onChange(of: floating) { changeFloating($0) }
            }
            permissions
            Group {
                if compact {
                    ObservationView(session: session, compact: true)
                } else {
                    TabView(selection: $tab) {
                        preparation.tabItem { Label("素材准备", systemImage: "viewfinder") }.tag("prepare")
                        ObservationView(session: session).tabItem { Label("实时识别", systemImage: "eye") }.tag("observe")
                        execution.tabItem { Label("脚本运行", systemImage: "play.circle") }.tag("run")
                    }
                }
            }
            .onChange(of: tab) { value in
                if value == "run" && session.scripts.isEmpty && session.canOperate { session.reloadScripts() }
                if value == "observe" && session.canOperate { session.reloadObservationRules() }
            }
            .onChange(of: session.phase) { value in
                if value == .ready && session.canOperate {
                    if tab == "run" { session.reloadScripts() }
                    if tab == "observe" { session.reloadObservationRules() }
                }
            }
            HStack {
                if session.busy || session.phase == .starting || session.phase == .stopping {
                    ProgressView().controlSize(.small)
                }
                Text(session.status).font(.callout).foregroundStyle(.secondary)
                    .lineLimit(compact ? 2 : nil).help(session.status)
                Spacer()
                if session.observationRunning {
                    Button("停止识别", action: session.stopObservation).disabled(session.phase != .ready)
                }
                if session.runRunning {
                    Button("停止脚本", action: session.stopScript).disabled(session.busy || session.phase != .ready)
                }
                if session.phase == .failed && !session.processRunning {
                    Button("重启后台", action: session.restart)
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
        if compact && session.permissionsKnown && session.accessibilityAllowed && session.screenRecordingAllowed {
            HStack {
                Label("窗口与截图已授权", systemImage: "checkmark.circle").font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("检测", action: session.refreshPermissions)
                    .disabled(!session.canOperate || session.checkingPermissions)
            }
        } else {
            GroupBox("系统权限") {
                VStack(alignment: .leading, spacing: 8) {
                    permissionControls
                    if !session.accessibilityAllowed || !session.screenRecordingAllowed {
                        Text("读取窗口需要窗口控制，截取画面需要录屏权限。请按系统提示为 Star 授权。")
                            .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                        HStack {
                            Button("打开隐私设置", action: session.openPrivacySettings)
                            Button("重启后台", action: session.restartBackend).disabled(!session.canOperate)
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
                Button("重新检测", action: session.refreshPermissions).disabled(session.checkingPermissions)
            }.disabled(!session.canOperate)
        } else {
            HStack {
                accessibilityControl
                Spacer()
                screenRecordingControl
                Spacer()
                Button("重新检测", action: session.refreshPermissions).disabled(session.checkingPermissions)
            }.disabled(!session.canOperate)
        }
    }

    private var accessibilityControl: some View {
        HStack {
            Label("窗口控制：" + permissionLabel(session.accessibilityAllowed),
                  systemImage: session.accessibilityAllowed ? "checkmark.circle" : "lock")
            if !session.accessibilityAllowed {
                Button("申请窗口控制") { session.requestPermission("accessibility") }
            }
        }
    }

    private var screenRecordingControl: some View {
        HStack {
            Label("屏幕截图：" + permissionLabel(session.screenRecordingAllowed),
                  systemImage: session.screenRecordingAllowed ? "checkmark.circle" : "lock")
            if !session.screenRecordingAllowed {
                Button("申请屏幕截图") { session.requestPermission("screen_recording") }
            }
        }
    }

    private func permissionLabel(_ allowed: Bool) -> String {
        session.permissionsKnown ? (allowed ? "已授权" : "未授权") : "待检测"
    }

    private var preparation: some View {
        VStack(alignment: .leading, spacing: 12) {
            TargetWindowPicker(session: session, showCapture: true)
            Text(session.frame.map { "\($0.title) · \($0.width) × \($0.height) 像素 · 点击取点，拖动框选" } ?? "选窗后截取一帧画面，准备点位和模板。")
                .font(.caption).foregroundStyle(.secondary)
            ScreenshotCanvas(frame: session.frame, enabled: session.canOperate,
                             onPoint: session.point, onRegion: { session.selection = $0 })
                .frame(minHeight: 260, maxHeight: .infinity)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
            HStack {
                TextField("目标名称，例如 任务入口", text: $session.targetName)
                if let selection = session.selection { Text("\(selection.width) × \(selection.height) 像素").font(.caption).foregroundStyle(.secondary) }
                Button("保存模板", action: session.saveCrop)
                    .disabled(!session.canOperate || session.selection == nil || session.targetName.isEmpty)
                Button("复制资源") { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(session.resourceText, forType: .string) }
                    .disabled(session.resourceText.isEmpty)
            }
            GroupBox("登记状态素材") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        TextField("该素材代表的状态，例如 对话框", text: $session.stateName)
                        TextField("匹配阈值", text: $session.stateConfidence).frame(width: 90)
                        Button("保存状态素材", action: session.saveStateMaterial)
                            .disabled(!session.canOperate || session.selection == nil || session.targetName.isEmpty || session.stateName.isEmpty)
                    }
                    HStack {
                        Text(session.searchRegion.map { "搜索范围：\($0.width) × \($0.height) 像素" } ?? "搜索范围：整个游戏窗口")
                            .font(.caption).foregroundStyle(.secondary)
                        Button("将框选设为搜索范围", action: session.useSelectionAsSearchRegion)
                            .disabled(!session.canOperate || session.selection == nil)
                        Button("使用整个窗口") { session.searchRegion = nil }.disabled(!session.canOperate)
                    }
                    Text("可先框选较大的搜索范围，再框选小素材。保存后到实时识别页开始观察。")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(4)
            }
            Text("点位以窗口左上角为原点，运行时仍需绑定目标窗口。模板保存到当前工作区 assets，重名不覆盖。")
                .font(.caption).foregroundStyle(.secondary)
            ScrollView { Text(session.resourceText.isEmpty ? "取点或保存模板后，这里显示脚本资源。" : session.resourceText)
                .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                .frame(height: 100).padding(10).background(Color.secondary.opacity(0.08)).clipShape(RoundedRectangle(cornerRadius: 6))
        }.padding(14)
    }

    private var execution: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Picker("脚本", selection: $session.selectedScript) {
                    Text("请选择脚本").tag("")
                    ForEach(session.scripts, id: \.self) { Text($0).tag($0) }
                }.onChange(of: session.selectedScript) { _ in session.describeScript() }
                Button("重新加载", action: session.reloadScripts).disabled(!session.canOperate)
                Toggle("模拟运行", isOn: $session.dryRun).toggleStyle(.checkbox)
                Button("运行", action: session.startScript).disabled(!session.canOperate || session.selectedScript.isEmpty)
            }.disabled(session.busy || session.runRunning || session.phase != .ready)
            if session.dryRun {
                HStack {
                    TextField("模拟颜色 #000000", text: $session.dryRunColor)
                    TextField("模拟状态", text: $session.dryRunState)
                }.disabled(!session.canOperate)
            } else {
                Text("真实运行会控制当前桌面；当前点位和状态区域仍按脚本及运行配置解析。")
                    .font(.caption).foregroundStyle(.secondary)
            }
            GroupBox("步骤与依赖") {
                ScrollView { Text(session.scriptDetails.isEmpty ? "读取脚本后显示步骤和依赖。" : session.scriptDetails)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                    .frame(height: 150)
            }
            GroupBox("运行记录") {
                ScrollView { Text(session.runLog.isEmpty ? "暂无运行记录。" : session.runLog)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                    .frame(maxHeight: .infinity)
            }
        }.padding(14)
    }
}
