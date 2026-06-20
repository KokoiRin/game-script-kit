## Context

`load_config_scripts()` 当前按目录读取 `scripts/*.json`，任意文件解析失败都会抛出异常。`load_project_script_catalog()` 直接把解析结果合并进 `ScriptCatalog`，所以一个坏文件会导致 CLI list/details/run 和 UI 默认装配整体失败。

## Goals / Non-Goals

**Goals:**

- 加载文件脚本时隔离单个坏文件。
- 保留 strict loader 用于测试和需要“遇错即停”的场景。
- 为项目 catalog 提供结构化 `script_config_errors`，供 CLI/UI 展示。
- 重复脚本名称也作为配置错误处理，保留先出现的有效脚本。

**Non-Goals:**

- 不做 UI 内修复或编辑脚本文件。
- 不改变文件脚本 JSON DSL。
- 不让无效脚本出现在可运行脚本列表中。

## Decisions

1. **新增 tolerant 结果对象，不把错误塞进 `ScriptCatalog`。**
   - 理由：catalog 的职责仍是保存可运行脚本集合；配置错误是项目装配结果的一部分。
   - 备选：让 `ScriptCatalog` 直接保存错误。这样会污染已有内置脚本 catalog 和测试。

2. **保留 `load_config_scripts()` strict 行为，新增 tolerant loader。**
   - 理由：已有底层测试依赖 strict 错误；同时项目运行需要部分成功。
   - 备选：直接改变 `load_config_scripts()` 语义。风险是隐藏调用方原本想捕获的配置错误。

3. **CLI list 通过 stderr 展示配置错误。**
   - 理由：stdout 保持脚本名列表可被管道消费，错误信息不混入可用脚本列表。

4. **UI 在 `/api/scripts` payload 中带 `script_config_errors`。**
   - 理由：这是脚本列表加载时最自然的可见位置；HTTP adapter 只转发 application 层结果，不解析配置。

## Risks / Trade-offs

- [Risk] 用户可能忽略 stderr 或 UI 错误区。→ Mitigation：错误文本包含文件名和原因，后续可再做更强提示。
- [Risk] 重复名保留先出现脚本可能让用户困惑。→ Mitigation：错误文本明确哪个文件被跳过以及原因。
