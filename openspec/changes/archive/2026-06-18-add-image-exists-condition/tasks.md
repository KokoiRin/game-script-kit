## 1. 领域条件模型

- [x] 1.1 新增 `ImageExists` 领域模型测试，覆盖默认值、搜索区域、最低匹配置信度和非法置信度
- [x] 1.2 实现 `ImageExists` 并把 `Condition` 扩展为 `ColorIs | ImageExists`
- [x] 1.3 从领域包导出 `ImageExists`

## 2. 条件评估和 runner 注入

- [x] 2.1 新增条件评估测试，覆盖图片存在、图片不存在、搜索区域窗口解析、最低置信度传递和缺少 locator 报错
- [x] 2.2 修改 `condition_evaluator`，通过 `ScreenImageLocator` 评估 `ImageExists`
- [x] 2.3 新增 runner 测试，覆盖 `If(ImageExists(...))` 和 `WaitUntil(ImageExists(...))`
- [x] 2.4 修改 `ScriptRunner`，注入可选 `ScreenImageLocator` 并传给条件评估模块

## 3. 脚本需求分析和应用层装配

- [x] 3.1 新增 `script_requirements` 测试，覆盖图片条件、嵌套图片条件和无图片条件
- [x] 3.2 修改 `script_requirements`，新增 `needs_image_locator`
- [x] 3.3 新增应用层 `run_script` 测试，覆盖 dry-run 图片存在/不存在、真实运行按需注入 locator 和 setup 错误
- [x] 3.4 修改 `run_script`，支持 dry-run 图片模板配置和真实 image locator factory
- [x] 3.5 修改本地桌面 composition，把真实 image locator factory 接入脚本运行用例

## 4. CLI 和示例脚本

- [x] 4.1 新增 CLI 测试，覆盖 `--dry-run-image` 参数、图片等待 demo 成功/超时和真实运行注入 image locator
- [x] 4.2 修改 CLI，支持可重复 `--dry-run-image <template-path>` 参数
- [x] 4.3 新增 `wait-until-image-demo` 命名脚本并注册到默认 catalog
- [x] 4.4 更新 README，记录 `ImageExists`、`wait-until-image-demo` 和 dry-run 验证命令

## 5. 验证

- [x] 5.1 运行领域模型、条件评估、runner、应用层和 CLI 聚焦测试
- [x] 5.2 运行 `.venv/bin/python -m pytest`
- [x] 5.3 运行 `openspec validate add-image-exists-condition --strict`
- [x] 5.4 运行 `openspec validate --specs --strict`
- [x] 5.5 运行 `git diff --check`
