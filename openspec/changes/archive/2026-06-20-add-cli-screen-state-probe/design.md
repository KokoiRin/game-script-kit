# Design: add-cli-screen-state-probe

## Boundary

CLI 入口不解释状态识别规则，也不直接创建图像定位 adapter。它通过 desktop composition 创建 `LocalControlApplication`，调用 `probe_screen_state_once(...)`，再把结果打印成命令行文本。

## Output

输出包含：

- `当前状态：<state>`
- `总耗时：<ms>ms`
- `候选：`
- 每个候选的状态名、搜索项名、命中状态、耗时和置信度

## Error Handling

配置错误返回 `2`。平台 adapter、截图权限或图像定位失败返回 `1`。错误信息写入 stderr。
