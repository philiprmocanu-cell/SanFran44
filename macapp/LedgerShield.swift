// Ledger Shield for Mac: a self-contained app. It serves the bundled Shield page and the on-device
// AI model from a tiny web server bound to this Mac only (127.0.0.1), and shows it in a native window.
// No Docker, no internet: the model ships inside the app.
import Cocoa
import Network
import WebKit

// MARK: - Local-only static file server

final class LocalServer {
    let root: URL
    private var listener: NWListener?
    private(set) var port: UInt16 = 0

    init(root: URL) { self.root = root.standardizedFileURL }

    func start(preferred: [UInt16], ready: @escaping (Bool) -> Void) {
        guard let p = preferred.first else { return ready(false) }
        let params = NWParameters.tcp
        params.requiredLocalEndpoint = .hostPort(host: .ipv4(.loopback), port: NWEndpoint.Port(rawValue: p)!)
        params.allowLocalEndpointReuse = true
        guard let l = try? NWListener(using: params) else { return start(preferred: Array(preferred.dropFirst()), ready: ready) }
        listener = l
        l.newConnectionHandler = { [weak self] c in
            c.start(queue: .global(qos: .userInitiated))
            self?.read(c, buffer: Data())
        }
        l.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready: self?.port = p; DispatchQueue.main.async { ready(true) }
            case .failed:
                l.cancel()
                DispatchQueue.main.async { self?.start(preferred: Array(preferred.dropFirst()), ready: ready) }
            default: break
            }
        }
        l.start(queue: .global(qos: .userInitiated))
    }

    private func read(_ c: NWConnection, buffer: Data) {
        c.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, done, err in
            guard let self else { return }
            var buf = buffer
            if let data { buf.append(data) }
            if let end = buf.range(of: Data("\r\n\r\n".utf8)) {
                self.respond(c, head: String(decoding: buf[..<end.lowerBound], as: UTF8.self))
            } else if done || err != nil || buf.count > 65536 {
                c.cancel()
            } else {
                self.read(c, buffer: buf)
            }
        }
    }

    private func respond(_ c: NWConnection, head: String) {
        let parts = head.split(separator: "\r\n").first?.split(separator: " ") ?? []
        guard parts.count >= 2, parts[0] == "GET" || parts[0] == "HEAD" else { return send(c, 405, "text/plain", Data("Method not allowed".utf8)) }
        var path = String(parts[1]).components(separatedBy: "?")[0].removingPercentEncoding ?? "/"
        if path.hasSuffix("/") { path += "index.html" }
        let file = root.appendingPathComponent(String(path.dropFirst())).standardizedFileURL
        guard file.path.hasPrefix(root.path),
              let body = try? Data(contentsOf: file, options: .mappedIfSafe) else {
            return send(c, 404, "text/plain", Data("Not found".utf8))
        }
        send(c, 200, Self.mime(file.pathExtension), parts[0] == "HEAD" ? Data() : body, length: body.count)
    }

    private func send(_ c: NWConnection, _ code: Int, _ type: String, _ body: Data, length: Int? = nil) {
        let status = [200: "OK", 404: "Not Found", 405: "Method Not Allowed"][code] ?? "OK"
        var head = "HTTP/1.1 \(code) \(status)\r\nContent-Type: \(type)\r\nContent-Length: \(length ?? body.count)\r\n"
        head += "Cache-Control: no-cache\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n"
        var out = Data(head.utf8)
        out.append(body)
        c.send(content: out, completion: .contentProcessed { _ in c.cancel() })
    }

    static func mime(_ ext: String) -> String {
        switch ext.lowercased() {
        case "html": return "text/html; charset=utf-8"
        case "js", "mjs": return "text/javascript; charset=utf-8"
        case "json": return "application/json"
        case "wasm": return "application/wasm"
        case "css": return "text/css"
        case "svg": return "image/svg+xml"
        case "png": return "image/png"
        case "txt": return "text/plain; charset=utf-8"
        default: return "application/octet-stream"
        }
    }
}

// MARK: - App

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var web: WKWebView!
    var server: LocalServer!
    // Clipboard auto-clean: watch the Mac clipboard and replace sensitive text with the cleaned version.
    var autoClean = true
    var pageReady = false
    var lastChange = NSPasteboard.general.changeCount
    var clipTimer: Timer?
    var statusItem: NSStatusItem!
    var cleanedCount = 0

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1440, height: 920),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "Ledger Shield"
        window.titlebarAppearsTransparent = true
        window.backgroundColor = NSColor(red: 0.03, green: 0.043, blue: 0.08, alpha: 1)
        window.minSize = NSSize(width: 980, height: 640)
        window.setFrameAutosaveName("LedgerShieldMain")
        window.delegate = self
        window.center()

        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.userContentController.add(self, name: "shield")
        web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.setValue(false, forKey: "drawsBackground")
        if #available(macOS 13.3, *) { web.isInspectable = true }
        window.contentView = web
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        setupStatusItem()
        clipTimer = Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { [weak self] _ in self?.checkClipboard() }

        let root = Bundle.main.resourceURL!.appendingPathComponent("web")
        server = LocalServer(root: root)
        server.start(preferred: Array(47821...47830)) { [weak self] ok in
            guard let self else { return }
            if ok {
                self.web.load(URLRequest(url: URL(string: "http://127.0.0.1:\(self.server.port)/")!))
            } else {
                self.web.loadHTMLString("<body style='background:#080b14;color:#eee;font:16px -apple-system;padding:40px'>Ledger Shield couldn't start its local server.</body>", baseURL: nil)
            }
        }
    }

    // Closing the window keeps Shield cleaning the clipboard in the background (menu bar icon stays).
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func windowShouldClose(_ sender: NSWindow) -> Bool { window.orderOut(nil); return false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { showWindow(); return true }
    @objc func showWindow() { window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true) }

    // MARK: - Clipboard auto-clean

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any] else { return }
        if let on = body["autoClean"] as? Bool { autoClean = on; updateStatusItem() }
        if body["ready"] as? Bool == true { pageReady = true; lastChange = NSPasteboard.general.changeCount }
    }

    func checkClipboard() {
        let pb = NSPasteboard.general
        guard pb.changeCount != lastChange else { return }
        lastChange = pb.changeCount
        guard autoClean, pageReady else { return }
        // Leave Shield's own copies alone (e.g. restored answers), and respect password managers.
        let front = NSWorkspace.shared.frontmostApplication
        if front?.bundleIdentifier == Bundle.main.bundleIdentifier { return }
        let types = pb.types ?? []
        if types.contains(NSPasteboard.PasteboardType("org.nspasteboard.ConcealedType")) || types.contains(NSPasteboard.PasteboardType("org.nspasteboard.TransientType")) { return }
        guard let text = pb.string(forType: .string), !text.isEmpty, text.count < 200_000 else { return }
        let seen = pb.changeCount
        web.callAsyncJavaScript("return await window.shieldClean(text, app);", arguments: ["text": text, "app": front?.localizedName ?? ""], in: nil, in: .page) { [weak self] result in
            guard let self, case .success(let value) = result, let clean = value as? String, clean != text else { return }
            guard NSPasteboard.general.changeCount == seen else { return }   // user copied something newer meanwhile
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(clean, forType: .string)
            self.lastChange = NSPasteboard.general.changeCount
            self.cleanedCount += 1
            self.flashStatusItem()
        }
    }

    func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        updateStatusItem()
    }

    func updateStatusItem() {
        let menu = NSMenu()
        let toggle = NSMenuItem(title: "Auto-clean clipboard", action: #selector(toggleAutoClean), keyEquivalent: "")
        toggle.state = autoClean ? .on : .off
        toggle.target = self
        menu.addItem(toggle)
        let info = NSMenuItem(title: cleanedCount == 0 ? "Nothing cleaned yet" : "Cleaned \(cleanedCount) copied item\(cleanedCount == 1 ? "" : "s")", action: nil, keyEquivalent: "")
        info.isEnabled = false
        menu.addItem(info)
        menu.addItem(.separator())
        let open = NSMenuItem(title: "Open Ledger Shield", action: #selector(showWindow), keyEquivalent: "o"); open.target = self
        menu.addItem(open)
        menu.addItem(withTitle: "Quit Ledger Shield", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        statusItem.menu = menu
        if let b = statusItem.button {
            b.image = NSImage(systemSymbolName: autoClean ? "checkmark.shield.fill" : "shield.slash", accessibilityDescription: "Ledger Shield")
            b.title = ""
        }
    }

    func flashStatusItem() {
        updateStatusItem()
        guard let b = statusItem.button else { return }
        b.title = " Cleaned"
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in self?.statusItem.button?.title = "" }
    }

    @objc func toggleAutoClean() {
        autoClean.toggle()
        updateStatusItem()
        web.evaluateJavaScript("window.setAutoClean && window.setAutoClean(\(autoClean))")
    }

    // Keep the app on its own local pages; open anything else in the default browser.
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if action.shouldPerformDownload { return decisionHandler(.download) }
        if let url = action.request.url, let host = url.host, host != "127.0.0.1", url.scheme?.hasPrefix("http") == true {
            NSWorkspace.shared.open(url)
            return decisionHandler(.cancel)
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let dir = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask)[0]
        var dest = dir.appendingPathComponent(suggestedFilename)
        let base = dest.deletingPathExtension().lastPathComponent, ext = dest.pathExtension
        var i = 1
        while FileManager.default.fileExists(atPath: dest.path) { dest = dir.appendingPathComponent("\(base) \(i).\(ext)"); i += 1 }
        completionHandler(dest)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { NSWorkspace.shared.activateFileViewerSelecting([dest]) }
    }

    // File picker for "Upload CSV" and "Import policy".
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = false
        panel.beginSheetModal(for: window) { completionHandler($0 == .OK ? panel.urls : nil) }
    }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Ledger Shield", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Reload", action: #selector(reload), keyEquivalent: "r")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Ledger Shield", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Ledger Shield", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        let editItem = NSMenuItem(); main.addItem(editItem)
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        let winItem = NSMenuItem(); main.addItem(winItem)
        let win = NSMenu(title: "Window")
        win.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        win.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        winItem.submenu = win
        NSApp.mainMenu = main
        NSApp.windowsMenu = win
    }

    @objc func reload() { web.reload() }
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
