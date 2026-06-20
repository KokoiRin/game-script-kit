## 1. Application

- [x] 1.1 添加脚本依赖分析测试，覆盖 `PointRef` 会进入结构化点位依赖且去重。
- [x] 1.2 在 `ScriptDependencyDetails` 和 `ScriptDetailsResult` 中新增 `point_dependencies`。
- [x] 1.3 实现递归收集 `PointRef` 点位依赖，排除裸 `Point`。

## 2. CLI 和 UI

- [x] 2.1 添加 CLI details 测试，覆盖“点位依赖”分组。
- [x] 2.2 添加 UI HTTP 和静态资源测试，覆盖 `point_dependencies` payload 与页面展示。
- [x] 2.3 更新 CLI、HTTP payload 和前端脚本详情展示。

## 3. 验证和归档

- [x] 3.1 运行相关测试、全量测试、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实脚本详情 smoke test。
- [x] 3.3 完成 OpenSpec 归档。
- [x] 3.4 提交并推送当前分支。
