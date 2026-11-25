import Foundation

/// 将字典格式化为按 key 排序的缩进 JSON，供资源展示、指纹计算与证据输出共用。
func prettyJSON(_ value: [String: Any]) -> String {
    guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) else {
        return ""
    }
    return String(decoding: data, as: UTF8.self)
}

/// 负责将原生壳诊断消息加上时间戳并追加到内存缓冲与工作区 `.star/desktop.log`。
enum DiagnosticsLog {
    private static let memoryCharacterLimit = 32768
    private static let fileByteLimit: UInt64 = 1_048_576

    static func append(_ message: String, to diagnostics: inout String, workspace: URL?) {
        let entry = ISO8601DateFormatter().string(from: Date()) + " " + message
        diagnostics = String((diagnostics + entry).suffix(memoryCharacterLimit))
        guard let workspace else { return }
        let folder = workspace.appendingPathComponent(".star")
        let log = folder.appendingPathComponent("desktop.log")
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: log.path) {
            FileManager.default.createFile(atPath: log.path, contents: nil)
        }
        if let handle = try? FileHandle(forWritingTo: log) {
            defer { try? handle.close() }
            let size = (try? handle.seekToEnd()) ?? 0
            if size > fileByteLimit {
                try? handle.truncate(atOffset: 0)
                try? handle.seek(toOffset: 0)
            }
            try? handle.write(contentsOf: Data(entry.utf8))
        }
    }
}
