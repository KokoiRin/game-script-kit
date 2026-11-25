import AppKit
import SwiftUI

struct PreparationView: View {
    @ObservedObject var session: DesktopSession

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            TargetWindowPicker(session: session, showCapture: true)
            Text(session.preparation.frame.map { "\($0.title) · \($0.width) × \($0.height) 像素 · 点击取点，拖动框选" } ?? "选窗后截取一帧画面，准备点位和模板。")
                .font(.caption).foregroundStyle(.secondary)
            ScreenshotCanvas(frame: session.preparation.frame, enabled: session.canOperate,
                             onPoint: session.point, onRegion: { session.preparation.selection = $0 })
                .frame(minHeight: 260, maxHeight: .infinity)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
            HStack {
                TextField("目标名称，例如 任务入口", text: $session.preparation.targetName)
                if let selection = session.preparation.selection {
                    Text("\(selection.width) × \(selection.height) 像素").font(.caption).foregroundStyle(.secondary)
                }
                Button("保存模板", action: session.saveCrop)
                    .disabled(!session.canOperate || session.preparation.selection == nil || session.preparation.targetName.isEmpty)
                Button("复制资源") {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(session.preparation.resourceText, forType: .string)
                }
                .disabled(session.preparation.resourceText.isEmpty)
            }
            GroupBox("登记状态素材") {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        TextField("该素材代表的状态，例如 对话框", text: $session.preparation.stateName)
                        TextField("匹配阈值", text: $session.preparation.stateConfidence).frame(width: 90)
                        Button("保存状态素材", action: session.saveStateMaterial)
                            .disabled(!session.canOperate || session.preparation.selection == nil || session.preparation.targetName.isEmpty || session.preparation.stateName.isEmpty)
                    }
                    HStack {
                        Text(session.preparation.searchRegion.map { "搜索范围：\($0.width) × \($0.height) 像素" } ?? "搜索范围：整个游戏窗口")
                            .font(.caption).foregroundStyle(.secondary)
                        Button("将框选设为搜索范围", action: session.useSelectionAsSearchRegion)
                            .disabled(!session.canOperate || session.preparation.selection == nil)
                        Button("使用整个窗口") { session.preparation.searchRegion = nil }.disabled(!session.canOperate)
                    }
                    Text("可先框选较大的搜索范围，再框选小素材。保存后到实时识别页开始观察。")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(4)
            }
            Text("点位以窗口左上角为原点，运行时仍需绑定目标窗口。模板保存到当前工作区 assets，重名不覆盖。")
                .font(.caption).foregroundStyle(.secondary)
            ScrollView {
                Text(session.preparation.resourceText.isEmpty ? "取点或保存模板后，这里显示脚本资源。" : session.preparation.resourceText)
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(height: 100).padding(10).background(Color.secondary.opacity(0.08)).clipShape(RoundedRectangle(cornerRadius: 6))
        }.padding(14)
    }
}
