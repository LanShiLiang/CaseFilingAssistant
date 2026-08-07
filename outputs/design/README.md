# Case Filing Assistant 设计交付

本目录用于产品审核、视觉统一和实现对照，不包含真实案件材料或个人敏感信息。

## 文件说明

- `case-filing-assistant-design.html`：交互式设计稿源文件。建议通过本地 HTTP 服务打开，不要直接使用 `file://` 地址。
- `case-filing-assistant-canva-resource.pptx`：可导入 Canva 的 16:9 设计资源，共 15 页。设计基础、组件和状态页由可编辑文字及基础图形构成；完整界面页为高保真截图参考。
- `case-filing-assistant-canva-resource-preview.png`：整套 Canva 资源的缩略图总览。

## Canva 导入

在 Canva 中选择“导入文件”，上传 `case-filing-assistant-canva-resource.pptx`。导入后应人工检查中文字体替换、文字换行和组件对齐。

## 产品边界

- 仅面向中国大陆强制执行申请材料生成。
- 仅生成供人工审阅的文件，不执行立案、提交、缴费、送达或联系法院等外部行为。
- 示例姓名、案号、证件号码和金额均为虚构或脱敏内容。
