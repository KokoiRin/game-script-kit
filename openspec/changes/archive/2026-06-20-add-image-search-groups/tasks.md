## 1. 领域搜索模型

- [x] 1.1 增加 `RegionRef`、`NamedRegion`、`ImageSearchSpec`、`SearchRef` 和 `NamedImageSearch` 领域模型。
- [x] 1.2 扩展 `TargetCatalog`，支持解析命名区域和命名图片搜索，并测试重复名称、未知名称和直接值解析。

## 2. 批量图片搜索请求

- [x] 2.1 增加批量搜索请求/结果模型，使每个请求能携带独立 region 和 min_confidence。
- [x] 2.2 更新 `ScreenImageBatchLocator` port，支持按搜索请求批量定位，并保留旧模板批量定位的兼容入口。
- [x] 2.3 更新桌面 adapter，在一次截图内按每个请求的 region 裁剪匹配，并测试只截图一次、不同 region、早停和 skipped 结果。

## 3. 状态探测使用搜索规格

- [x] 3.1 更新 `ScreenStateCandidate` 使用 `ImageSearchSpec`，并保持从单图片候选构造全屏搜索的兼容能力。
- [x] 3.2 更新 `probe_screen_state`，批量路径使用搜索请求，单图 fallback 使用候选搜索规格的区域和阈值。
- [x] 3.3 测试状态探测按状态候选搜索区域传递请求，并在命中后跳过后续候选。

## 4. 状态组配置文档

- [x] 4.1 增加 `assets/screen-states.json` 解析用例，支持 `regions` 和 `groups[].searches[]`。
- [x] 4.2 本地控制 application 优先从配置文档生成状态候选；没有配置时回退到扫描 `assets/` 图片。
- [x] 4.3 测试非法配置、路径逃逸、未知 region、空 group/search 被拒绝。

## 5. 验证和归档

- [x] 5.1 运行聚焦测试、完整 pytest、OpenSpec strict 校验和 `git diff --check`。
- [x] 5.2 归档 OpenSpec change，按项目规则提交并 push。
