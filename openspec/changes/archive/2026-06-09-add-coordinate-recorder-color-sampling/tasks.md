## 1. 领域模型和端口

- [x] 1.1 新增 `tests/test_color_model.py`，覆盖合法 RGB、非法通道值和字段保留行为
- [x] 1.2 新增 `src/game_automation/domain/color.py` 的 `Color` 值对象，并从 `src/game_automation/domain/__init__.py` 导出
- [x] 1.3 修改 `src/game_automation/engine/ports.py`，新增 `PixelColorReader.read_color(point: Point) -> Color` 协议
- [x] 1.4 运行 `.venv/bin/python -m pytest tests/test_color_model.py -v` 验证颜色模型

## 2. 桌面取色 Adapter

- [x] 2.1 新增 `tests/test_desktop_pixel_color.py`，用 fake pyautogui backend 覆盖 RGB 和 RGBA 像素返回
- [x] 2.2 新增 `src/game_automation/adapters/desktop/pixel_color.py`，实现 `PyAutoGuiPixelColorReader`
- [x] 2.3 更新 `src/game_automation/adapters/desktop/__init__.py`，导出 `PyAutoGuiPixelColorReader`
- [x] 2.4 测试 adapter 读取失败时抛出清晰 `RuntimeError`，并运行 `.venv/bin/python -m pytest tests/test_desktop_pixel_color.py -v`

## 3. 坐标记录器接入颜色

- [x] 3.1 修改 `tests/test_coordinate_recorder.py`，增加 fake color reader，并断言实时输出包含当前坐标和颜色
- [x] 3.2 修改 `tests/test_coordinate_recorder.py`，断言按 `1` 记录时返回和保存包含 `Point` + `Color` 的记录对象
- [x] 3.3 修改 `tests/test_coordinate_recorder.py`，断言结束汇总逐条打印坐标和颜色，空记录仍打印 `(none)`
- [x] 3.4 修改 `src/game_automation/tools/coordinate_recorder.py`，新增 `RecordedPoint`，通过注入的 `PixelColorReader` 同步读取颜色
- [x] 3.5 运行 `.venv/bin/python -m pytest tests/test_coordinate_recorder.py -v` 验证业务工具行为

## 4. CLI 组装和错误处理

- [x] 4.1 修改 `tests/test_script_cli.py` 或新增 CLI 测试，覆盖 `star recorder` 会组装 `PyAutoGuiPixelColorReader`
- [x] 4.2 修改 `src/game_automation/star_cli.py`，启动 recorder 时同时注入 `PyAutoGuiPointerPositionReader`、`TerminalKeyStateReader` 和 `PyAutoGuiPixelColorReader`
- [x] 4.3 测试颜色读取 setup 失败时 CLI 返回非零退出码，并输出清晰错误
- [x] 4.4 运行 `.venv/bin/python -m pytest tests/test_script_cli.py tests/test_coordinate_recorder_adapters.py -v`

## 5. 文档和回归验证

- [x] 5.1 更新 `README.md` 的坐标记录工具说明：实时显示和记录都会包含颜色，并补充截图/屏幕录制权限提示
- [x] 5.2 运行 `.venv/bin/python -m pytest`，确认全部测试通过
- [x] 5.3 运行 `.venv/bin/star list` 和 `.venv/bin/star run demo --dry-run`，确认脚本入口未受影响
- [x] 5.4 如当前环境允许交互和截图，手动运行 `.venv/bin/star recorder` 验证输出包含坐标和颜色；若权限不足，记录实际错误信息
- [x] 5.5 将 `openspec/changes/add-coordinate-recorder-color-sampling/tasks.md` 中已完成任务勾选，并运行 `openspec status --change "add-coordinate-recorder-color-sampling"`
