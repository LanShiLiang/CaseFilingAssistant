# CaseFilingAssistant 项目协作指引

## 语言与沟通

- 项目方案、产品文档、界面文案和面向团队的说明默认使用简体中文。
- 技术标识、代码符号、协议名称和无法准确翻译的专有名词可以保留英文。
- 重要技术决策应说明理由、风险、替代方案和验证方式。
- 代码应优先通过目录、类型、函数和变量命名表达意图；中文注释用于解释法律/业务不变量、revision 失效原因、并发与事务边界、兼容性取舍，不得用逐行翻译语法的注释掩盖职责混乱。

## 任务启动与证据基线

- 开始实现、诊断或评审前，必须阅读 `README.md`、根目录 `AGENTS.md` 和 `outputs` 中与任务直接相关的产品、前端、后端、架构方案；不得只凭对话摘要或历史记忆修改代码。
- 用户要求依据 commit、PR 或 review 评论工作时，必须同时检查顶层评论和文件行内评论，记录评论链接、文件、行号和原文；先把评论归纳为职责、契约、不变量、测试或文档问题，再决定整改，不能只在被评论行附近增加注释或机械拆文件。
- 开始写入前检查 `git status --short`、相关 diff、当前分支和正在运行的进程；共享工作区中未提交改动默认属于用户或其他 Agent，禁止覆盖、回滚、清理或顺手格式化无关文件。
- 评审和事实判断必须引用当前代码、配置或可复现命令；方案描述、README 声明和文件名本身不能作为“已实现、已测试、可发布”的证据。

## 授权与变更边界

- “评审、诊断、分析、给建议”默认只允许读取并输出报告，不授权修改业务代码、依赖、数据库、GitHub 状态或发布物；只有用户明确要求实现/修复时才落地代码。
- 用户限定“仅架构优化”时，只调整职责、边界、依赖方向、契约、可靠性结构及其文档/测试支撑，不改产品规则、页面业务行为、法律文案、输出模板结论或 MVP 支持范围。
- 发现需要扩展产品范围、引入外部服务、改变数据保留策略、改写已发布迁移或执行破坏性操作时，必须停止并请求明确授权，不得把这些动作包装成“架构优化”。
- 优化应以当前模块化单体为默认：没有经过吞吐、隔离或运维数据证明，不拆微服务、不引入 Redis/Celery、不复制 API/worker 领域实现，也不为未来微信小程序提前建立第二套规则或 UI。

## 产品范围

- 产品仅面向中国大陆法律及司法规则。
- MVP 聚焦根据用户上传的证据、调解书、判决书等材料，生成可人工审阅的申请强制执行材料包草稿。
- 全国性法律、司法解释和最高人民法院规则作为基础规则；地方法院差异通过可配置规则包处理。
- 所有生成事实和关键字段必须能追溯到用户材料、用户填写内容或明确标注的权威来源。
- 必须保留人工复核、来源展示、不确定项提示和用户最终确认。
- 不实现自动立案、法院提交、缴费、送达、联系法院或其他外部法律行为。

## 数据与安全

- 不得把真实案件材料、身份证件、姓名、身份证号、详细地址、电话、银行账户、签名、印章或其他个人敏感信息提交到 Git。
- 不得把真实案件材料、仓库中的本地运行数据或可识别个人信息发送给外部模型、第三方插件、在线 OCR、遥测或错误上报服务；需要验证 AI/外部能力时，只能使用明确虚构且可公开的样本，并先确认任务授权和数据流向。
- 测试数据必须完全虚构，并使用明显的占位符或专用测试样本。
- 日志不得记录用户材料正文、OCR 全文、访问令牌、私钥或敏感字段明文。
- 上传件、OCR 缓存、生成文书、导出文件、环境变量和密钥必须遵守 `.gitignore`。
- 发现疑似真实个人信息时，应先停止传播和提交，完成脱敏与复核后再继续。
- Agent 不得因工具可用就自行安装或执行第三方脚本、hooks、skills、网络 agent 或新增运行时依赖；只有任务确有必要且用户已授权时才可使用，并在交付中说明来源、锁定方式、制品影响和验证结果。

## 工程结构

- `apps/web`：MVP 的同一套桌面 Web 与响应式移动 Web；桌面是视觉和效率基准。
- `apps/miniprogram`：未来微信小程序方向；MVP 中仅占位，不参与默认构建、测试或发布。
- `services/api`：单一 Python 项目；API、worker、迁移通过独立入口复用领域、迁移、规则、模板和依赖锁，不创建第二套 `services/worker`。
- `packages/contracts`：OpenAPI 快照、生成类型、稳定错误码和无 UI 协议工具。
- `packages/design-tokens`：跨端纯数据 token，不包含 DOM 或案件领域模型。
- `packages/ui`：Web/DOM 通用组件，不直接复用到微信小程序。
- `infra`：容器、部署、监控和环境配置。
- `outputs`：产品、设计、技术和架构研发输入；不得作为运行依赖或进入镜像、安装包、发布压缩包。

## 实施原则

- 在代码、锁文件、迁移、健康检查、测试和制品审计真实落地并通过前，不得用占位 Compose/package/Dockerfile 或静态配置宣称可以一键启动；已存在的能力也必须按当前环境重新区分“静态检查通过”和“运行验收通过”。
- 优先沿用仓库既有技术栈、目录边界和共享契约，避免无关重构。
- 文书生成必须采用结构化字段、确定性模板和版本化规则，不允许仅依赖自由文本生成。
- OCR、模型抽取和规则匹配结果必须包含来源位置、置信度和人工确认状态。
- 桌面 Web 是 MVP 的基准体验；移动 Web 必须用同一业务流程完成核心闭环。微信小程序是后续实现，届时保持适用门禁、来源、确认、阻断和草稿边界一致，但不得直接复用 DOM UI 或在小程序端复制服务端法律规则。
- 前后端契约以 OpenAPI 为来源，生成客户端禁止手改；服务端是适用范围、revision、校验和生成门禁的唯一权威。
- API、worker、migrate 使用同一 Python package 和 frozen lock；MVP 不为 worker 复制领域模型、schema、迁移、规则或模板。
- 生产构建采用 build-context denylist 与最终 runner allowlist 双层隔离；禁止先复制整个仓库再删除 `outputs`。
- 修改共享契约、文书模板、规则引擎或隐私处理逻辑时，应增加针对性测试。

## 前端职责与依赖方向

- 页面和顶层工作台组件只负责组合 controller hook、步骤视图、通用 UI 与路由结果，不得同时实现协议参数拼装、幂等策略、任务轮询、revision 决策、字段转换和四个步骤的完整 JSX。
- 每个业务动作应有命名明确的 application/controller hook，例如“创建已确认适用事项”“保存当事人与依据”“请求生成”；hook 负责编排 query/mutation、取消轮询、稳定错误码和成功后的缓存失效，纯视图只接收展示数据与事件回调。
- 步骤组件、上传控件、字段编辑器和状态面板按 feature 分文件；拆分必须形成清晰单向依赖，禁止仅为了缩短文件把同一闭包状态散到多个无语义 helper 中。
- 架构验收看职责、依赖方向、正确性和独立可测性，不把单文件行数、目录层数、组件数量或是否引入 Storybook 当作 KPI。
- 服务端状态与本地草稿分离。可达步骤、校验结果、生成资格和权威金额由服务端响应派生；浏览器本地状态只管理未提交输入和展示状态，不得建立第二套业务状态机。
- OpenAPI 是协议唯一事实来源。先用 Pydantic 显式 model/`Literal` 固化状态、来源、gate、错误码和嵌套对象，再生成消费者；`packages/contracts` 的生成文件禁止手改，API 参数和响应必须由生成类型/客户端或其薄增强层消费，不得在 `apps/web` 再维护同构手写 `Matter`、endpoint 或协议常量。不能用 codegen 掩盖服务端的 `dict[str, Any]` 或模糊 `str` schema。
- JavaScript `Number` 只能用于非权威展示；法律金额的解析、舍入、合计与校验由服务端 decimal 规则完成，前端展示服务端返回的值和计算依据。
- Next.js 同源 route 只负责受控转发、header allowlist、大小限制、取消与 `no-store`；上传应流式处理，不得无界 `arrayBuffer` 整体缓冲，也不得把内部 API 地址或敏感响应写入客户端缓存。

## 后端职责与依赖方向

- FastAPI route 只做请求解析、协议校验、幂等/上下文获取、application use case 调用和错误映射；不得直接承载事务编排、ORM 状态跃迁、生成门禁或文件发布逻辑。
- application use case 是 API 与 worker 复用业务动作的入口，负责事务边界和领域操作顺序；只为并发、存储和测试定义窄 repository/事务端口，domain/value object 表达 revision、来源、确认和校验不变量。禁止用一个通用 `services.py` 持续堆叠跨领域过程函数，也禁止为统一形式引入 BaseRepository、通用 UoW/CQRS、service locator 或依赖注入容器。
- extraction 只产生带来源位置、置信度、提取器版本和复杂性信号的候选；候选不能覆盖已确认事实。适用范围、校验、金额和生成资格始终由服务端规则决定。
- 耗时解析不得持有旧 ORM 状态作为发布依据。解析完成后必须在新的短事务中按 matter ID 与 input revision 重新锁定/读取，以当前数据库 JSON 为 merge base，只更新仍未 confirmed 的字段；revision 不匹配或 job 已失租时将结果标记为 superseded，不回写事实、来源或确认状态。
- `facts`、`sources`、`confirmations` 即使在 MVP 中继续存 JSON，读取和写入也必须经过带 `schema_version` 的 Pydantic/value object 校验；禁止由 route、worker 和 renderer 各自解释无版本字典。
- 文书生成必须先冻结 `ConfirmationSnapshot`/`GenerationContext`，记录 matter、revision、规则版本、模板版本、来源和内容 hash。renderer 只消费不可变快照，不得在慢任务中直接读取可变 ORM `Matter` 或未确认候选。
- DOCX renderer、PDF renderer、材料清单、来源核对表和 ZIP/manifest assembler 应按职责分离；渲染器不访问数据库，assembler 不重新计算法律事实，artifact 只有在 hash、size、manifest 与 revision 校验通过后才能发布。
- BlobStore 使用 opaque key 和临时写入/原子发布协议；数据库/API/日志不得暴露本机绝对路径。存储、OCR、LibreOffice/Poppler 等外部依赖通过窄接口和 capability 暴露，错误分类必须区分输入错误、瞬时资源错误和不可恢复错误。

## Revision、任务与迁移不变量

- 改变事实、来源、确认、金额或目标法院时必须推进 revision，并使旧 validation、preview、generation 和 artifact 明确失效；任何可见步骤解锁都不能仅依赖前端缓存。
- job claim 必须返回 job ID、lease token、leased-until 和输入 revision；heartbeat、完成、失败及 artifact 发布均使用“当前状态 + lease token”的条件更新（CAS）。失租或 revision 过期的 worker 可以清理临时结果，但不得写回终态或发布当前结果。
- 长任务必须续租；重试采用有限次数、退避和 jitter，并按稳定错误类型决定是否重试。任务处理器只编排 handler，lease repository、retry policy、业务 handler 和 artifact publisher 不得揉成无法独立测试的单类。
- PostgreSQL、SQLite 的并发能力差异必须在测试和 capability 中明确；不能用 SQLite 串行测试证明 PostgreSQL `SKIP LOCKED`、租约竞争或连接池行为正确。
- 已发布迁移不得改写。后续 Alembic revision 使用显式 `op.*` 描述 DDL，不得以 `metadata.create_all/drop_all` 代替可审查迁移；每次 schema 变更至少验证空库升级、上一受支持版本升级和失败后不会启动 API/worker。
- schema、snapshot 或 artifact manifest 演进必须声明兼容策略和版本转换；无法兼容时应明确阻断，不得静默按新结构解释旧数据。

## 测试与审查矩阵

- 测试应对准职责边界：纯 view/component 测交互与可访问性，controller hook 测 query/mutation/轮询和恢复，application use case 测事务与不变量，repository 测数据库语义，worker 测 lease/CAS/失租/重试，renderer 测确定性 golden 与视觉结果。
- OpenAPI 变更必须执行生成与 no-diff 漂移检查，并至少有一个前端消费者编译/契约测试；禁止仅提交更新后的快照而不验证实际客户端。
- revision、确认、来源、金额、生成或任务可靠性变更，必须覆盖：旧 revision 拒绝发布、失租 worker 拒绝回写、重复请求幂等、修改后旧文书失效以及中断/重启恢复。
- 迁移测试必须使用目标数据库 PostgreSQL；SQLite 可保留作快速本地测试，但不能替代锁、事务、decimal、JSON 和连接池的集成验收。
- DOCX/PDF/ZIP 变更必须验证确定性字段、manifest、hash、占位符清理，并实际渲染检查分页、字体、表格、页眉页脚、签章位置和字段溢出。
- 修复 review 评论时，测试名称应表达被保护的不变量；只有可复现验证通过后才能把评论标记为已处理，不能以“已拆文件”或“已加注释”代替验收。

## CI、制品与事实一致性

- Pull request 硬门禁至少包含 format/lint、typecheck、前后端单测、OpenAPI no-diff、PostgreSQL/worker 集成、生产构建和 artifact audit；发布候选再执行桌面/移动 E2E、容器 smoke、迁移路径和文书视觉核验。
- Compose/Web 启动只依赖 API ready，不把 worker 健康混入 API liveness；worker 或 OCR/渲染依赖异常时，由 API capability 返回脱敏降级码并由服务端阻断相关写操作，事项查看和可恢复操作仍应可用。
- artifact audit 必须检查实际最终镜像/发布包的文件清单和内容，而不只扫描源码目录；最终 runner 使用 allowlist，build context 使用 denylist，且禁止先复制整个仓库再删除 `outputs`。
- 最终制品不得包含 `outputs/`、设计/需求文档、测试 fixture/trace/coverage、本地数据库、上传/OCR/导出件、secret、本机绝对路径或未替换占位符；例外许可证文件必须显式 allowlist。
- `README.md`、方案、测试报告和 release 说明必须区分：设计目标、静态验证、当前机器运行验证、外部环境待验证。Docker daemon 不可用时不得宣称 Compose 已运行通过；功能实现变化后同步更新文档，禁止让计划态文档覆盖当前事实。
- 架构报告必须明确列出“哪里实现不好、为何有风险、应改什么、如何验收、当前不做什么”，并标出 P0/P1/P2；建议不得把未来能力写成当前 MVP 已完成。

## 交付与验证

- 提交前运行与变更范围匹配的格式检查、类型检查和测试。
- 提交前检查 `git status --short`、`git diff --check` 和 staged diff；不得覆盖或清理他人未提交改动。
- 提交前逐项核对变更是否超出用户授权，检查生成文件是否由对应命令产生，确认新增依赖、迁移、外部网络和制品变化均有必要性与验证证据。
- 生成 DOCX 或 PDF 时必须进行渲染和视觉核验，检查分页、表格、字体、页眉页脚及字段溢出。
- 容器或发布物变更必须列出最终文件并运行 artifact audit，确认不含 `outputs/`、设计/需求方案、测试材料、本地案件数据、secret 或本机绝对路径。
- 一键启动目标为 `docker compose up --build`；只有 PostgreSQL 健康、一次性迁移、API/worker/Web 健康链路、持久化恢复、E2E 和制品门禁全部通过后才可标记为可用。
- 最终报告应列出变更文件、验证结果、未完成风险和需要人工确认的事项。
- 不得把本地生成的案件文书或用户上传材料作为演示文件提交到仓库。
- 多 Agent 协作时，每个 Agent 只能修改任务明确分配的文件；主 Agent 在汇总前必须读取实际 diff、处理报告冲突并重新运行合并后的验证，不能直接把子 Agent 的结论当作已确认事实。
- Git 提交应按单一目的组织，提交前审阅 staged diff；未经用户明确要求不推送、不创建 PR、不发布、不改写历史。提交/推送后报告准确的 commit、branch、远端结果和仍未纳入的工作区改动。
