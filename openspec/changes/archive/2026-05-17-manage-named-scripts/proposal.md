## Why

当前脚本仍以代码中的固定函数或 CLI 入口存在，脚本数量增加后不方便查找、编辑和复用。需要把脚本任务独立成可管理的定义，并允许调用方通过脚本名称直接启动指定脚本。

## What Changes

- 为 `Script` 增加稳定的 `name` 字段，用于标识脚本任务。
- 新增脚本管理能力：集中保存、列出、读取和解析脚本定义。
- 新增按名称运行脚本的入口，让 CLI 可以通过脚本名称选择并执行脚本。
- 第一版脚本定义使用仓库内可编辑的 Python 模块或轻量注册表，不引入数据库或复杂文件格式。
- 保留现有 runner、动作模型和窗口坐标解析规则。

## Capabilities

### New Capabilities
- `script-management`: 管理命名脚本定义，并支持按名称查找和启动脚本。

### Modified Capabilities
- `script-action-model`: `Script` 需要记录脚本名称，并在创建时校验名称可用。

## Impact

- 影响 `src/game_automation/core/script.py` 的 `Script` 数据模型。
- 新增脚本目录或注册表模块，用于管理多个命名脚本。
- 调整或新增 CLI，使用户可以通过脚本名称运行某个脚本。
- 更新 README 和测试，覆盖脚本命名、查找、编辑入口和按名称运行。
