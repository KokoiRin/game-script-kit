## ADDED Requirements

### Requirement: CLI 提供界面状态命名区域裁剪导出

系统 SHALL 提供命令行区域裁剪导出入口，用于把当前屏幕中的状态识别命名区域保存为独立图片。裁剪导出 MUST 复用 application 层截图诊断用例和状态配置解析，不得在 CLI 入口层直接截图、裁剪或解析状态配置。

#### Scenario: 保存命名区域裁剪图

- **WHEN** 用户运行 `star capture-region-crops`
- **AND** `assets/screen-states.json` 配置了命名区域
- **THEN** CLI 为每个命名区域保存一张裁剪图
- **AND** stdout 输出每个裁剪图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 区域裁剪导出失败

- **WHEN** 截图 adapter 不可用、屏幕尺寸不可用、状态配置非法、缺少状态配置或缺少命名区域
- **AND** 用户运行 `star capture-region-crops`
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
