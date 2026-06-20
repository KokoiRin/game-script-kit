## 1. 文件脚本解析

- [x] 1.1 添加配置脚本 loader 测试，覆盖 wait、click point、click search、repeat、if_state、wait_until_state。
- [x] 1.2 实现 `scripts/*.json` 读取、基础 schema 校验和可读错误。
- [x] 1.3 将文件脚本转换为标准 `Script` 与 `TargetCatalog`，支持局部 points/images/regions/searches 资源。

## 2. Catalog 和入口接入

- [x] 2.1 添加项目 catalog 合并测试，覆盖内置脚本保留、文件脚本加入、重复名称报错。
- [x] 2.2 实现项目脚本 catalog 组装，并保持内置 `DEFAULT_SCRIPT_CATALOG` 不依赖项目文件系统。
- [x] 2.3 更新 CLI `list/details/run` 使用项目 catalog，并补充文件脚本 CLI 行为测试。

## 3. 本地 UI 接入

- [x] 3.1 更新本地控制 application/composition 使用项目 catalog。
- [x] 3.2 添加 UI HTTP 测试，覆盖文件脚本列表、详情和运行入口。

## 4. 示例和验证

- [x] 4.1 添加一个最小项目脚本示例文件，用于 smoke test 和用户参考。
- [x] 4.2 运行相关测试、全量测试、OpenSpec 校验和 diff 检查。
- [x] 4.3 运行 CLI smoke test，确认 `star list/details/run --dry-run` 可使用文件脚本。
- [x] 4.4 完成 OpenSpec 归档。
- [x] 4.5 提交并推送当前分支。
