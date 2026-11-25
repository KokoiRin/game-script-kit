import SwiftUI

struct ExecutionView: View {
    @ObservedObject var session: DesktopSession
    let compact: Bool
    @State private var selectedPlanEntry: UUID?
    @State private var runLogExpanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle("编排列表", isOn: $session.execution.useSavedPlan)
                .onChange(of: session.execution.useSavedPlan) { _ in session.describeScript() }
                .disabled(!session.canOperate)
            if session.execution.useSavedPlan {
                planEditor
            } else {
                HStack {
                    Picker("脚本", selection: $session.execution.selectedScript) {
                        Text("请选择脚本").tag("")
                        ForEach(session.execution.scripts, id: \.self) { Text($0).tag($0) }
                    }.onChange(of: session.execution.selectedScript) { _ in session.describeScript() }
                    Button("重新加载", action: session.reloadScripts)
                }
                .disabled(!session.canOperate)
            }
            HStack {
                Toggle("模拟运行", isOn: $session.execution.dryRun).toggleStyle(.checkbox)
                Spacer()
                Button("运行", action: session.startScript)
                    .disabled(!session.canOperate || (session.execution.useSavedPlan ? session.execution.planEntries.isEmpty : session.execution.selectedScript.isEmpty))
            }.disabled(!session.canOperate)
            if session.execution.dryRun {
                HStack {
                    TextField("模拟颜色 #000000", text: $session.execution.dryRunColor)
                    TextField("模拟状态", text: $session.execution.dryRunState)
                }.disabled(!session.canOperate)
            } else {
                Text("真实运行会控制当前桌面；当前点位和状态区域仍按脚本及运行配置解析。")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if !session.execution.useSavedPlan {
                GroupBox("入口与依赖") {
                    ScrollView {
                        Text(session.execution.scriptDetails.isEmpty ? "读取脚本后显示入口和依赖。" : session.execution.scriptDetails)
                            .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading).fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(height: 150)
                }
            }
            DisclosureGroup(isExpanded: $runLogExpanded) {
                ScrollView {
                    Text(session.execution.runLog.isEmpty ? "暂无运行记录。" : session.execution.runLog)
                        .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading).fixedSize(horizontal: false, vertical: true)
                }
                .frame(minHeight: 80, idealHeight: 160, maxHeight: 200)
            } label: {
                HStack {
                    Text("运行记录")
                    Spacer()
                    Button("打开记录文件夹", action: session.openRunRecords).font(.caption)
                }
            }
        }.padding(compact ? 0 : 14)
    }

    private var planEditor: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                TextField("流程名称", text: $session.execution.savedPlanName)
                Button("保存", action: session.savePlan).disabled(session.execution.planEntries.isEmpty)
                Button("重新加载", action: session.reloadScripts)
            }
            HStack(alignment: .top, spacing: 8) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("全部脚本").font(.caption).foregroundStyle(.secondary)
                    List(session.execution.scripts, id: \.self, selection: scriptSelection) { name in
                        Text(name).lineLimit(1).truncationMode(.middle).help(name)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .contentShape(Rectangle())
                            .simultaneousGesture(TapGesture(count: 2).onEnded {
                                guard session.canOperate else { return }
                                session.execution.selectedScript = name
                                session.addPlanEntry()
                                selectedPlanEntry = session.execution.planEntries.last?.id
                            })
                            .tag(name)
                    }
                    .listStyle(.plain)
                    .border(Color.secondary.opacity(0.2))
                    Button("添加到右侧") {
                        session.addPlanEntry()
                        selectedPlanEntry = session.execution.planEntries.last?.id
                    }.disabled(session.execution.selectedScript.isEmpty)
                }.frame(maxWidth: .infinity)
                VStack(alignment: .leading, spacing: 6) {
                    Text("执行顺序").font(.caption).foregroundStyle(.secondary)
                    List(session.execution.planEntries, selection: $selectedPlanEntry) { entry in
                        Text(entry.name).lineLimit(1).truncationMode(.middle).help(entry.name)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .contentShape(Rectangle())
                            .simultaneousGesture(TapGesture(count: 2).onEnded {
                                guard session.canOperate else { return }
                                session.removePlanEntry(entry.id)
                                if selectedPlanEntry == entry.id { selectedPlanEntry = nil }
                            })
                            .tag(entry.id)
                    }
                    .listStyle(.plain)
                    .border(Color.secondary.opacity(0.2))
                    HStack(spacing: 8) {
                        Button {
                            if let id = selectedPlanEntry { session.movePlanEntry(id, by: -1) }
                        } label: { Image(systemName: "arrow.up") }
                        .accessibilityLabel("上移任务")
                        .disabled(selectedPlanIndex == nil || selectedPlanIndex == 0)
                        Button {
                            if let id = selectedPlanEntry { session.movePlanEntry(id, by: 1) }
                        } label: { Image(systemName: "arrow.down") }
                        .accessibilityLabel("下移任务")
                        .disabled(selectedPlanIndex == nil || selectedPlanIndex == session.execution.planEntries.count - 1)
                        Button {
                            if let id = selectedPlanEntry { session.removePlanEntry(id) }
                            selectedPlanEntry = nil
                        } label: { Image(systemName: "minus") }
                        .accessibilityLabel("移除任务")
                        .disabled(selectedPlanIndex == nil)
                        Spacer(minLength: 0)
                    }
                }.frame(maxWidth: .infinity)
            }.frame(minHeight: 130, maxHeight: .infinity)
            HStack(spacing: 5) {
                Spacer()
                Text("完成后等待").foregroundStyle(.secondary)
                TextField("秒数", text: selectedPlanWait).frame(width: 65)
                    .textFieldStyle(.roundedBorder).accessibilityLabel("选中任务完成后等待秒数")
                Text("秒").foregroundStyle(.secondary)
            }
            .font(.caption)
            .disabled(selectedPlanIndex == nil)
        }
        .disabled(!session.canOperate)
    }

    private var scriptSelection: Binding<String?> {
        Binding(
            get: { session.execution.selectedScript.isEmpty ? nil : session.execution.selectedScript },
            set: { value in
                session.execution.selectedScript = value ?? ""
                session.describeScript()
            }
        )
    }

    private var selectedPlanIndex: Int? {
        session.execution.planEntries.firstIndex { $0.id == selectedPlanEntry }
    }

    private var selectedPlanWait: Binding<String> {
        Binding(
            get: {
                guard let index = selectedPlanIndex else { return "" }
                return session.execution.planEntries[index].waitSeconds
            },
            set: { value in
                if let index = selectedPlanIndex {
                    session.execution.planEntries[index].waitSeconds = value
                }
            }
        )
    }
}
