// Ledger Check for Mac: starts the sealed containers and shows the app in a native window.
import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var status: NSTextField!
    var spinner: NSProgressIndicator!
    let home = FileManager.default.homeDirectoryForCurrentUser
    lazy var support = home.appendingPathComponent("Library/Application Support/LedgerCheck")
    lazy var projectDir = support.appendingPathComponent("project")
    lazy var envFile = projectDir.appendingPathComponent(".env")
    var docker = "docker"

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1320, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Ledger Check"
        window.minSize = NSSize(width: 900, height: 600)
        window.center()

        let loading = NSView()
        spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.startAnimation(nil)
        let title = NSTextField(labelWithString: "Ledger Check")
        title.font = .systemFont(ofSize: 26, weight: .semibold)
        status = NSTextField(labelWithString: "Starting…")
        status.textColor = .secondaryLabelColor
        let stack = NSStackView(views: [title, spinner, status])
        stack.orientation = .vertical
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        loading.addSubview(stack)
        NSLayoutConstraint.activate([stack.centerXAnchor.constraint(equalTo: loading.centerXAnchor),
                                     stack.centerYAnchor.constraint(equalTo: loading.centerYAnchor)])
        window.contentView = loading
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        DispatchQueue.global(qos: .userInitiated).async { self.start() }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ notification: Notification) {
        _ = run([docker, "compose", "-p", "ledgercheck", "stop"], timeout: 20)
    }

    // MARK: - Startup

    func start() {
        say("Preparing the sealed container…")
        do { try installProject() } catch { return fail("Couldn't prepare files: \(error.localizedDescription)") }
        guard ensureKey() else { return fail("An Anthropic API key is needed to run the analyst.") }
        guard let d = findDocker() else { return fail("Docker isn't installed. Install OrbStack or Docker Desktop, then reopen Ledger Check.") }
        docker = d
        if run([docker, "info"], timeout: 15).code != 0 {
            say("Starting Docker…")
            _ = run(["/usr/bin/open", "-a", "OrbStack"], timeout: 10)
            if run([docker, "info"], timeout: 5).code != 0 { _ = run(["/usr/bin/open", "-a", "Docker"], timeout: 10) }
            var ready = false
            for _ in 0..<45 { if run([docker, "info"], timeout: 5).code == 0 { ready = true; break }; Thread.sleep(forTimeInterval: 2) }
            if !ready { return fail("Docker didn't start. Open OrbStack or Docker Desktop, then reopen Ledger Check.") }
        }
        say("Building and sealing the containers (first run takes a minute)…")
        let up = run([docker, "compose", "-p", "ledgercheck", "up", "-d", "--build"], cwd: projectDir, timeout: 600)
        try? up.out.write(to: support.appendingPathComponent("compose.log"), atomically: true, encoding: .utf8)
        if up.code != 0 { return fail("Couldn't start the containers. Details are in ~/Library/Application Support/LedgerCheck/compose.log") }
        say("Running isolation checks…")
        for _ in 0..<60 {
            if let u = URL(string: "http://localhost:8080/api/audit"), (try? Data(contentsOf: u)) != nil {
                DispatchQueue.main.async { self.showApp() }
                return
            }
            Thread.sleep(forTimeInterval: 1)
        }
        fail("The app didn't come up on localhost:8080.")
    }

    func installProject() throws {
        let fm = FileManager.default
        guard let bundled = Bundle.main.resourceURL?.appendingPathComponent("project") else { return }
        try fm.createDirectory(at: projectDir, withIntermediateDirectories: true)
        for item in try fm.contentsOfDirectory(atPath: bundled.path) {
            let dest = projectDir.appendingPathComponent(item)
            if fm.fileExists(atPath: dest.path) { try fm.removeItem(at: dest) }
            try fm.copyItem(at: bundled.appendingPathComponent(item), to: dest)
        }
    }

    func ensureKey() -> Bool {
        if let s = try? String(contentsOf: envFile, encoding: .utf8), s.contains("ANTHROPIC_API_KEY=sk-") { return true }
        var key: String?
        DispatchQueue.main.sync {
            let alert = NSAlert()
            alert.messageText = "Connect the AI analyst"
            alert.informativeText = "Paste your Anthropic API key. It's saved only on this Mac and only the sealed container uses it."
            let field = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 340, height: 24))
            field.placeholderString = "sk-ant-…"
            alert.accessoryView = field
            alert.addButton(withTitle: "Save")
            alert.addButton(withTitle: "Cancel")
            alert.window.initialFirstResponder = field
            if alert.runModal() == .alertFirstButtonReturn { key = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines) }
        }
        guard let k = key, k.hasPrefix("sk-") else { return false }
        do {
            try "ANTHROPIC_API_KEY=\(k)\n".write(to: envFile, atomically: true, encoding: .utf8)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: envFile.path)
        } catch { return false }
        return true
    }

    func findDocker() -> String? {
        ["/usr/local/bin/docker", "/opt/homebrew/bin/docker", home.appendingPathComponent(".orbstack/bin/docker").path,
         "/Applications/Docker.app/Contents/Resources/bin/docker"].first { FileManager.default.isExecutableFile(atPath: $0) }
    }

    // MARK: - UI

    func showApp() {
        web = WKWebView(frame: .zero, configuration: WKWebViewConfiguration())
        web.load(URLRequest(url: URL(string: "http://localhost:8080")!))
        window.contentView = web
    }

    func say(_ text: String) { DispatchQueue.main.async { self.status.stringValue = text } }

    func fail(_ text: String) {
        DispatchQueue.main.async {
            self.spinner.stopAnimation(nil)
            self.spinner.isHidden = true
            self.status.stringValue = text
            self.status.textColor = .systemRed
        }
    }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Reload", action: #selector(reload), keyEquivalent: "r")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Ledger Check", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        let editItem = NSMenuItem()
        main.addItem(editItem)
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        NSApp.mainMenu = main
    }

    @objc func reload() { web?.reload() }

    // MARK: - Shell

    @discardableResult
    func run(_ args: [String], cwd: URL? = nil, timeout: TimeInterval) -> (code: Int32, out: String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: args[0])
        p.arguments = Array(args.dropFirst())
        if let cwd { p.currentDirectoryURL = cwd }
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:\(home.path)/.orbstack/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        p.environment = env
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        var data = Data()
        let lock = NSLock()
        pipe.fileHandleForReading.readabilityHandler = { h in let d = h.availableData; lock.lock(); data.append(d); lock.unlock() }
        do { try p.run() } catch { return (-1, "\(error)") }
        let deadline = Date().addingTimeInterval(timeout)
        while p.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.2) }
        if p.isRunning { p.terminate() }
        p.waitUntilExit()
        pipe.fileHandleForReading.readabilityHandler = nil
        lock.lock(); defer { lock.unlock() }
        return (p.terminationStatus, String(decoding: data, as: UTF8.self))
    }
}

@main
struct Main {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
