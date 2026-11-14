import AppKit
import SwiftUI
import Darwin

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private let session = DesktopSession()
    private var window: NSWindow?
    private var terminating = false
    private var sourceRoot: URL?
    private var python: URL?
    private var signalSources: [DispatchSourceSignal] = []
    private var wideFrame: CGRect?

    func applicationDidFinishLaunching(_ notification: Notification) {
        Darwin.signal(SIGPIPE, SIG_IGN)
        sourceRoot = configuredURL("STAR_SOURCE_ROOT", bundleKey: "StarSourceRoot") ?? developmentRoot()
        python = configuredURL("STAR_PYTHON", bundleKey: "StarPython") ?? sourceRoot?.appendingPathComponent(".venv/bin/python")
        let initialTab = argument("--tab") ?? "observe"
        let compact = usesCompactLayout(for: initialTab)
        let floating = initialTab == "observe"
        let view = WorkspaceView(session: session, tab: initialTab, floating: floating,
                                 chooseWorkspace: { [weak self] in self?.chooseWorkspace() },
                                 changeCompactLayout: { [weak self] in self?.setCompactLayout($0) },
                                 changeFloating: { [weak self] floating in self?.window?.level = floating ? .floating : .normal })
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1100, height: 850),
                              styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Star"
        window.isReleasedWhenClosed = false
        window.delegate = self
        window.contentView = NSHostingView(rootView: view)
        window.setFrameAutosaveName("StarMainWindow")
        if !window.setFrameUsingName("StarMainWindow") { window.center() }
        self.window = window
        if let screen = window.screen ?? NSScreen.main {
            let visible = screen.visibleFrame
            wideFrame = windowFrame(CGRect(x: visible.midX - 550, y: visible.midY - 425,
                                           width: 1100, height: 850), fitting: visible)
        }
        setCompactLayout(compact)
        window.level = floating ? .floating : .normal
        installMenus()
        installSignals()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        if let workspace = argument("--workspace") { open(URL(fileURLWithPath: workspace)) }
        else if let last = UserDefaults.standard.string(forKey: "lastWorkspace"), FileManager.default.fileExists(atPath: last) {
            open(URL(fileURLWithPath: last))
        } else { chooseWorkspace() }
    }

    private func setCompactLayout(_ compact: Bool) {
        guard let window, let screen = window.screen ?? NSScreen.main else { return }
        let visible = screen.visibleFrame
        if compact {
            if window.frame.width >= min(980, visible.width) { wideFrame = window.frame }
            window.minSize = NSSize(width: min(460, visible.width), height: min(620, visible.height))
            window.setFrame(sidePanelFrame(in: visible), display: true)
        } else {
            window.minSize = NSSize(width: min(980, visible.width), height: min(750, visible.height))
            let restored = wideFrame ?? CGRect(x: visible.minX, y: visible.minY, width: 1100, height: 850)
            window.setFrame(windowFrame(restored, fitting: visible), display: true)
        }
    }

    private func configuredURL(_ variable: String, bundleKey: String) -> URL? {
        let value = ProcessInfo.processInfo.environment[variable] ?? (Bundle.main.object(forInfoDictionaryKey: bundleKey) as? String)
        return value.map { URL(fileURLWithPath: NSString(string: $0).expandingTildeInPath) }
    }

    private func developmentRoot() -> URL? {
        var path = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        for _ in 0..<7 {
            if FileManager.default.fileExists(atPath: path.appendingPathComponent("pyproject.toml").path) { return path }
            path.deleteLastPathComponent()
        }
        return nil
    }

    private func argument(_ key: String) -> String? {
        guard let index = CommandLine.arguments.firstIndex(of: key), CommandLine.arguments.count > index + 1 else { return nil }
        return CommandLine.arguments[index + 1]
    }

    @objc private func chooseWorkspace() {
        guard !terminating else { return }
        guard session.canSwitchWorkspace else {
            session.errorMessage = "请先停止当前任务，再切换工作区。"
            return
        }
        let chooser = NSOpenPanel()
        chooser.title = "选择 Star 任务工作区"
        chooser.canChooseFiles = false; chooser.canChooseDirectories = true; chooser.canCreateDirectories = true
        chooser.allowsMultipleSelection = false
        if chooser.runModal() == .OK, let url = chooser.url { open(url) }
    }

    private func open(_ workspace: URL) {
        guard let sourceRoot, let python,
              FileManager.default.isExecutableFile(atPath: python.path) else {
            session.errorMessage = "未找到 Python 环境。请在项目根目录创建 .venv，或通过 STAR_PYTHON 指定解释器。"
            return
        }
        session.stop { [weak self] in
            guard let self, !self.terminating else { return }
            UserDefaults.standard.set(workspace.path, forKey: "lastWorkspace")
            self.window?.title = "Star — \(workspace.lastPathComponent)"
            self.session.start(workspace: workspace, python: python, sourceRoot: sourceRoot)
        }
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        NSApp.terminate(nil)
        return false
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if !session.processRunning { return .terminateNow }
        if terminating { return .terminateLater }
        terminating = true
        session.stop { NSApp.reply(toApplicationShouldTerminate: true) }
        return .terminateLater
    }

    func applicationWillTerminate(_ notification: Notification) {
        signalSources.forEach { $0.cancel() }
        signalSources.removeAll()
    }

    private func installSignals() {
        for number in [SIGINT, SIGTERM] {
            Darwin.signal(number, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: number, queue: .main)
            source.setEventHandler { NSApp.terminate(nil) }
            source.resume()
            signalSources.append(source)
        }
    }

    private func installMenus() {
        let main = NSMenu(), applicationItem = NSMenuItem(), applicationMenu = NSMenu()
        applicationMenu.addItem(withTitle: "关于 Star", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        applicationMenu.addItem(.separator())
        applicationMenu.addItem(withTitle: "退出 Star", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        applicationItem.submenu = applicationMenu; main.addItem(applicationItem)
        let fileItem = NSMenuItem(), fileMenu = NSMenu(title: "文件")
        let open = fileMenu.addItem(withTitle: "选择工作区…", action: #selector(chooseWorkspace), keyEquivalent: "o")
        open.target = self
        fileItem.submenu = fileMenu; main.addItem(fileItem)
        NSApp.mainMenu = main
    }
}

@main
struct StarDesktop {
    @MainActor static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
        withExtendedLifetime(delegate) {}
    }
}
