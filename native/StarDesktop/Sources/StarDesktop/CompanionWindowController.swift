import AppKit

final class CompanionConsoleWindow: NSWindow {
    var followsTarget = false

    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        followsTarget ? frameRect : super.constrainFrameRect(frameRect, to: screen)
    }
}

@MainActor
final class CompanionWindowController {
    private weak var window: CompanionConsoleWindow?
    private var target: CompanionTarget?
    private var timer: Timer?
    private var activationObserver: NSObjectProtocol?
    private var mouseMonitor: Any?
    private var visibility = CompanionVisibility()

    init(window: CompanionConsoleWindow) {
        self.window = window
    }

    func bind(_ target: CompanionTarget?) {
        guard self.target != target else { return }
        stop()
        self.target = target
        window?.followsTarget = target != nil
        guard target != nil else { return }
        activationObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
        mouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: .leftMouseDown) { [weak self] _ in
            Task { @MainActor in self?.refresh(clicked: true) }
        }
        let timer = Timer(timeInterval: 0.08, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
        self.timer = timer
        RunLoop.main.add(timer, forMode: .common)
        refresh()
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        if let activationObserver {
            NSWorkspace.shared.notificationCenter.removeObserver(activationObserver)
        }
        activationObserver = nil
        if let mouseMonitor { NSEvent.removeMonitor(mouseMonitor) }
        mouseMonitor = nil
        target = nil
        visibility = CompanionVisibility()
        window?.followsTarget = false
    }

    func refresh(clicked: Bool = false) {
        guard let window, let target,
              let rows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]],
              let row = rows.first(where: {
                  ($0[kCGWindowNumber as String] as? UInt32) == target.windowNumber &&
                  ($0[kCGWindowOwnerPID as String] as? Int32) == target.pid
              }),
              let bounds = row[kCGWindowBounds as String] as? NSDictionary,
              let rect = CGRect(dictionaryRepresentation: bounds),
              let desktopTop = NSScreen.screens.first?.frame.maxY else {
            visibility = CompanionVisibility()
            return
        }
        let frame = companionFrame(target: rect, consoleSize: window.frame.size, desktopTop: desktopTop)
        if window.frame != frame { window.setFrame(frame, display: true) }
        let frontPID = NSWorkspace.shared.frontmostApplication?.processIdentifier
        let frontWindow = rows.first {
            ($0[kCGWindowOwnerPID as String] as? Int32) == frontPID &&
            ($0[kCGWindowLayer as String] as? Int) == 0
        }
        let targetIsFront = frontPID == target.pid &&
            (frontWindow?[kCGWindowNumber as String] as? UInt32) == target.windowNumber
        let cursor = NSEvent.mouseLocation
        let inside = rect.contains(CGPoint(x: cursor.x, y: desktopTop - cursor.y))
        let reveal = visibility.shouldReveal(targetIsFront: targetIsFront,
                                             mouseDown: NSEvent.pressedMouseButtons & 1 != 0,
                                             clickInsideTarget: inside)
        if reveal || (clicked && targetIsFront && inside) {
            let previous = NSWorkspace.shared.frontmostApplication
            NSApp.unhideWithoutActivation()
            if window.isMiniaturized { window.deminiaturize(nil) }
            window.orderFrontRegardless()
            // 取消最小化在部分系统上会激活所属应用，恢复之前的输入接收者。
            if NSWorkspace.shared.frontmostApplication?.processIdentifier != previous?.processIdentifier {
                previous?.activate(options: [])
            }
        }
    }
}
