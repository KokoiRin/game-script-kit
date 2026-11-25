import AppKit
import Foundation

struct WindowChoice: Identifiable {
    let id: String
    let title: String
}

struct FrozenFrame {
    let id: String
    let title: String
    let width: Int
    let height: Int
    let image: NSImage
}

struct PreparationState {
    var application = ""
    var windows: [WindowChoice] = []
    var selectedWindow = ""
    var frame: FrozenFrame?
    var selection: PixelRegion?
    var targetName = ""
    var resourceText = ""
    var stateName = ""
    var stateConfidence = "0.90"
    var searchRegion: PixelRegion?

    mutating func clearFrame() {
        frame = nil
        selection = nil
        searchRegion = nil
        resourceText = ""
    }

    mutating func resetWindows() {
        windows = []
        selectedWindow = ""
        clearFrame()
    }
}

extension DesktopSession {
    func clearFrame() {
        frameGeneration = UUID()
        preparation.clearFrame()
    }

    func readWindows() {
        guard requirePermission("accessibility") else { return }
        frameGeneration = UUID()
        preparation.resetWindows()
        perform("preparation.windows", ["application": preparation.application]) { [weak self] result in
            guard let self else { return }
            self.preparation.windows = (result["windows"] as? [Object] ?? []).compactMap { value in
                guard let id = value["id"] as? String, let title = value["title"] as? String else { return nil }
                return WindowChoice(id: id, title: title)
            }
            self.preparation.selectedWindow = self.preparation.windows.first?.id ?? ""
            self.status = self.preparation.windows.isEmpty ? "没有可用窗口，请检查应用名、窗口与辅助功能权限。" : "选择目标窗口后截取画面。"
        }
    }

    func capture() {
        guard requirePermission("accessibility"), requirePermission("screen_recording") else { return }
        clearFrame()
        let generation = frameGeneration
        perform("preparation.capture", ["application": preparation.application, "window_id": preparation.selectedWindow]) { [weak self] result in
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
                        self.preparation.frame = FrozenFrame(id: id, title: title, width: width, height: height, image: preview)
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
        guard let frame = preparation.frame else { return }
        preparation.selection = nil
        perform("preparation.point", ["frame_id": frame.id, "x": Int(point.x), "y": Int(point.y)]) { [weak self] result in
            guard let self else { return }
            let name = self.preparation.targetName.isEmpty ? "目标" : self.preparation.targetName
            self.preparation.resourceText = prettyJSON(["resources": ["points": [name: result["window_relative"] ?? [:]]], "screen": result["screen"] ?? [:]])
        }
    }

    func saveCrop() {
        guard let frame = preparation.frame, let selection = preparation.selection else { return }
        perform("preparation.crop", ["frame_id": frame.id, "region": selection.payload, "name": preparation.targetName]) { [weak self] result in
            guard let self else { return }
            self.preparation.resourceText = prettyJSON(["resources": result["resources"] ?? [:]])
            self.status = "已保存 assets/\(result["image"] as? String ?? "")"
        }
    }

    func useSelectionAsSearchRegion() {
        guard canOperate, let selection = preparation.selection else { return }
        preparation.searchRegion = selection
    }

    func saveStateMaterial() {
        guard let frame = preparation.frame, let selection = preparation.selection,
              let threshold = Double(preparation.stateConfidence), threshold.isFinite else {
            errorMessage = "请框选素材并填写有效的匹配阈值。"
            return
        }
        var params: Object = ["frame_id": frame.id, "region": selection.payload, "name": preparation.targetName,
                              "state": preparation.stateName, "min_confidence": threshold]
        if let searchRegion = preparation.searchRegion { params["search_region"] = searchRegion.payload }
        perform("observation.rule.save", params) { [weak self] result in
            self?.renderObservationRules(result)
            self?.status = "状态素材已保存，可进入实时识别页开始观察。"
        }
    }
}
