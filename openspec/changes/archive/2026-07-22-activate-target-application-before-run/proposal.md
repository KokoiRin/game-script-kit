## Why

视觉靶场已经能稳定验证截图、识图和点击，但真实运行仍要求用户在脚本开始前手动把 Safari 切到前台。开发工具或终端一旦抢占焦点，Star 就会在错误应用上截图和点击。Star 需要在真实运行前主动激活用户指定的目标应用，让自动化任务可以从入口到结果独立完成。

## What Changes

- 为 `star run` 和 `star run-plan` 增加 `--target-app` 参数。
- 真实运行每个脚本前，通过应用层 port 请求平台激活目标应用。
- 新增 macOS 目标应用激活 adapter，使用系统 `open -a` 能力并等待界面稳定。
- 激活失败时停止当前脚本，以稳定的 setup failure 返回，不执行鼠标动作。
- dry-run 明确拒绝 `--target-app`，避免产生“已激活”的错误预期。
- 更新视觉靶场 smoke，使其可以直接验证无需人工切换 Safari 的完整流程。

## Capabilities

### New Capabilities

- `target-application-activation`: 定义真实脚本运行前激活目标应用的入口、应用层语义、平台接入和错误行为。

### Modified Capabilities

无。

## Impact

- 修改脚本运行 application、macOS adapter、本地桌面 composition 和 CLI。
- 不修改脚本 DSL、Window 坐标规则、runner 或图像匹配语义。
- 不新增第三方依赖。
