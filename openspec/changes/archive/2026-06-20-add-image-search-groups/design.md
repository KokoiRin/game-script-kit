## Context

这轮需求不是完整脚本变量系统，但要让当前改动朝“值变量语义”演进：静态搜索定义可以被命名和复用，运行时匹配结果后续可以自然成为脚本里的值。

现有模型中：

- `ImageTarget` / `ImageExists` 已经有 `region`，但搜索参数挂在具体动作或条件上。
- `TargetCatalog` 只管理点位和图片别名。
- `ScreenStateCandidate` 只保存 `name + ImageTemplate`。
- `ScreenImageBatchLocator.locate_many` 接收模板列表和一个共享区域，无法表达每张图不同区域。

## Goals / Non-Goals

**Goals:**

- 引入 `ImageSearchSpec`，统一表达图片、区域和最低置信度。
- 引入 `NamedRegion` 和 `NamedImageSearch`，让区域和搜索任务能被命名管理。
- 让状态探测候选使用 `ImageSearchSpec`。
- 让批量定位能在一张截图上执行多条带独立区域的搜索请求。
- 让本地状态识别优先读取 `assets/screen-states.json`，以状态组为单位执行匹配。

**Non-Goals:**

- 不实现脚本变量、赋值、表达式或作用域。
- 不新增 UI 区域拖拽录入。
- 不要求脚本立即支持 `SearchRef` 语法。
- 不做多尺度匹配、降采样或并行匹配。

## State Group Semantics

状态配置文档使用状态组表达场景：

```json
{
  "regions": {
    "右上弹窗": {"left": 1800, "top": 120, "width": 700, "height": 500}
  },
  "groups": [
    {
      "state": "战斗失败",
      "searches": [
        {"name": "离开按钮", "image": "离开.png", "region": "右上弹窗", "min_confidence": 0.8},
        {"name": "重来按钮", "image": "重来.png", "region": "右上弹窗", "min_confidence": 0.8}
      ]
    }
  ]
}
```

语义：

- `groups` 顺序是状态优先级。
- 一个 group 对应一个状态名称。
- group 内任意搜索项命中，即认为该状态命中。
- 组内和组间都按顺序早停。
- 图片路径相对 `assets/` 目录解析，仍禁止逃逸出 `assets/`。

## Decisions

1. **先做搜索规格，不做变量系统。**
   - 理由：搜索规格是未来运行时值的静态来源；先把 `image + region + threshold` 收束起来，可以避免脚本和状态识别各自长出一套语义。

2. **状态组配置放在 `assets/screen-states.json`。**
   - 理由：它描述的是素材和搜索区域，和图片资源生命周期一致；同时 application 层可以负责路径校验，不让领域层知道文件系统。

3. **批量定位使用搜索请求列表。**
   - 理由：性能关键在于一轮只截图一次，但每个搜索请求可以裁剪自己的区域后匹配。

4. **保留 assets 扫描回退。**
   - 理由：现有 UI 和用户习惯不应立即失效。没有配置文档时，系统继续把 `assets/` 图片作为全屏状态候选。

## Risks / Trade-offs

- JSON 配置需要手写坐标，短期不如 UI 拖拽直观；但它让搜索内容先从脚本流程中分离出来。
- group 内使用 any-of 语义，无法表达“多个标识必须同时命中”；后续如有必要再扩展 matcher 类型。
- batch port 变更会触及 adapter 和 fake；需要用测试确认旧调用方仍可通过兼容方法工作。
