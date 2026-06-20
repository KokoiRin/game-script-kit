## ADDED Requirements

### Requirement: UI 提供配置状态名候选
本地控制 UI SHALL 从 application 层获取当前配置中的界面状态名称，并把它们作为 dry-run 模拟状态输入的候选项。缺少状态配置时，系统 MUST 返回空候选列表且不阻止用户手动输入状态名。

#### Scenario: 页面加载状态候选
- **WHEN** 用户打开本地 UI 页面且 `assets/screen-states.json` 配置了 `主页` 和 `人物`
- **THEN** 页面可获取并展示 `主页` 与 `人物` 作为模拟状态输入候选

#### Scenario: 缺少配置时候选为空
- **WHEN** 用户打开本地 UI 页面但没有状态配置
- **THEN** 状态候选接口返回空列表
- **AND** 用户仍可手动输入模拟状态并运行脚本
