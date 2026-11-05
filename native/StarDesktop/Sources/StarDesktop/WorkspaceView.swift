import AppKit
import SwiftUI

struct WorkspaceView: View {
    @ObservedObject var session: DesktopSession
    @State var tab = "prepare"
    let chooseWorkspace: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Label("Star", systemImage: "sparkle").font(.title2.bold())
                Spacer()
                Text(session.workspace?.path ?? "尚未选择工作区").foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)
                Button("选择工作区…", action: chooseWorkspace)
                    .disabled(session.busy || session.runRunning || session.phase == .starting || session.phase == .stopping)
            }
            TabView(selection: $tab) {
                preparation.tabItem { Label("素材准备", systemImage: "viewfinder") }.tag("prepare")
                execution.tabItem { Label("脚本运行", systemImage: "play.circle") }.tag("run")
            }
            .onChange(of: tab) { value in
                if value == "run" && session.scripts.isEmpty && session.canOperate { session.reloadScripts() }
            }
            HStack {
                if session.busy || session.phase == .starting || session.phase == .stopping {
                    ProgressView().controlSize(.small)
                }
                Text(session.status).font(.callout).foregroundStyle(.secondary)
                Spacer()
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
            }
            DisclosureGroup("诊断") {
                ScrollView { Text(session.diagnostics.isEmpty ? "暂无后台诊断。" : session.diagnostics)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                    .frame(height: 90)
            }.font(.caption)
        }
        .padding(20)
        .frame(minWidth: 980, minHeight: 720)
    }

    private var preparation: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                TextField("目标应用，例如 Safari 或游戏应用名", text: $session.application)
                    .onChange(of: session.application) { _ in session.windows = []; session.selectedWindow = ""; session.clearFrame() }
                Button("读取窗口", action: session.readWindows).disabled(!session.canOperate || session.application.isEmpty)
                Picker("窗口", selection: $session.selectedWindow) {
                    Text("请选择窗口").tag("")
                    ForEach(session.windows) { Text($0.title).tag($0.id) }
                }.frame(minWidth: 200)
                    .onChange(of: session.selectedWindow) { _ in session.clearFrame() }
                Button("截取画面", action: session.capture).disabled(!session.canOperate || session.selectedWindow.isEmpty)
            }.disabled(session.busy || session.runRunning || session.phase != .ready)
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
