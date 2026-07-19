## 1. OpenSpec

- [x] 1.1 定义 Run Plan 第一版行为、范围和失败策略。
- [x] 1.2 补充 `script-management` 规格，覆盖 CLI 顺序执行、默认停止和继续收集。

## 2. Application 编排

- [x] 2.1 新增 Run Plan application 模型和用例，按脚本名顺序运行已有脚本。
- [x] 2.2 覆盖成功计划、默认遇错停止、`continue_on_error` 继续收集和未知脚本错误。
- [x] 2.3 传播条件未满足的正常停止结果，避免 Run Plan 误报整轮完成。

## 3. CLI 入口

- [x] 3.1 新增 `star run-plan <script>...` 子命令，复用 dry-run 参数和共享资源解析。
- [x] 3.2 输出每个 item 的摘要和单脚本输出，返回稳定整体退出码。
- [x] 3.3 覆盖 CLI 成功、失败停止、继续收集和 dry-run 图片依赖。
- [x] 3.4 覆盖 CLI 条件未满足摘要和默认停止后续脚本。

## 4. 验证

- [x] 4.1 运行相关测试和全量测试。
- [x] 4.2 运行 `openspec validate add-run-plan-orchestration --strict`。
- [x] 4.3 运行 `openspec validate --specs --strict` 和 `git diff --check`。
