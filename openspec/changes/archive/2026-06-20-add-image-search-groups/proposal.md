## Why

当前脚本模型已经支持图片别名和图片目标的搜索区域，但“要找哪张图、在哪找、用什么阈值找”仍散落在动作、条件和状态探测候选里。界面状态探测目前只从 `assets/` 目录按图片文件生成候选，无法把多个图片组织成同一个场景，也无法为每个图片指定不同搜索区域。

后续脚本模型会逐步引入运行时值语义，例如匹配结果、中心点、当前状态等。现在需要先把静态搜索定义独立出来，作为未来变量和值系统的前置模型。

## What Changes

- 增加命名区域和图片搜索规格模型，统一表达 `image + region + min_confidence`。
- 增加命名图片搜索，使“离开按钮”“人物界面标识”等搜索任务可以脱离脚本流程管理。
- 状态探测候选改为使用图片搜索规格，而不是只保存图片模板。
- 批量图片定位支持一组搜索请求，每个请求可以有自己的搜索区域，并保持一轮只截图一次。
- 本地控制 application 支持读取 `assets/screen-states.json`，按文档中的状态组、图片和区域执行状态识别；没有配置文档时继续回退到扫描 `assets/` 图片文件。

## Capabilities

### New Capabilities
- `image-aliases`: 命名区域和命名图片搜索。

### Modified Capabilities
- `screen-image-matching`: 批量图片定位支持每个搜索请求自己的区域。
- `screen-state-probe`: 界面状态探测支持配置化状态组。

## Impact

- 更新领域模型：区域引用、图片搜索规格、命名图片搜索。
- 更新 batch locator port 和 desktop adapter，使批量定位接收搜索请求。
- 更新状态探测领域模型和 engine，使状态候选携带搜索规格。
- 更新本地控制 application，读取并校验 `assets/screen-states.json`。
- 增加单元测试覆盖配置解析、状态组生成、多区域批量匹配和回退行为。
