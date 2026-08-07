# Case Filing Assistant v0.1.0 前后端架构 Review 报告

版本：v1.0

评审日期：2026-08-07

评审对象：`89b46505ff18a4468e82b92d618d2d6f0aa36ce2`（`v0.1.0`）

评审范围：仅评审前后端架构、工程边界和可靠性结构；不调整产品范围、法律规则、界面设计或业务行为。

## 1. 结论

当前项目的技术方向基本正确：Next.js + RTK Query、FastAPI 模块化单体、单一 Python 包承载 API/worker/migrate、PostgreSQL 任务队列、OpenAPI 契约和本地 Blob 存储，都适合可靠 MVP。主要问题不在选型，而在“方案中的边界没有落实到代码结构”：

1. 前端把页面、工作流编排、服务端状态轮询、未提交表单、错误处理和业务派生集中在一个 408 行组件中，已经形成高耦合工作台。
2. OpenAPI 虽能生成类型，但运行时仍维护手写领域类型和手写 RTK Query endpoints，存在双事实来源。
3. 服务端 route、事务、应用用例和领域判断仍混在 `api.py`/`services.py`；worker 的 lease token 没有参与续租和完成时的条件更新，可靠性承诺尚未闭环。
4. 解析 worker 会在耗时处理后基于陈旧 ORM/JSON 回写候选，存在覆盖用户刚确认字段的竞态；这是当前最紧急的正确性风险。文书生成直接读取可变 ORM `Matter`，则使验证与生成输入缺少可审计的一致性证明。
5. 现有迁移、CI 和制品审计主要证明“代码可运行和源码目录干净”，还不能证明数据库可演进、worker 可恢复、最终镜像只包含 allowlist 文件。

因此，本次建议继续保持模块化单体，不拆微服务、不引入 Redis/Celery、不创建第二套前端或法律规则；用三轮小步重构把既定边界真正落地。

## 2. Commit 评论核对

GitHub 提交页显示顶层 commit comment 为 0，但文件 diff 中存在 3 条行内评论：

| 位置 | 评论 | 架构含义 |
|---|---|---|
| `apps/web/src/components/HomePage.tsx:19` | “比较黑盒，不知道这个代码的作用” | 创建事项的 command、适用条件版本、幂等键和错误处理没有通过命名良好的应用 hook 表达。 |
| `apps/web/src/components/MatterWorkbench.tsx:118` | “应该使MatterWorkbench干净点，只有hooks和UI组件，其他的模块，依赖函数，方法都封装到对应的文件” | 工作台组件承担了查询、mutation、轮询、未提交表单、步骤门禁和视图渲染，缺少容器/用例/视图分层。 |
| `apps/web/src/components/MatterWorkbench.tsx:182` | “这些组件封装到外面，全部依赖的组件都写在一个文件太难阅读，使项目结构也不够语义化” | `UploadControl`、`Field`、四步页面及动作函数都在同一文件，无法从目录判断职责，也不利于独立测试。 |

评论链接：

- [HomePage 行内评论](https://github.com/LanShiLiang/CaseFilingAssistant/commit/89b46505ff18a4468e82b92d618d2d6f0aa36ce2#r195193242)
- [MatterWorkbench 组件边界评论](https://github.com/LanShiLiang/CaseFilingAssistant/commit/89b46505ff18a4468e82b92d618d2d6f0aa36ce2#r195193929)
- [MatterWorkbench 文件结构评论](https://github.com/LanShiLiang/CaseFilingAssistant/commit/89b46505ff18a4468e82b92d618d2d6f0aa36ce2#r195193550)

这些评论判断正确，但“多写中文注释”只能缓解阅读成本，不能解决职责耦合。正确整改方式是让代码结构和命名直接表达用例，关键不变量再用中文注释解释原因。

## 3. 优先级总览

| 优先级 | 问题 | 当前风险 | 建议动作 |
|---|---|---|---|
| P0 | 解析 worker 基于陈旧 ORM/JSON 回写 | 用户在解析期间确认字段后，旧 worker 可能把已确认值覆盖为旧值或 pending | 耗时解析脱离事务；发布时新开短事务并按 revision/token 重读、合并当前 JSON |
| P0 | worker lease 只在领取时写入，完成/失败未按 token CAS，长任务无续租 | 任务超时被再次领取后，旧 worker 仍可能回写；“至少一次执行、一次发布收敛”未被代码保证 | 返回 `ClaimedJob(id, token)`，heartbeat 续租，所有终态更新匹配 token 与状态 |
| P0 | 缺少真实 PostgreSQL 并发回归网 | SQLite 顺序测试不能证明 `SKIP LOCKED`、lease expiry 和陈旧 worker 的语义 | 先建立 barrier 驱动的 PostgreSQL 竞态测试，再改 worker |
| P0 | 产品适用范围未形成结构化服务端规则链 | 当前校验只有必填、确认和金额关系，缺少多当事人、代理人、组织主体、多义务等不可绕过 blocker | 建立规范化 Dossier/ComplexitySignal 和版本化 ProductScopeRules |
| P1 | 生成读取可变 ORM，而非版本化纯数据输入 | 难以证明生成物与校验上下文完全一致 | 分步建立 `ValidationRunV1`/`GenerationInputV1`，renderer 只读纯数据 |
| P1 | OpenAPI 与手写类型/endpoints 双轨 | 协议变更可通过生成检查，却仍与真正被 UI 使用的手写类型不一致 | 先强化 Pydantic/OpenAPI schema，再删除手写 shape；是否生成全部 hooks 按收益决定 |
| P1 | `MatterWorkbench` 是 God Component | 修改任一步骤都会影响轮询、未提交表单、生成和其他步骤，测试只能走整页 | 拆成 controller hook、步骤 feature、纯 UI 和工作流 presenter |
| P1 | 前端复制步骤门禁与金额权威逻辑 | 客户端与服务端可能显示不同可达步骤或金额；JS `Number` 不适合法律金额权威计算 | 服务端返回 `step_gates`/`AmountComputation`；前端只做非权威预览 |
| P1 | route、应用用例、事务和 ORM 混层 | 业务不变量散落，API 与 worker 难复用同一用例 | 按 matters/documents/validation/generation 划分显式 use case 与窄持久化适配器 |
| P1 | `facts/confirmations/sources` 使用无版本裸 JSON | schema 演进、来源失效和审计规则依赖约定，缺少结构化校验 | MVP 继续用 JSON 列，但写入/读取必须经过版本化 Pydantic snapshot/value object |
| P1 | 幂等策略只覆盖创建事项 | 上传、生成和其他修改型 command 没有统一 request fingerprint/idempotency policy | 在应用命令层统一幂等键、请求摘要、冲突和安全重试语义 |
| P1 | 文书生成模块同时负责上下文、DOCX/PDF、清单和 ZIP | 模板版本、渲染器、清单校验无法独立演进与测试 | 拆 `context`、renderer、package assembler、manifest verifier |
| P1 | 材料没有显式 active/version/invalidated 生命周期 | 同类材料替换后旧记录仍参与集合判断，来源失效只能依赖隐式“取最新”约定 | 建立材料版本聚合与单一 active 约束，替换时原子失效来源和旧结果 |
| P1 | 发布门禁缺少 CI 和真实镜像审计 | 本地脚本通过不等于 PR 或 release 可复现；当前 audit 没检查最终镜像 | 增加 GitHub Actions、容器 smoke、image allowlist 和 SBOM/secret scan |
| P1 | Compose 把 Web 启动绑定到 worker healthy | worker 故障时 Web 无法启动，与“可查看事项并显示降级”目标冲突 | Web 只依赖 API ready，worker 状态通过 capability 控制解析/生成 |
| P2 | 初始迁移使用 `create_all/drop_all` | 不能审阅精确 DDL，未来 schema 漂移和 downgrade 风险高 | 不改写已发布 0001；后续迁移显式 `op.*`，增加空库/升级路径测试 |
| P2 | 同源代理把上传完整读入 `arrayBuffer` | 大文件同时占用浏览器、Next.js 和 API 内存，移动端与并发下放大 | 引入受限流式代理，保持 header allowlist 和 `no-store` |
| P2 | readiness/observability 只覆盖 DB 查询和存储写探针 | 无法判定迁移版本、模板/规则清单、队列停滞和渲染能力 | 增加结构化 capability、迁移 head、模板 manifest 与队列指标 |

## 4. 前端架构 Review

### 4.1 `HomePage` 创建逻辑不可读

证据：`HomePage.tsx:18-28` 的 `handleCreate` 同时负责清错误、组装 eligibility command、硬编码版本、生成幂等键、调用 mutation、跳转和错误转换。

实现不好的地方：

- `handleCreate` 的名称只描述事件，不说明业务动作是“以已确认适用条件创建事项”。
- `self_single_v1.0.0` 在页面中硬编码，后续版本切换需要修改 UI。
- 幂等键策略和协议错误映射藏在组件里，其他入口容易实现成另一套。
- `parseApiError` 只返回中文 message，组件无法按稳定 error code 做恢复。

建议改为：

```text
features/eligibility/
  eligibility.contract.ts
  useCreateEligibleMatter.ts
  EligibilityGate.tsx
  createEligibleMatter.test.ts
```

`HomePage` 只组合 `useListMatters`、`useCreateEligibleMatter` 和 UI。hook 暴露 `{create, pending, error, reset}`，内部负责 command、幂等键、稳定错误码和成功跳转。适用条件版本从生成契约或 runtime capability 获得，不由页面散落常量控制。

验收：HomePage 组件测试不 mock `crypto` 或拼接协议参数；应用 hook 独立覆盖重复点击、`409 idempotency_key_reused`、API 不可用和成功跳转。

### 4.2 `MatterWorkbench` 过重，评论指出的是结构问题

证据：

- 文件 408 行；`UploadControl` 位于 44 行、`Field` 位于 84 行、主组件位于 118 行。
- 主组件持有事项、任务、生成、7 个本地状态和 7 个 query/mutation 生命周期。
- `handleUpload`、`saveStepOne`、`saveStepTwo`、`runValidation`、`generate`、`confirmAndUnlock` 全部定义在页面组件中。
- 四个步骤的完整 JSX 都在同一返回树中。

实现不好的地方：

- 任何 mutation 或轮询策略变化都迫使修改主视图文件。
- 页面通过闭包共享 `matter/revision/fields`，难以看出每个动作真正依赖什么。
- 步骤 UI 无法单独 Storybook/Testing Library 验证；只能构造整个工作台。
- 组件既是 server-state controller，又是 workflow state machine，又是表单容器。

建议目标结构：

```text
apps/web/src/features/matter-workbench/
  MatterWorkbench.tsx              # 仅组合 controller 与步骤视图
  MatterWorkbenchView.tsx          # 布局与状态分支
  useMatterWorkbenchController.ts  # 聚合 hooks，不渲染 JSX
  workflowPresenter.ts             # 服务端状态到 UI 展示态的纯映射
  components/
    MatterHeader.tsx
    StepNavigation.tsx
    Field.tsx
    UploadControl.tsx
  steps/
    PartiesAndBasisStep.tsx
    ApplicationStep.tsx
    ReviewStep.tsx
    ExportStep.tsx
  hooks/
    useRevisionDraft.ts
    useDocumentUpload.ts
    useGenerationLifecycle.ts
```

约束：

- controller hook 只能编排生成的 API hooks，不写法律规则。
- step 组件通过窄 props 接收数据与 command，不直接访问整个 store。
- `Field`/`UploadControl` 如无案件语义可放 `packages/ui`；含来源、材料 kind 或 revision 语义时留在 feature。
- 不按“每 50 行一个文件”机械拆分；以可独立测试的职责为边界。

验收：主文件只保留 hooks 与 UI 组合；每一步有独立组件测试；上传、revision 冲突、终态停止轮询和生成失效有 controller/hook 测试。

不以文件行数、目录层数或是否引入 Storybook 作为验收 KPI；只验证模块是否单一职责、业务动作能否独立测试、依赖是否单向。

### 4.3 前端复制服务端权威规则

证据：`domain.ts:54-64` 根据材料和确认字段推导四步门禁，`domain.ts:26-31` 用 JS `Number` 计算尚未履行金额；`MatterWorkbench.tsx:152-157` 将二者直接用于导航和显示。

实现不好的地方：

- 方案明确服务端是 step gate 和金额的唯一权威，但当前 `MatterResponse` 没有 `step_gates`，迫使前端复制规则。
- JS `Number` 的浮点和范围语义不能作为法律金额最终值。
- 前端 helper 的测试会固化第二套规则，未来后端修改后容易产生“服务端阻断、前端已解锁”的错觉。

建议：

- `MatterResponse` 增加结构化 `step_gates`，至少包含 `state/code/reason_ids`；导航只映射展示状态。
- 服务端保存申请时返回版本化 `AmountComputation`（decimal 字符串、输入 revision、formula version、result、confirmation state）。
- 客户端允许即时显示“未保存预估值”，但不得用它解锁校验/生成；服务端响应到达后覆盖为权威值。
- 删除 `deriveStepGates` 的领域判断，仅保留 `toStepNavigationView` 这类展示映射。

### 4.4 契约存在双事实来源

证据：

- `packages/contracts/src/generated.ts` 是 OpenAPI 生成物。
- `packages/contracts/src/index.ts:1-97` 又手写 `DocumentKind`、`JobStatus`、`Matter`、`Generation` 等类型，只在 99 行重新导出生成类型。
- `apps/web/src/store/caseApi.ts` 手写 `UploadResult`、`GenerationStartResult` 和全部 endpoint。

实现不好的地方：`contracts:check` 只能证明 OpenAPI 快照和 `generated.ts` 同步，不能证明页面真正使用的手写类型/endpoints 与它们同步。

此外，当前只有创建事项传递 `Idempotency-Key`；上传、生成和最终确认等修改型 command 没有共享的幂等策略。revision 可以阻止部分重复写入，但不能替代“相同 command 安全重试、相同 key 不同 payload 拒绝”的协议语义。

建议：

```text
packages/contracts/
  openapi.json
  src/generated.ts          # 自动生成，禁止手改
  src/errorPolicy.ts        # 仅稳定错误码到无 UI 策略的映射
apps/web/src/store/api/
  caseApi.ts                # 直接引用生成 operations/components 的薄 adapter
  apiPolicy.ts              # tags、轮询、幂等与错误归一化
```

先把服务端普通 `str`、`dict[str, Any]` 收紧为 Pydantic `Literal` 和显式嵌套 response model；否则 codegen 只会自动生成模糊契约。随后删除手写协议 shape，增强层不得重新声明响应结构。endpoint 可先保留薄 RTK Query adapter，但入参与返回值必须直接引用生成的 `operations/components`；只有 endpoint 数量或多客户端收益明确时，才生成全部 hooks。CI 除 no-diff 外，增加真实前端消费者的类型编译和关键 enum 穷尽检查。

幂等键应在 API adapter policy 或应用 hook 中统一注入，服务端 use case 统一计算不含敏感正文的 request fingerprint；route 不各自发明处理方式。

### 4.5 RTK Query 生命周期与工作流状态混合

证据：`MatterWorkbench.tsx:119-150` 同时轮询 Matter、Job、Generation，并在 effect 中手工 `refetch`；active step 是本地 `useState(1)`。

实现不好的地方：

- 活动任务结束后 query 仍由局部条件间接控制，页面可见性、卸载和事项切换没有统一策略。
- active step 可以和服务端门禁脱节，刷新后总回到步骤 1。
- mutation 后既使用 tag invalidation 又手工 refetch，缓存职责不清晰。

建议：

- 用经过服务端 gate 校验的 URL search param 或其他可恢复导航状态表达步骤；MVP 不强制拆成四个页面路由，服务端 `step_gates` 决定是否可达。
- `useJobPolling(jobId)` 统一活动态/终态、页面可见性、abort 和退避。
- mutation 只依赖明确 tags 或 `updateQueryData`；只在确有竞态的地方手工 refetch。
- `useGenerationLifecycle` 统一 generation/job/revision 三者，不由页面自行拼接 `effectiveGenerationId`。

### 4.6 前端测试层次不足

当前仅有首页门禁组件测试、4 个 domain helper 测试和 1 条 E2E。主工作台没有组件/controller 测试，手写契约没有运行期 schema 验证。

架构重构后优先补：

1. controller hook：上传、保存、冲突、任务终态、旧 generation 失效。
2. 每个 step：输入输出和服务端 gate 的展示映射。
3. generated client：关键请求头、multipart、错误码与 enum 穷尽。
4. 同源代理：超限、流式上传、502 和敏感 header allowlist。

## 5. 后端架构 Review

### 5.1 API route 承担应用用例和事务

证据：`api.py:196-347` 的 validate、start generation、confirm、preview 和 download route 直接查询 ORM、比较 revision、调用规则、提交事务并拼装下载门禁；`list_matters` 也直接构造 SQLAlchemy 查询。

实现不好的地方：

- route 不再是协议适配器，API 成为唯一能执行这些用例的入口。
- worker 或未来小程序后端入口无法复用同一 command handler，只能复制逻辑。
- 事务边界散在 route 和 `services.py`，无法统一审计“锁定—校验—写入—失效—提交”。

建议保持单体但按用例分层：

```text
app/
  api/routes/                 # HTTP 转换、header、response
  application/
    matters/commands.py
    documents/commands.py
    validation/commands.py
    generation/commands.py
  domain/                     # value objects、规则和不变量
  persistence/               # 仅按并发与测试需要提供窄 SQLAlchemy 适配器
  infrastructure/            # LocalBlobStore、renderers、clock
```

不要引入通用 CQRS、BaseRepository、全局 UoW 框架或依赖注入容器。每个修改型用例使用一个显式 use-case function 和一个清楚的事务；只为并发更新、存储故障注入等实际需要定义窄端口，route 只调用 use case。

### 5.2 确认卷宗缺少版本化类型边界

证据：`models.py:29-31` 将 `facts`、`confirmations`、`sources` 保存为无 schema version 的 JSON；`services.py:310-376` 通过字符串集合和字典变更维护它们。

实现不好的地方：

- 字段 value、来源和确认状态可以形成不一致组合。
- 无法明确区分候选、用户确认值、确定性派生值和失效值的 schema 版本。
- 未来字段变化只能依赖散落的字符串判断，历史事项难迁移。

MVP 优化方式不是立即拆十几张表，而是：

- 建立 `DossierV1`、`ConfirmedFieldV1`、`SourceRefV1`、`AmountComputationV1` Pydantic value object。
- JSON 列保留，但任何写入先通过类型校验，并保存 `dossier_schema_version`。
- repository 负责 ORM JSON 与 domain object 转换，应用层不直接改裸 dict。
- 对来源失效和 revision 推进建立单一 `revise_dossier()` 入口。

### 5.3 缺少版本化、不可变的生成输入

证据：`generation.py` 的所有 renderer 直接接收 ORM `Matter`；`jobs.py:114-151` 在 worker 执行时重新读取当前 Matter 并传给 `generate_package`。当前只有 revision 比较，没有保存生成上下文 hash 或 validation snapshot 关联。

实现不好的地方：revision 比较可以挡住明显旧任务，但不能证明“校验看见的数据”和“生成看见的数据”来自同一个不可变结构，也让 renderer 依赖数据库模型。

建议作为 P1 紧随并发修复分步落地：

1. 先定义 `GenerationInputV1`，在启动生成的短事务中从已确认字段构造、校验、序列化并持久化，保存 matter revision、schema/rule/template version、source/confirmed hash。
2. worker 只按 generation ID 读取这份纯数据输入，不再重新读取可变 ORM `Matter`。
3. 保存最小 `ValidationRunV1`（input hash、rule version、issues、passed、created_at），让 Generation 引用批准它的 validation run。
4. 若后续确有跨运行复用需要，再把两者抽象成独立 `ConfirmationSnapshot`；MVP 不同时建立多套语义相近的 DossierRevision/Snapshot/Context 表。
5. renderer 禁止导入 SQLAlchemy model；发布前同时校验 lease token、generation 状态、input hash 和当前 revision。

验收：在 validation 后修改事实、任务执行中修改事项、旧 worker 延迟完成三种情况下，旧产物均不能成为当前下载项。

### 5.4 产品适用范围规则没有落到服务端结构

证据：`validation.py` 当前只有一个 `validate_matter()`，检查 eligibility、必填/确认字段和金额关系；代码中没有 `unsupported_multiple_applicants`、`unsupported_multiple_respondents`、`unsupported_representative`、`unsupported_organization_party`、`unsupported_multiple_obligations` 或 `unsupported_complex_obligation` 的结构化规则。现有 API 流测试使用 SQLite 和单一支持样本，不能证明复杂事项会被阻断。

实现不好的地方：首页 attestation 只能提示用户，不能替代上传材料后的服务端识别和最终生成门禁。如果解析只取第一个姓名/金额，复杂材料可能被压扁为表面上完整的单一事项。

建议：

- 先建立固定 `DossierV1`（一名 applicant、一名 respondent、一项 monetary obligation）和 `ComplexitySignalV1`，不开放通用新增角色 API。
- validation 按 `ProductScopeRules -> ConfirmedDataRules -> NationalBaselineRules -> TemplateReadinessRules` 顺序执行，scope blocker 不允许前端忽略。
- extraction 只产生候选和复杂性信号，不直接决定或覆盖最终角色。
- generation handler 必须重新核对 snapshot 的 `scope_supported=true` 和零 blocking。
- 增加多当事人、代理人、组织主体、多项义务的虚构负样本，验收生成记录数为 0。

### 5.5 P0：解析任务可能覆盖用户已确认字段

证据：`jobs.py:75-108` 在开始耗时 PDF/OCR 解析前把 `Matter` 加载进 Session；解析结束后比较的仍是该 Session 内的 `matter.revision`，没有重新刷新或加锁。用户若在此期间保存字段，数据库已经进入 N+1，但 worker 仍可能看到内存中的 N 并用旧 `facts/sources/confirmations` JSON 提交覆盖。

整改要求：

1. claim 后只读取不可变任务输入，耗时解析在不持有业务事务和 ORM aggregate 的阶段完成。
2. 发布解析结果时开启新的短事务，按 matter ID + expected revision 加锁并重新读取当前 JSON。
3. 只有 revision 匹配、当前字段仍未 confirmed 时才合并候选；merge base 必须是数据库最新值。
4. job/document 状态更新同时匹配 lease token；失租或 revision 不匹配只收敛为 superseded，不发布候选。
5. PostgreSQL 测试使用 barrier/fake slow parser 稳定复现“解析中用户保存”，不能用 sleep 碰运气。

### 5.6 worker lease 可靠性未闭环

证据：

- `jobs.py:28-54` 领取时写入 `lease_token/leased_until`，但只返回 job ID。
- `process`、`_parse_document`、`_generate_package` 和 `_record_failure` 更新时不匹配 lease token。
- 长任务期间没有 heartbeat 延长 `leased_until`；只有 `run_forever` 写进程 heartbeat 文件。
- 解析/生成输出写 Blob 后才提交数据库，失租或提交失败可能遗留孤儿文件。

实现不好的地方：当前结构不能严格保证过期 worker 不回写，也不能让租约覆盖长 OCR/生成任务。

建议：

```text
JobQueue.claim() -> ClaimedJob(job_id, lease_token, input_revision)
JobLease.heartbeat(claimed_job)
JobHandler.handle(command) -> HandlerOutcome
JobPublisher.publish(claimed_job, outcome)  # WHERE id/token/status=running
```

- handler 运行期间独立 heartbeat；续租失败立刻停止发布。
- success/failure/retry 全部使用 `id + lease_token + status=running` 条件更新并检查 affected row。
- 错误按稳定 classifier 区分 terminal/retryable，不使用“所有 ValueError 都终态”。
- artifact 先写 staging key，CAS 发布成功后才移动到正式 key；失败/失租进入有界 cleanup。
- 对 SQLite 本机模式明确降级为单 worker，不宣称验证了 PostgreSQL 并发语义。

### 5.7 文书生成是第二个 God Module

证据：`generation.py` 423 行，同时负责 Word 字体/布局、申请书、材料清单、来源表、PDF 预览、manifest 和 ZIP；所有入口均接收 ORM `Matter`。

建议结构：

```text
generation/
  context.py              # GenerationContextV1
  registry.py             # template/rule/schema version 选择
  renderers/
    application_docx.py
    checklist_docx.py
    source_audit_docx.py
    preview_pdf.py
  package.py              # ZIP + manifest
  verify.py               # placeholder、可打开、hash、页数
```

共享字体/段落 helper 可保留，但 renderer 不互相调用、不访问 ORM/Session/Settings。模板版本由 registry 明确选择，不只是在 manifest 中记录字符串。

### 5.8 材料版本和 LocalBlobStore 边界都不完整

`Document` 当前没有 `active/invalidated/parse_revision/storage_status/replaced_by` 等生命周期字段；上传同类材料只新增记录，`matter.documents` 仍保留全部历史项，而前端和 validation 都用“集合里是否出现 kind”判断门禁。与此同时，`services.py`、`api.py`、`jobs.py` 都直接依赖 `LocalBlobStore`，下载 route 通过 `path_for()` 暴露本机路径概念给 API 层。

建议建立材料聚合内的显式版本关系和每种主材料的单一 active 约束；替换时在同一事务内激活新版本、失效旧来源、推进 revision，并使旧 validation/generation 过期。再定义小而真实的 `BlobStore` Protocol：`stage/open/publish/delete`，让下载应用服务返回受控 stream + metadata。MVP 仍只有 Local 适配器，不增加 S3；Protocol 的价值是隔离发布语义和测试故障，不是为了提前多云。

### 5.9 迁移不适合长期演进

证据：已发布的 `0001_initial.py` 使用 `Base.metadata.create_all()` 和 `drop_all()`。

处理原则：

- 不改写已经随 v0.1.0 发布并可能被使用的 0001。
- 从 0002 起使用显式 `op.create_table/add_column/create_index` 等前向迁移。
- CI 同时验证空库升级和 v0.1.0 数据库升级；生产 downgrade 默认不作为恢复策略，恢复依赖备份与前向修复。
- 增加 schema drift 检查，避免 ORM 改了但迁移未提交。

### 5.10 readiness 与观测不足

`/health/ready` 当前只查询 DB 并检查存储可写，未检查 Alembic head、规则/模板 manifest 或关键渲染能力。worker health 证明进程写过 heartbeat 文件，但不能证明队列正在推进或 lease 没有堆积。

建议在不记录敏感内容的前提下增加：migration revision、template/rule manifest version、队列深度/最老等待时长、lease expiry、job error code、阶段耗时。对外 capability 只返回状态与稳定错误码，不返回路径、文件名或正文。

### 5.11 幂等记录的并发冲突没有收敛

`create_matter()` 当前采用“先查询 idempotency record，再插入事项与唯一记录”。两个相同 key 的并发请求可能在唯一约束处得到数据库异常，而不是稳定返回第一次响应。

建议把幂等处理放在 use case 事务边界：相同 key + 相同 fingerprint 返回首次结果；相同 key + 不同 fingerprint 返回稳定 `409 idempotency_key_reused`；唯一冲突时回滚并重读记录。fingerprint 只保存规范化 command hash 和文件 SHA-256，不保存请求正文。用真实 PostgreSQL 增加同 key 并发测试。

## 6. 工程与发布架构 Review

### 6.1 缺少仓库内 CI

仓库没有 `.github/workflows`。`pnpm verify` 是良好的本地聚合入口，但发布门禁目前依赖人工运行，无法证明 PR 和 tag 都执行了同一套检查。

建议增加最小 GitHub Actions：

1. `quality`：lint、typecheck、web/backend tests、contracts no-diff。
2. `postgres-worker`：真实 PostgreSQL 下的 lease/revision/snapshot 集成测试。
3. `build-artifact`：Web/后端镜像构建、容器 smoke、最终文件清单、denylist/allowlist、secret scan。
4. `e2e`：虚构材料完成桌面和移动闭环；release tag 必须依赖前三项成功。

依赖使用 lockfile，Action 固定 major 或 commit SHA；测试 fixture 只使用明显虚构数据。

### 6.2 当前 artifact audit 名称大于能力

`scripts/artifact-audit.ps1` 只扫描 `apps/packages/services/infra` 源码中的少量扩展名，并确认 `.dockerignore` 含若干字符串。它没有列出或扫描最终 Docker image/filesystem，也没有检查本机绝对路径、secret、层大小和 runner allowlist。

建议将现脚本更名或降级为 `source-boundary-audit`，新增真实 `image-artifact-audit`：

- 导出最终容器文件清单和镜像层。
- Web 只允许 standalone/static/运行依赖；后端只允许 venv/app/migrations/runtime resources。
- 检查 `outputs`、设计/需求文档、tests、Git、本地数据、密钥模式、本机绝对路径和异常大文件。
- 输出机器可读报告并作为 release artifact；禁止用“先复制再删除”掩盖中间层。

### 6.3 同源代理会缓冲整个上传

`apps/web/src/app/api/v1/[...path]/route.ts:35` 对非 GET 请求调用 `arrayBuffer()`。20MB 上限下单请求尚可，但并发、移动设备和后续扩大文件上限时会形成额外内存副本。

建议建立受控 proxy adapter：保留请求/响应 header allowlist、`no-store`、内部 URL 不下发，上传正文采用 bounded streaming，并为上游超时、取消、413/502 增加集成测试。

### 6.4 worker 降级目标与 Compose 启动条件冲突

架构规范要求 worker 故障时 Web 仍能打开并展示降级原因，但 `compose.yaml` 当前让 Web 同时依赖 API 和 worker healthy；worker 初始故障时 Web 根本不会启动，`CapabilityResponse` 也没有表达 worker 在线/队列可处理状态。

建议 Web 只依赖 API ready；API capability 聚合脱敏的 worker heartbeat、OCR/渲染依赖和稳定降级码。事项查看继续可用，上传解析/生成由服务端 capability 阻断；worker 健康不应混入 API liveness。

## 7. 推荐实施顺序

### 阶段 0：先建立并发回归网

1. 新增真实 PostgreSQL integration suite，保留 SQLite 快速测试。
2. 用 barrier/fake slow parser 覆盖解析中保存、双 worker claim、失租后旧 worker 完成、生成中 revision 变化和同 key 并发。
3. 先让旧实现稳定暴露失败，再开始并发重构。

完成定义：所有目标竞态均能确定性复现，不依赖 sleep 或单进程顺序 harness。

### 阶段 1：修正 P0 正确性与发布语义

1. 解析计算与发布分离；发布时重新锁 Matter、基于当前 JSON 合并。
2. 修正 job lease：token CAS、heartbeat、staging/publish/cleanup。
3. 建立 `DossierV1`/`ComplexitySignalV1` 和 ProductScopeRules，不支持事项生成数量必须为 0。
4. SQLite 明确为单 worker 开发模式，不用它证明 PostgreSQL 并发。

完成定义：解析期间的 confirmed 字段不会被覆盖；旧 revision/失租 worker 不能写当前状态或正式 Blob；复杂事项不可生成。

### 阶段 2：固化生成输入与服务端权威状态

1. 引入 `ValidationRunV1`、`GenerationInputV1`，让 renderer 脱离 ORM。
2. 拆 generation renderers、package assembler 和 verifier。
3. 服务端返回 step gates/amount computation；前端删除权威规则复制。
4. 把 `api.py` 中修改型逻辑迁入显式 use cases。

完成定义：每个 Generation 可追溯到 validation run、input hash 和版本；修改确认事实后旧生成不可下载。

### 阶段 3：可读性与契约单轨

1. 拆 `MatterWorkbench` controller、steps、components、polling hooks。
2. 把 `HomePage.handleCreate` 提炼为命名业务 hook。
3. 强化 Pydantic/OpenAPI 状态、来源、gate 和错误码 schema。
4. 删除 TypeScript 手写协议 shape；薄 endpoint adapter 直接引用生成类型，再按收益决定是否生成全部 RTK Query hooks。

完成定义：页面组件不直接构造业务 command/事务规则；route 不直接编排 ORM 状态变更；单文件职责可由目录名说明。

### 阶段 4：发布可信度

1. 添加真实 PostgreSQL worker 集成测试、迁移升级测试和容器 smoke。
2. 增加 GitHub Actions 和真实 image artifact audit。
3. 完善 readiness/capability/worker 降级和脱敏可观测性。
4. 在有 Docker daemon 的干净环境复验 `docker compose up --build`。

完成定义：release tag 只在 CI 门禁全部通过时创建；最终镜像文件清单可审计且不含 `outputs/` 等研发资源。

## 8. 明确不做

为保持可靠 MVP，本轮架构优化明确不做：

- 不拆 FastAPI API 与 worker 为两个 Python 项目。
- 不引入微服务、Redis、Celery、Kafka、Temporal 或 Kubernetes。
- 不添加账号、权限、组织、后台管理、自动法院提交或生成式 AI。
- 不为了未来微信小程序共享 DOM UI；只稳定 OpenAPI、错误码、纯数据 token 和服务端权威状态。
- 不一次性把所有 JSON 拆成关系表；先建立版本化 domain schema 和 snapshot 边界。
- 不改写已经发布的 0001 migration 或历史 commit。

## 9. 验证清单

架构整改完成后至少满足：

- [ ] `MatterWorkbench.tsx` 仅承担 controller 与步骤视图组合，步骤和动作可独立测试，不以机械行数为指标。
- [ ] 页面不手写 eligibility version、协议响应 shape 或权威 step gate。
- [ ] OpenAPI 先用强类型 schema 固化状态/来源/gate/错误码，UI 直接消费生成类型且 no-diff 覆盖真实消费者。
- [ ] 解析期间用户保存的 confirmed 字段不会被陈旧 worker 覆盖。
- [ ] generation 引用持久化、版本化的 `ValidationRunV1`/`GenerationInputV1` 与 hash。
- [ ] 所有 job 完成、失败和续租都匹配 lease token；失租 worker 不能发布。
- [ ] renderer 不导入 ORM model，生成只消费 `GenerationInputV1`。
- [ ] 后续 Alembic migration 使用显式操作，空库和 v0.1.0 升级均通过。
- [ ] PR/tag CI 使用真实 PostgreSQL；覆盖 worker 并发、恢复和 stale revision。
- [ ] worker 不健康时 Web 仍可查看事项，并通过 capability 显示降级状态。
- [ ] 最终镜像执行 allowlist/denylist、secret、路径和大小审计。
- [ ] `docker compose up --build` 在有 Docker daemon 的干净主机完成一次全链路复验。

## 10. 人工决策点

1. 是否把“解析陈旧回写竞态 + worker lease CAS/heartbeat + PostgreSQL 并发测试”列为 v0.1.1 的 release blocker；主审与资深复核均建议是。
2. 前端步骤是否映射到独立路由，还是保留单路由 + 可验证 search param；二者均可，但不得继续仅用不可恢复的本地 `useState`。
3. 本地 SQLite 模式是否明确只支持单 worker；若保留，应在 capability 和文档中标注降级语义。
4. 是否将现有 `artifact-audit` 改名以避免过度承诺；本报告建议区分 source audit 与 image audit。
