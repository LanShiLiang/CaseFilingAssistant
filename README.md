# Case Filing Assistant

面向中国大陆申请强制执行场景的本地法律文书辅助生成项目。

当前可靠 MVP 只服务一种简单场景：用户本人办理，只有一名自然人申请执行人和一名自然人被执行人、无代理人，并依据一份民事调解书或民事判决书处理一项明确的金钱给付义务。系统从材料形成带来源候选，经用户人工确认后生成申请强制执行材料草稿。

> 当前仓库处于方案与工程初始化阶段，尚无可运行应用、依赖锁、迁移或 Compose 编排，**目前不能一键启动**。文档中的启动命令是下一阶段目标；通过健康链路、端到端和制品审计前不得宣称已可用。

## MVP 边界

- 不需要登录、注册、用户管理、组织管理、权限管理或后台管理台。
- 桌面 Web 是视觉与效率基准；同一 Next.js 应用必须保证移动 Web 可完成首页门禁和四步核心流程，不建立第二套业务流程。
- 当前不实现微信小程序；`apps/miniprogram` 仅表示未来客户端方向，不参与 MVP 构建或发布。
- 不自动向法院提交、立案、缴费、送达、联系法院或对外发送材料。
- 全国性法律、司法解释和最高人民法院规则作为基础；地方法院差异通过可配置规则包和风险提示处理。
- 所有事实和生成字段必须可追溯到用户材料、用户填写内容或明确规则来源。
- 关键事实必须经用户确认后才能进入导出文书；任何事实或申请内容变化都会使旧校验和旧文书失效。
- 不支持共同申请人、多个被执行人、代理人、组织主体和复杂履行关系；检测到后明确提示当前版本不适用。
- 产物只是草稿，必须由用户人工复核、签章并自行核对目标法院要求。

## 当前技术决策

- P0 固定使用 `self_single_v1` 四步流程：当事人与依据、申请内容、检查与预览、导出。
- OCR、正则、词典和版面规则优先提取高确定性字段；识别失败允许用户手工补充。
- MVP 不实现生成式 AI、模型配置或外部模型调用；本地 OCR 只负责材料读取。
- 规则校验、金额计算和 DOCX 生成采用已确认结构化字段、确定性规则和版本化模板。
- 前端目标为 pnpm workspace + Turborepo + Next.js App Router + Redux Toolkit/RTK Query。
- 后端目标为单一 FastAPI/Python 模块化单体 + PostgreSQL；API、worker、migrate 复用同一代码和镜像、使用不同入口。
- OpenAPI 是跨端协议来源；未来微信小程序只复用 contracts、design tokens 和纯领域映射，不复用 DOM UI。

## 仓库状态与结构

当前已有结构：

```text
apps/
  web/                    # MVP Web 占位，尚无代码
  miniprogram/            # 未来方向占位，不进入 MVP 构建
services/
  api/                    # 单 Python 后端占位，未来含 api/worker/migrate
packages/
  contracts/              # OpenAPI/生成类型边界占位
  design-tokens/          # 跨端纯数据 token 占位
  ui/                     # Web/DOM 通用组件占位
infra/                    # Compose/健康检查/制品审计占位
outputs/                  # 产品、设计、技术和架构研发输入
```

不要为占位目录添加无法运行的空泛脚手架。进入实施阶段时，按[项目架构与工程化规范](outputs/项目架构与工程化规范.md)一次完成代码、锁文件、健康检查、测试和可复现启动。

## 方案文档

- [产品方案](outputs/产品方案_全国版强制执行材料生成助手.md)
- [前端技术方案](outputs/前端技术方案_全国版强制执行材料生成助手.md)
- [后端技术方案](outputs/后端技术方案_全国版强制执行材料生成助手.md)
- [项目架构与工程化规范](outputs/项目架构与工程化规范.md)
- [开发与仓库规范](outputs/开发与仓库规范.md)
- [中国大陆全国版产品范围与实施计划](outputs/mainland_china_enforcement_assistant_scope_plan_zh.md)
- [英文产品范围与实施计划](outputs/application_enforcement_assistant_scope_plan.md)

`outputs/` 可以进入 Git 供研发审核，但必须被 Docker build context 和最终 runner allowlist 排除。运行代码不得读取其中的设计稿、需求或方案。

## 目标启动方式

工程实现完成后的统一目标命令是：

```bash
docker compose up --build
```

目标服务链路为：PostgreSQL health → migrate one-shot success → API/worker → Web。浏览器只访问 `http://127.0.0.1:3000`，API 和数据库留在 Compose 内部网络。

只有以下验收全部通过后，README 才能把本节从“目标”改为“可用”：

- 干净环境能执行命令，迁移和所有健康门禁正确。
- 桌面与移动 Web 的虚构样本四步闭环通过。
- worker 中断、重试、重启和旧 revision 拒绝发布通过。
- DOCX/PDF/PNG 实际渲染和视觉核验通过。
- 最终镜像不含 `outputs/`、设计/需求文档、测试材料、上传件、OCR 缓存、导出件、secret 或本机绝对路径。

停止服务不得默认删除 volume；数据销毁必须使用单独、明确确认的操作。

## 安全说明

不得把真实案件材料、身份证件、姓名、证件号、联系方式、地址、银行账户、签名、印章、OCR 中间结果或生成案件文书提交到 Git。测试数据必须完全虚构且显著标识为测试用途。

`work/`、上传件、数据库、OCR 缓存、导出文件、环境变量、密钥、测试 trace、截图和本地报告必须保持在 `.gitignore` 与 `.dockerignore` 保护范围内。发现疑似真实个人信息或 secret 时先停止传播，完成隔离、脱敏复核或凭据轮换后再继续。
