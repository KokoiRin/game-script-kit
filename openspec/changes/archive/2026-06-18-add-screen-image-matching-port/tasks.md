## 1. 领域模型

- [x] 1.1 新增图像模板领域模型测试，覆盖非空路径保留和空路径拒绝
- [x] 1.2 实现 `ImageTemplate` 值对象并从领域包导出
- [x] 1.3 新增图像匹配结果领域模型测试，覆盖矩形、中心点、置信度保留和非法置信度拒绝
- [x] 1.4 实现 `ImageMatch` 值对象并从领域包导出

## 2. Engine Port 和测试替身

- [x] 2.1 在 `engine.ports` 中新增 `ScreenImageLocator` Protocol，保持独立于 `InputDevice` 和 `PixelColorReader`
- [x] 2.2 新增 fake/dry-run 图像定位实现测试，覆盖预设匹配和未找到路径
- [x] 2.3 实现 fake/dry-run 图像定位 adapter，供后续应用层和脚本语义测试复用

## 3. 桌面图像定位 Adapter

- [x] 3.1 新增桌面 adapter contract 测试，使用 fake `pyautogui` backend 覆盖成功匹配、指定 `region`、未找到和 setup 错误
- [x] 3.2 实现 `PyAutoGuiScreenImageLocator`，延迟加载平台依赖并把后端匹配结果转换为 `ImageMatch`
- [x] 3.3 覆盖 `min_confidence < 1.0` 的依赖/后端能力检查，确保不支持置信度匹配时报告清晰错误
- [x] 3.4 从 desktop adapters 包导出 `PyAutoGuiScreenImageLocator`

## 4. 装配与文档

- [x] 4.1 在本地桌面 composition 中提供真实图像定位 adapter factory，暂不改变脚本运行公开行为
- [x] 4.2 更新 README，说明屏幕图像匹配端口、macOS 屏幕录制权限和后续 `ImageExists`/图片定位点击路线

## 5. 验证

- [x] 5.1 运行针对领域模型、fake locator 和桌面 adapter 的聚焦测试
- [x] 5.2 运行 `.venv/bin/python -m pytest`
- [x] 5.3 运行 `openspec validate add-screen-image-matching-port --strict`
- [x] 5.4 运行 `openspec validate --specs --strict`
- [x] 5.5 运行 `git diff --check`
