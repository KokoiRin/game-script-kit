## Context

Star 现在的脚本都由 Python 代码注册到 `DEFAULT_SCRIPT_CATALOG`。脚本运行、详情和 UI 都依赖 catalog 查询脚本；共享搜索和区域已经可以从 `assets/screen-states.json` 合并到脚本资源中。缺口是用户无法在项目目录里新增一个可编辑脚本文件，并让 CLI/UI 像内置脚本一样使用它。

## Goals / Non-Goals

**Goals:**

- 新增项目脚本目录 `scripts/`，加载其中的 `*.json` 脚本文件。
- 文件脚本支持最小可用步骤：`wait`、`click`、`repeat`、`if_state`、`wait_until_state`。
- 文件脚本支持引用点位、图片、搜索和状态；搜索可以继续复用命名区域。
- CLI `list/details/run` 和本地 UI 列表/详情/运行都使用合并后的项目脚本 catalog。
- 解析错误应以可读错误暴露给 CLI 或 UI，而不是在入口层散落解析逻辑。

**Non-Goals:**

- 不做 UI 内脚本编辑器。
- 不引入自然语言到脚本的编译前端。
- 不支持全部 Python 脚本模型，例如颜色判断、拖拽、任意窗口选择。
- 不改变内置脚本的 Python 注册方式。

## Decisions

1. **使用 JSON 作为第一版文件脚本格式。**
   - 理由：Python 标准库可解析，无需新增依赖；和已有 `assets/screen-states.json` 风格一致。
   - 备选：YAML/TOML。YAML 需要新增依赖，TOML 对嵌套步骤可读性一般，本轮不采用。

2. **新增 portable application 层 loader，而不是让 CLI/UI 解析脚本文件。**
   - 理由：文件读取和配置解析已经在 application 层有先例；CLI/UI 必须保持薄，只负责展示和调用用例。
   - 备选：在 `scripts_manager.catalog` 中直接读项目目录。这样会让默认内置 catalog 和项目文件系统耦合，不利于测试。

3. **文件脚本 loader 输出标准 `Script` 和 `TargetCatalog`。**
   - 理由：运行器、详情、依赖检查和 dry-run 已经围绕 `Script` 工作；复用现有语义可以最小化改动面。
   - 备选：新增一套运行时 AST。当前 DSL 还没稳定，过早增加第二套模型会扩大复杂度。

4. **项目 catalog 在 composition/入口装配处合并内置脚本和文件脚本。**
   - 理由：这符合 ports-and-adapters 的依赖方向；核心 catalog 继续只管理脚本集合，项目路径只在装配处出现。
   - 备选：每次 `list/details/run` 动态扫描。这样可以自动刷新，但会让错误处理和性能路径更分散。本轮先做启动/命令级加载。

5. **第一版 DSL 用显式动作对象，避免做“聪明解析”。**
   - 理由：后续自然语言前端可以编译到这个稳定结构；现在先保证人类可写、错误可读、测试可覆盖。

## Risks / Trade-offs

- [Risk] JSON 对用户不如 Python 灵活。→ Mitigation：第一版只承担配置脚本闭环，复杂脚本仍可继续写 Python 内置脚本。
- [Risk] UI 打开时遇到坏脚本可能影响脚本列表。→ Mitigation：本轮通过 application 层返回可读错误；后续可以增加 UI 脚本配置诊断区。
- [Risk] DSL 支持面过窄。→ Mitigation：只选当前游戏脚本最常用动作，后续按真实脚本需求扩展。
