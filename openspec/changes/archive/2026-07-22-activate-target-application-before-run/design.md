## Context

Star 当前在全屏范围截图和识图，真实鼠标也直接作用于当前桌面。视觉靶场 smoke 已证明识图与点击链路可用，但执行前必须人工把浏览器放回前台。这不是 runner 的步骤语义，而是一次真实运行的环境准备职责。

## Goals / Non-Goals

**Goals:**

- 用户可以从 `run` 和 `run-plan` 指定一个目标应用。
- 真实脚本在创建和调用 runner 前完成应用激活。
- 激活失败归一化为 setup failure，且不产生输入动作。
- 平台细节留在 macOS adapter，portable application 只依赖 port。
- 用视觉靶场完成一次无需人工切窗的真实验证。

**Non-Goals:**

- 不在本轮枚举窗口、选择同应用内的多个窗口或读取窗口边界。
- 不改变 `ScreenWindow` 和 `AreaWindow` 坐标模型。
- 不保证运行期间其他应用永远无法抢占前台。
- 不把目标应用写入脚本 JSON；第一版由运行入口显式指定。

## Decisions

### 目标应用属于运行环境准备，不属于脚本步骤

新增 `ApplicationActivator` port，并由 `run_script` 在非 dry-run 模式、runner 装配之前调用。这样激活失败不会创建或调用真实输入 device，CLI 也不需要解释执行顺序。

未把激活建模成 `ActivateApplication` 脚本步骤，因为目标应用是整次运行的前置环境，不应在 repeat、if 或脚本中段任意出现。

### 第一版使用入口参数

`star run NAME --target-app Safari` 和 `star run-plan ... --target-app Safari` 显式表达本轮运行目标。Run Plan 在每个脚本开始前重新激活一次，以便前一个脚本或外部窗口改变焦点后仍能恢复目标。

第一版不修改脚本文件格式，避免把 macOS 应用名写进跨平台脚本定义。后续如果形成稳定跨平台标识，再独立设计持久化配置。

### macOS adapter 使用系统 open 命令

adapter 使用参数数组调用 `/usr/bin/open -a <application>`，不经过 shell。成功返回后等待一个短稳定时间，再交给 runner。命令不存在、应用不存在或非零退出都转换为可读的 `RuntimeError`。

### dry-run 拒绝目标应用

dry-run 的承诺是无真实桌面副作用，所以 `--dry-run` 与 `--target-app` 同时出现时 CLI 返回配置错误。应用层也不会在 dry-run 中调用 activator，确保非 CLI 调用方仍然安全。

## Risks / Trade-offs

- [应用成功激活但页面尚未渲染] → adapter 在系统命令成功后使用短稳定等待；脚本仍应通过 `WaitUntil` 等待具体视觉目标。
- [同名应用或多个窗口无法精确选择] → 本轮只解决应用级前台激活，多窗口选择留给独立能力。
- [运行期间焦点再次被抢走] → Run Plan 每个脚本前重新激活；脚本内部的持续焦点守护不纳入本轮。

## Migration Plan

现有命令不传 `--target-app` 时行为不变。若功能出现问题，可移除新参数和 adapter，不影响脚本 DSL 与 runner。

## Open Questions

无。先通过 Safari 靶场验证应用级激活是否足以消除当前人工切窗步骤。
