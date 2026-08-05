# Case Filing Assistant

面向中国大陆申请强制执行场景的本地法律文书辅助生成项目。

当前可靠 MVP 只服务一种简单场景：用户本人办理，只有一名自然人申请执行人和一名自然人被执行人、无代理人，并依据一份民事调解书或民事判决书处理一项明确的金钱给付义务。系统读取用户导入的执行依据和身份材料，形成带来源、置信度与确认状态的候选字段；用户逐项确认后，系统按确定性规则生成可人工复核的材料包草稿。

## 已实现能力

- 首页用 1—4 项适用条件和一个总确认框阻断不适用事项。
- 上传 PDF、DOCX、JPG、PNG；执行依据负责提取案号、法院、日期、当事人和金额等候选字段，识别失败时允许人工补充。
- 四步闭环：当事人与执行依据 → 申请内容 → 检查与预览 → 导出。
- 字段保存来源位置、置信度和人工确认状态；数据变化会提升 revision，并使旧校验、旧预览和旧导出失效。
- 后台任务采用数据库租约、重试和旧 revision 发布拦截，API、worker、迁移共用同一后端代码。
- 生成申请执行书草稿、材料清单、字段来源核对表、PDF 预览和 ZIP 材料包。
- 桌面 Web 与移动 Web 使用同一业务流程；API 通过 Next.js 同源代理，浏览器不直接连接后端。

所有输出均为草稿。系统不会登录法院，也不会代为立案、提交、缴费、送达、联系法院或实施其他外部法律行为。

## MVP 边界

- 无登录、注册、用户、组织、权限或后台管理功能。
- 当前不实现微信小程序；`apps/miniprogram` 只保留未来客户端方向，不参与 MVP 构建和发布。
- 不支持共同申请人、多个被执行人、代理人、组织主体和复杂履行关系；检测到后明确阻断。
- 全国性法律、司法解释和最高人民法院规则作为基础；地方法院差异预留版本化规则包边界。
- MVP 不调用生成式 AI 或外部模型；OCR、正则、词典和版面规则只提供候选，关键字段必须人工确认。
- 用户必须自行复核、签章，并核对目标法院的最新要求。

## 本机启动

Windows 本机开发路径已经通过联合调试。需要 Node.js 22 以上、Python 3.12 和 PowerShell；根目录使用 `pnpm@11.9.0`，Python 依赖由锁定的 `uv` 环境管理。

首次安装依赖：

```powershell
pnpm bootstrap
```

启动 Web、API、worker，并自动执行数据库迁移：

```powershell
pnpm dev
```

访问 `http://127.0.0.1:3000`。本机模式默认使用 `.local/case_filing.db` 和 `.local/storage`，日志写入 `.artifacts/dev`；这些路径均被 Git 忽略。按 `Ctrl+C` 会停止本次启动的三个子进程，不会删除本地数据。

若本机没有可用的图像 OCR 引擎，能力接口会显示 `image_ocr=false`；PDF/DOCX 文本仍可解析，身份证图片可上传并由用户手工确认字段。容器镜像已经包含 Tesseract 中文 OCR 运行依赖。

## Compose 启动

生产化本地链路已经编排为 PostgreSQL health → migrate → API/worker health → Web：

```powershell
docker compose up --build
```

浏览器仍只访问 `http://127.0.0.1:3000`，API 和数据库不暴露到宿主机。停止服务使用 `docker compose down`；不要附加 `--volumes`，除非已明确决定销毁本地数据。

当前开发机没有可用 Docker daemon，因此 Compose 文件、依赖关系和构建上下文已做静态验收，但完整容器启动仍需在安装 Docker 的主机上执行一次运行确认。用于多人或非本机环境时，必须先替换 `.env.example` 中的示例数据库密码。

## 验证

全量静态检查、前后端单元/集成测试、契约漂移检查、生产构建和制品审计：

```powershell
pnpm verify
```

桌面与移动端虚构样本端到端闭环：

```powershell
pnpm test:e2e
```

验收使用运行时生成的完全虚构材料，依次完成事项创建、材料上传、字段确认、申请内容校验、后台生成、最终确认和 ZIP 下载。测试 fixture、浏览器 trace、截图、覆盖率、上传件和生成文书只保存在被忽略的本地目录。

常用的分层命令：

```powershell
pnpm lint
pnpm typecheck
pnpm test:web
pnpm test:backend
pnpm contracts:check
pnpm build
pnpm artifact:audit
```

## 仓库结构

```text
apps/
  web/                    # Next.js App Router；桌面与移动 Web
  miniprogram/            # 未来方向，不进入 MVP 构建
services/
  api/                    # FastAPI 模块化单体、worker、迁移、规则与文书生成
packages/
  contracts/              # OpenAPI 快照和生成的 TypeScript 类型
  design-tokens/          # 跨端纯数据 token
  ui/                     # 不含案件领域模型的 Web 通用组件
scripts/                  # 安装、启动、契约、测试和制品审计入口
outputs/                  # 产品、设计、技术和架构研发输入
compose.yaml              # PostgreSQL、migrate、API、worker、Web 编排
```

`outputs/` 可以进入 Git 供研发审核，但被 Docker build context 和运行制品排除；生产代码不得在运行时读取设计稿、需求或方案文档。

## 方案文档

- [产品方案](outputs/产品方案_全国版强制执行材料生成助手.md)
- [前端技术方案](outputs/前端技术方案_全国版强制执行材料生成助手.md)
- [后端技术方案](outputs/后端技术方案_全国版强制执行材料生成助手.md)
- [项目架构与工程化规范](outputs/项目架构与工程化规范.md)
- [开发与仓库规范](outputs/开发与仓库规范.md)
- [中国大陆全国版产品范围与实施计划](outputs/mainland_china_enforcement_assistant_scope_plan_zh.md)

## 数据与安全

不得把真实案件材料、身份证件、姓名、证件号、联系方式、地址、银行账户、签名、印章、OCR 全文或生成案件文书提交到 Git。测试数据必须完全虚构并明显标识为测试用途。

`.local/`、上传件、数据库、OCR 缓存、导出文件、环境变量、密钥、测试 trace、截图和本地报告必须保持在 `.gitignore` 与 `.dockerignore` 保护范围内。日志只记录请求/任务标识、错误码、阶段和耗时，不记录材料正文或敏感字段明文。
