## Why

文件脚本进入真实使用后，用户很容易在 `scripts/*.json` 中写出一个临时坏文件。现在一个坏脚本会让整个项目 catalog 加载失败，导致可用脚本也无法列出或运行，影响排错和迭代效率。

## What Changes

- 项目脚本加载改为“部分成功”：合法文件脚本继续进入 catalog，坏文件脚本被跳过。
- 坏文件脚本、重复脚本名称等配置问题会被收集为可读错误。
- CLI `star list` 仍输出可用脚本，并把脚本配置错误写到 stderr。
- 本地 UI 的脚本列表仍显示可用脚本，并展示脚本配置错误。
- 不改变单个脚本详情或运行的执行语义；无效脚本不会被注册，也不能按名称运行。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-management`: 项目文件脚本加载从整体失败改为隔离坏脚本并暴露配置错误。
- `local-control-ui`: 本地 UI 展示文件脚本配置错误，同时保留可用脚本列表。

## Impact

- 影响配置脚本 loader、项目 catalog 组装、CLI list 输出、本地控制 application、HTTP payload 和前端脚本列表展示。
- 不新增第三方依赖，不改变现有 Python 内置脚本注册方式。
