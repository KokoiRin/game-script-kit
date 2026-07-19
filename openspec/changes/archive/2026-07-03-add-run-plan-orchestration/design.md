## Context

现有单脚本运行链路已经收敛：

```text
CLI run
  -> load project script catalog
  -> resolve shared resources
  -> run_script_on_local_desktop
  -> application.script_run.run_script
  -> engine.ScriptRunner
```

`LocalControlApplication` 也已经能按名称运行脚本并归一化 stdout/stderr，但还没有“多个脚本组成一轮”的应用层对象。

## Goals / Non-Goals

**Goals:**

- 让用户一次选择多个已有脚本运行。
- 让计划执行规则集中在 application 层，CLI 只负责参数映射和结果展示。
- 第一版输出稳定摘要，便于后续 UI 或计划文件复用。

**Non-Goals:**

- 不新增 `plans/*.json` 文件格式。
- 不把多个脚本合并成一个大 `Script`。
- 不实现后台 Run Plan、暂停恢复、并发执行或运行历史。
- 不修改单脚本 runner 的步骤语义。

## Design

新增 `game_automation.portable.application.run_plan`：

- `RunPlanItemResult`：记录单个脚本名称、序号、exit code、finish reason、stdout、stderr。
- `RunPlanResult`：记录整体 exit code、finish reason、所有 item 结果，并生成可展示 stdout/stderr。
- `run_script_plan(...)`：接收脚本名称序列、catalog、单脚本 runner callable 和 dry-run 参数，按顺序运行。

CLI 新增 `run-plan` 子命令：

- 解析多个脚本名。
- 复用项目脚本 catalog、共享资源合并、dry-run 图片依赖和 dry-run 状态解析。
- 默认某个 item 退出码非 0 后停止后续 item。
- item 退出码为 0 但结束原因为 `stopped_unmet_condition` 时也停止后续 item，并保留该整轮结束原因。
- `--continue-on-error` 打开后继续运行后续 item，最终 exit code 使用第一个非 0 item 的退出码。

## Decisions

- Run Plan 引用脚本名，不复制或嵌套脚本步骤。这样编排语义和脚本语义分离，避免入口层解释 DSL。
- 第一版使用 CLI 传入脚本列表，不新增计划文件格式。当前需求核心是“一轮选择并执行哪些脚本”，固定计划文件可以在同一 application use case 上后续扩展。
- 失败策略第一版只提供默认停止和继续收集两种模式，避免过早设计复杂 per-item policy。
- 条件未满足属于正常停止而非运行错误，因此保持退出码 0；Run Plan 通过结束原因判断是否完整执行，避免误报 `completed`。

## Risks / Trade-offs

- 没有计划文件意味着常用组合还不能保存为命名计划；但可以先验证编排语义和结果摘要是否符合真实使用。
- 同步 CLI 执行长计划会阻塞终端；后台 UI 计划执行留到编排语义稳定后再接入。
