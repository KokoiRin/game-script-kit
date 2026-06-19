## 1. 领域目标模型

- [x] 1.1 新增 `ImageTarget` 领域模型测试，覆盖默认值、搜索区域、最低匹配置信度、offset 和非法置信度
- [x] 1.2 实现 `ImageTarget` 并导出
- [x] 1.3 扩展 `Click` 测试，覆盖 `Click(ImageTarget(...))` 与既有 `Click(Point(...))`
- [x] 1.4 修改 `Click` 类型，使其目标支持 `Point | ImageTarget`

## 2. Runner 图片目标解析

- [x] 2.1 新增 runner 测试，覆盖图片目标点击中心点、offset、区域窗口解析、最低置信度传递、未找到和缺少 locator
- [x] 2.2 修改 runner，将 `Click(ImageTarget(...))` 解析为最终屏幕 `Point`
- [x] 2.3 保持 `Click(Point(...))` 既有窗口解析和 dry-run 输出不变

## 3. 需求分析和应用层

- [x] 3.1 新增 `script_requirements` 测试，覆盖图片目标点击需要 image locator
- [x] 3.2 修改 `script_requirements`，递归识别 `Click(ImageTarget(...))`
- [x] 3.3 新增应用层测试，覆盖 dry-run 图片目标点击成功、未找到和真实运行注入 image locator
- [x] 3.4 确认 `run_script` 复用现有 dry-run/真实 image locator 注入路径

## 4. CLI 和示例脚本

- [x] 4.1 新增 CLI 测试，覆盖 `click-image-demo` dry-run 成功、未找到和真实运行注入 image locator
- [x] 4.2 新增 `click-image-demo` 命名脚本并注册到默认 catalog
- [x] 4.3 更新 README，记录 `ImageTarget`、`click-image-demo` 和 dry-run 验证命令

## 5. 验证

- [x] 5.1 运行领域模型、runner、requirements、application 和 CLI 聚焦测试
- [x] 5.2 运行 `.venv/bin/python -m pytest`
- [x] 5.3 运行 `openspec validate add-image-target-click --strict`
- [x] 5.4 运行 `openspec validate --specs --strict`
- [x] 5.5 运行 `git diff --check`
