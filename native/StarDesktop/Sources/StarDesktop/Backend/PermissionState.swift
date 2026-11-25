import AppKit
import Foundation

struct PermissionState {
    var known = false
    var accessibilityAllowed = false
    var screenRecordingAllowed = false
    var checking = false

    var allGranted: Bool { known && accessibilityAllowed && screenRecordingAllowed }

    mutating func resetForStart() {
        known = false
        checking = false
    }
}

extension DesktopSession {
    var canCheckPermissions: Bool { canOperate && !permissions.checking }

    // 权限由实际执行后台查询，界面不以自身授权代替子进程授权。
    func refreshPermissions() {
        guard canCheckPermissions else { return }
        permissions.checking = true
        call("permissions.status") { [weak self] reply in
            guard let self else { return }
            self.permissions.checking = false
            switch reply {
            case .success(let value): self.renderPermissions(value)
            case .failure(let error): self.errorMessage = "权限检测失败：\(error.localizedDescription)"
            }
        }
    }

    func requestPermission(_ kind: String) {
        guard canCheckPermissions else { return }
        busy = true; errorMessage = ""
        status = "请按 macOS 提示确认权限，完成后返回 Star。"
        // 截图权限提示可能等待用户选择，不能套用普通操作的短超时。
        call("permissions.request", ["kind": kind], timeoutSeconds: 120) { [weak self] reply in
            guard let self else { return }
            self.busy = false
            switch reply {
            case .success(let value):
                self.renderPermissions(value)
                self.status = "权限申请已发出。请在系统设置中确认，然后重新检测；必要时重启后台。"
            case .failure(let error): self.errorMessage = "权限申请失败：\(error.localizedDescription)"
            }
        }
    }

    func openPrivacySettings() {
        guard let url = URL(string: "x-apple.systempreferences:com.apple.preference.security") else { return }
        NSWorkspace.shared.open(url)
    }

    func renderPermissions(_ value: Object) {
        guard let accessibility = value["accessibility"] as? Bool,
              let screenRecording = value["screen_recording"] as? Bool else {
            errorMessage = "后台返回了无效的权限状态。"
            return
        }
        permissions.accessibilityAllowed = accessibility
        permissions.screenRecordingAllowed = screenRecording
        permissions.known = true
    }

    func requirePermission(_ kind: String) -> Bool {
        let allowed = kind == "accessibility" ? permissions.accessibilityAllowed : permissions.screenRecordingAllowed
        guard permissions.known, allowed else {
            errorMessage = kind == "accessibility"
                ? "需要窗口控制权限，请点击上方“申请窗口控制”。"
                : "需要屏幕截图权限，请点击上方“申请屏幕截图”。"
            refreshPermissions()
            return false
        }
        return true
    }
}
