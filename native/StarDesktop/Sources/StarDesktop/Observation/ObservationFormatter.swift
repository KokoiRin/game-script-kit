import Foundation

/// 纯文本格式化器：将后台返回的实时识别 JSON 载荷转换为界面展示文案，不持有状态或 I/O。
enum ObservationFormatter {
    typealias Object = [String: Any]

    static func rulesSummary(_ result: Object) -> String {
        let rules = result["rules"] as? [Object] ?? []
        if rules.isEmpty {
            return "还没有状态素材，请到素材准备页框选并登记。"
        }
        return rules.map { rule in
            let state = rule["state"] as? String ?? ""
            let image = rule["image"] as? String ?? ""
            let region = (rule["region"] as? Object).map(prettyJSON) ?? "整个窗口"
            let isPoints = rule["method"] as? String == "points"
            let method = isPoints ? "多点 · \(rule["point_count"] as? Int ?? 0) 点" : "模板"
            let location = isPoints
                ? "固定截图像素点位 · 整体偏移 ±\(rule["offset_radius"] as? Int ?? 0) 像素"
                : "搜索范围：\(region)"
            return "\(state) · 优先级 \(rule["priority"] as? Int ?? 0) · \(method) · \(image) · \(location)"
        }.joined(separator: "\n")
    }

    static func phaseLabel(_ rawPhase: String) -> String {
        let labels = [
            "idle": "未启动",
            "waiting": "等待首帧",
            "observing": "正在观察",
            "unavailable": "画面不可用",
            "stale": "画面已过期",
            "stopping": "正在停止",
            "stopped": "已停止",
        ]
        return labels[rawPhase] ?? rawPhase
    }

    static func metrics(_ result: Object) -> String {
        let sequence = result["sequence"] as? Int ?? 0
        let elapsed = result["elapsed_ms"] as? Double ?? 0
        let actual = result["actual_hz"] as? Double ?? 0
        let age = result["age_ms"] as? Double
        return "第 \(sequence) 轮 · 耗时 \(String(format: "%.0f", elapsed)) ms · 实际 \(String(format: "%.1f", actual)) 次/秒" +
            (age.map { " · 画面距今 \(String(format: "%.0f", $0)) ms" } ?? "")
    }

    static func evidence(_ result: Object) -> String {
        let items = result["evidence"] as? [Object] ?? []
        if items.isEmpty {
            return "暂无有效画面证据"
        }
        return items.map { item in
            let skipped = item["skipped"] as? Bool ?? false
            let priority = item["priority"] as? Int ?? 0
            let status = skipped ? "未检测" : ((item["found"] as? Bool ?? false) ? "命中" : "未命中")
            let score = (item["score"] as? Double).map { String(format: "%.3f", $0) } ?? "—"
            let rect = (item["rect"] as? Object).map(prettyJSON) ?? "无位置"
            let detail = item["method"] as? String == "points"
                ? "多点 · 匹配 \((item["matched_points"] as? Int).map(String.init) ?? "—")/\(item["point_count"] as? Int ?? 0) 点"
                : "相似度 \(score)"
            return "\(item["state"] as? String ?? "") / \(item["name"] as? String ?? "") · 优先级 \(priority) · \(status) · \(detail) · \(rect)"
        }.joined(separator: "\n\n")
    }

    static func history(_ result: Object) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        let items = result["history"] as? [Object] ?? []
        if items.isEmpty {
            return "暂无状态变化"
        }
        return "历史记录（不代表当前画面）\n" + items.prefix(32).map { item in
            let time = formatter.string(from: Date(timeIntervalSince1970: item["at"] as? Double ?? 0))
            return "\(time)  \(item["previous"] as? String ?? "") → \(item["state"] as? String ?? "")"
        }.joined(separator: "\n")
    }

    static func performance(_ value: Object) -> (summary: String, details: String) {
        func milliseconds(_ key: String) -> String {
            guard let number = value[key] as? Double else { return "—" }
            return String(format: "%.1f", number) + " ms"
        }
        let materials = (value["material_count"] as? Int).map(String.init) ?? "—"
        let attempts = value["attempts"] as? Int ?? 0
        let failures = value["failures"] as? Int ?? 0
        let overBudget = value["over_budget"] as? Int ?? 0
        let stale = value["stale_results"] as? Int ?? 0
        let samples = value["sample_count"] as? Int ?? 0
        let limit = value["window_limit"] as? Int ?? 120
        let recentFailure: String
        if let at = value["last_failure_at"] as? Double {
            let formatter = DateFormatter()
            formatter.dateStyle = .short
            formatter.timeStyle = .medium
            let message = value["last_failure_message"] as? String ?? ""
            recentFailure = formatter.string(from: Date(timeIntervalSince1970: at)) + " " +
                (message.isEmpty ? "未提供错误详情" : message)
        } else {
            recentFailure = "无"
        }
        let streaming = value["capture_mode"] as? String == "window_stream"
        let captureLabel = streaming ? "窗口流取帧" : "截图"
        let duplicates = value["duplicate_results"] as? Int ?? 0
        let checked = (value["checked_count"] as? Int).map(String.init) ?? "—"
        let skipped = (value["skipped_count"] as? Int).map(String.init) ?? "—"
        let summary = "素材 \(materials) · 本轮检查 \(checked) · 跳过 \(skipped) · 最近轮 \(milliseconds("round_ms")) · p95 \(milliseconds("p95_ms"))"
        let details = "\(captureLabel) \(milliseconds("screenshot_ms")) · 识别 \(milliseconds("recognition_ms"))\n" +
            "高优先级先检查，命中后跳过低层素材。\n" +
            "源画面年龄 p95 \(milliseconds("source_age_p95_ms")) · 重复读取 \(duplicates) 次（不增加连续确认）\n" +
            "本次累计 \(attempts) 轮 · 成功 \(attempts - failures) · 失败 \(failures) · 超频率预算 \(overBudget) · 超龄结果 \(stale)\n" +
            "最近失败（历史，不代表当前不可用）：\(recentFailure)\n" +
            "最近最多 \(limit) 轮，当前 \(samples) 个样本（含失败）\n" +
            "整轮 p50 \(milliseconds("p50_ms")) · p95 \(milliseconds("p95_ms")) · max \(milliseconds("max_ms"))\n" +
            (streaming
                ? "采集频率跟随检测频率。取帧含窗口核对和内存转换，首轮含启动等待；源画面年龄单独统计，重复缓存不会续期。"
                : "截图含窗口核对和 PNG 读取。") +
            "识别含 OpenCV 加载、图像转换、模板加载与匹配。整轮不含调频等待或界面刷新；超过 1000/目标频率 ms 记一次超预算。停止保留统计。"
        return (summary, details)
    }
}
