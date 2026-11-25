import Foundation

/// 编排列表中的单个任务条目，使用独立 UUID 区分重复添加的同名任务。
struct PlanEntry: Identifiable, Equatable {
    let id = UUID()
    var name: String
    var waitSeconds: String = "0"
}

/// 纯值操作集合：负责编排草稿解析、指纹计算、排序以及提交前的合法性校验。
enum PlanDraft {
    typealias Object = [String: Any]

    struct ValidationError: LocalizedError, Equatable {
        let message: String
        var errorDescription: String? { message }
    }

    static func parse(_ plan: Object) -> (name: String, entries: [PlanEntry]) {
        let name = plan["name"] as? String ?? "我的流程"
        let entries = (plan["items"] as? [Object] ?? []).compactMap { item -> PlanEntry? in
            guard let itemName = item["name"] as? String else { return nil }
            let wait = (item["wait_after_seconds"] as? NSNumber)?.stringValue ?? "0"
            return PlanEntry(name: itemName, waitSeconds: wait)
        }
        return (name, entries)
    }

    static func fingerprint(name: String, entries: [PlanEntry]) -> String {
        let value: Object = [
            "name": name,
            "items": entries.map { ["name": $0.name, "wait": $0.waitSeconds] },
        ]
        return prettyJSON(value)
    }

    static func move(_ entries: inout [PlanEntry], id: UUID, by offset: Int) {
        guard let index = entries.firstIndex(where: { $0.id == id }) else { return }
        let destination = index + offset
        guard entries.indices.contains(destination) else { return }
        entries.swapAt(index, destination)
    }

    static func buildPayload(name: String, entries: [PlanEntry]) -> Result<Object, ValidationError> {
        guard !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, !entries.isEmpty else {
            return .failure(ValidationError(message: "请填写流程名称并添加至少一个任务。"))
        }
        var items: [Object] = []
        for entry in entries {
            guard let seconds = Double(entry.waitSeconds), seconds.isFinite, seconds >= 0 else {
                return .failure(ValidationError(message: "\(entry.name) 的等待秒数需要是大于或等于 0 的数字。"))
            }
            items.append(["name": entry.name, "wait_after_seconds": seconds])
        }
        return .success(["name": name, "items": items])
    }
}
