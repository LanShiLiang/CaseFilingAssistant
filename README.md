# Case Filing Assistant

面向中国大陆申请强制执行场景的法律文书辅助生成项目。

当前 MVP 定位为本地单机工具：服务于本人办理、只有一名申请执行人和一名被执行人、无代理人的简单案件。系统读取民事调解书、民事判决书、身份信息和履行材料，形成带来源的规则候选，经用户人工确认后生成申请强制执行材料草稿。

## MVP 边界

- 不需要登录、注册、用户管理、组织管理、权限管理或后台管理台。
- 不实现移动 Web、微信小程序、云存储或平台运营模块。
- 不自动向法院提交、立案、缴费、送达、联系法院或对外发送材料。
- 全国性法律、司法解释和最高人民法院规则作为基础规则。
- 地方法院差异通过可配置规则包和风险提示处理，不把 MVP 限定到某个地区。
- 所有事实和生成字段必须可追溯到用户材料、用户填写内容或明确规则来源。
- 关键事实必须经用户确认后才能进入导出文书。
- 不支持共同申请人、多个被执行人、代理人、组织主体和复杂履行关系；检测到后必须提示当前版本不适用。

## 当前决策

- P0 固定使用 `self_single_v1` 流程，只允许一名申请执行人、一名被执行人和一项主要金钱给付义务。
- OCR、正则、词典和版面规则优先提取高确定性字段；复杂字段识别失败时由用户手工补充。
- MVP 不实现生成式 AI、模型配置或外部模型调用；本地 OCR 属于材料读取能力。
- 规则校验、金额计算和 DOCX 生成采用已确认的结构化字段、确定性规则和版本化模板。
- 每次事实或申请内容变化都使旧校验和旧文书失效，避免导出与当前数据不一致的材料。
- 第二版再增加“自己是当事人/我是律师”入口、复杂角色和律师可选 AI，当前只保留规划文档。
- 前端基线为 Next.js App Router + Redux Toolkit + RTK Query；后端基线为 FastAPI + PostgreSQL + 独立 worker。

## 仓库结构

```text
case-filing-assistant/
|-- outputs/              # 产品与技术方案文档
|-- work/                 # 本地分析和临时材料，不提交 Git
|-- README.md
`-- .gitignore
```

后续代码落地时建议扩展为：

```text
apps/
  web/                    # Next.js 本地 Web 工作台
services/
  api/                    # FastAPI API、领域模块和基础设施适配器
  worker/                 # 文档解析和文书生成 worker
packages/
  contracts/              # OpenAPI 快照和 RTK Query 生成配置
  ui/                     # 共享 token 和领域无关 UI 组件
  doc-fields/             # 字段 key 和展示元数据
  redaction/              # 脱敏工具
compose.yaml              # web、api、worker、postgres 本地编排
```

## 方案文档

- [产品方案](outputs/产品方案_全国版强制执行材料生成助手.md)
- [前端技术方案](outputs/前端技术方案_全国版强制执行材料生成助手.md)
- [后端技术方案](outputs/后端技术方案_全国版强制执行材料生成助手.md)
- [中国大陆全国版产品范围与实施计划](outputs/mainland_china_enforcement_assistant_scope_plan_zh.md)
- [英文产品范围与实施计划](outputs/application_enforcement_assistant_scope_plan.md)

## 本地开发

当前仓库处于方案与工程初始化阶段。代码实现、OCR 依赖和环境变量说明会随脚手架落地补充。

MVP 目标启动形态：

```text
docker compose up --build
```

启动后在本机浏览器访问 `http://127.0.0.1:3000`，上传材料并生成本地导出文件。开发模式可以由 Turborepo 启动 Web、API 和 worker，并使用 Compose 运行 PostgreSQL。

## 安全说明

不得把真实案件材料、身份证件、联系方式、银行账户、签名、印章、OCR 中间结果或生成的案件文书提交到 Git。测试数据必须使用完全虚构的信息。

`work/`、上传件、OCR 缓存、导出文件、环境变量和密钥必须保持在 `.gitignore` 保护范围内。
