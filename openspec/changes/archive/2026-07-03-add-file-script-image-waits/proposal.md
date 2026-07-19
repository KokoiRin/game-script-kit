## Why

当前文件脚本只能等待固定状态，不能直接等待活动列表中的图片或命名搜索出现。游戏界面里任务条目位置会变化，脚本需要先等目标图片可见，再按搜索结果偏移点击，避免用固定时间猜测界面加载速度。

## What Changes

- 文件脚本 JSON 新增 `wait_until_image` 步骤。
- `wait_until_image` 支持引用命名搜索、命名图片或内联图片，并复用现有 `ImageExists(...)` 条件等待语义。
- 脚本详情和依赖检查复用现有图片依赖分析能力。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `script-management`: 文件脚本 JSON 格式支持图片/搜索目标条件等待。

## Impact

- 影响文件脚本配置解析、配置脚本测试和当前项目脚本。
- 不新增平台 adapter，不修改 runner、图像匹配端口或条件等待执行语义。
