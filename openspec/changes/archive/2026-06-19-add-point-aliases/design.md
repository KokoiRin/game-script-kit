## Context

现有脚本点击固定位置时只能直接使用 `Point`。这符合执行模型，但裸坐标缺少语义，不利于维护和未来前端生成脚本。本 change 只处理固定点位别名，不处理图片别名、匹配结果、anchor 或 offset。

## Goals / Non-Goals

**Goals:**

- 提供 `PointRef` 表达“引用一个命名点位”。
- 提供 `NamedPoint` 和 `TargetCatalog` 表达脚本可用的点位资源。
- 让 `Click(PointRef("头像"))` 在 runner 中解析为 `Point` 后继续执行。
- 保持 `Click(Point(...))` 的现有行为不变。

**Non-Goals:**

- 不处理图片资源、图片匹配或图片点击。
- 不处理点位 offset。
- 不引入外部配置文件或 UI 管理。
- 不新增任何平台 adapter 或平台依赖。

## Decisions

### Decision 1: 点位别名是 portable 领域概念

点位名称和固定坐标都是脚本语义，不依赖真实设备或平台权限，因此放在 `portable.domain`。runner 只消费这些领域对象。

### Decision 2: 脚本携带资源目录

为了让命名点位随脚本一起被执行和测试，`Script` 增加默认空资源目录。这样内置脚本可以声明自己的 `TargetCatalog`，调用方不用额外改入口参数。

### Decision 3: runner 解析引用，adapter 不知道别名

`PointRef` 只在 runner 执行前被解析为 `Point`。`InputDevice` 仍然只接收最终屏幕坐标，不学习名称或资源目录。

## Risks / Trade-offs

- [Risk] `Script` 增加字段可能影响现有构造代码。→ Mitigation：字段提供默认空目录，现有三参数构造保持兼容。
- [Risk] 后续图片别名也需要目录。→ Mitigation：先把目录命名为 `TargetCatalog`，但本轮只实现点位分支，后续 change 扩展图片分支。
