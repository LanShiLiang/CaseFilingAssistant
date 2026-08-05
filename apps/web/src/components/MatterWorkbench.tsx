"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Check,
  Download,
  FileSearch,
  FileText,
  LoaderCircle,
  ShieldAlert,
  Upload,
  UserRound
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { DocumentKind, Matter, ValidationResult } from "@case-filing/contracts";
import { Button, StatusBadge } from "@case-filing/ui";

import {
  useConfirmGenerationMutation,
  useGetGenerationQuery,
  useGetJobQuery,
  useGetMatterQuery,
  useSaveFactsMutation,
  useStartGenerationMutation,
  useUploadDocumentMutation,
  useValidateMatterMutation
} from "@/store/caseApi";
import {
  STEP_ONE_FIELDS,
  STEP_TWO_FIELDS,
  calculateOutstanding,
  deriveStepGates,
  formatMoney,
  mergeDraftField,
  parseApiError
} from "@/lib/domain";

const STEP_LABELS = ["当事人与依据", "申请内容", "检查与预览", "导出"] as const;

type FormState = Record<string, string>;

function UploadControl({
  kind,
  label,
  accept,
  matter,
  onUpload,
  optional = false,
  disabled = false
}: {
  kind: DocumentKind;
  label: string;
  accept: string;
  matter: Matter;
  onUpload: (kind: DocumentKind, file: File) => Promise<void>;
  optional?: boolean;
  disabled?: boolean;
}) {
  const document = [...matter.documents].reverse().find((item) => item.kind === kind);
  return (
    <label className={`upload-card ${document ? "upload-card--complete" : ""}`}>
      <span className="upload-icon">{document ? <Check size={20} /> : <Upload size={20} />}</span>
      <span className="upload-copy">
        <strong>{label}{optional ? "（选填）" : ""}</strong>
        <small>{document ? `${document.filename} · ${document.parse_status}` : `选择 ${accept} 文件`}</small>
      </span>
      <input
        aria-label={`上传${label}`}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void onUpload(kind, file);
          event.currentTarget.value = "";
        }}
      />
    </label>
  );
}

function Field({
  label,
  name,
  value,
  onChange,
  required = false,
  readOnly = false,
  type = "text",
  hint
}: {
  label: string;
  name: string;
  value: string;
  onChange: (name: string, value: string) => void;
  required?: boolean;
  readOnly?: boolean;
  type?: string;
  hint?: string | undefined;
}) {
  return (
    <label className="form-field">
      <span>{label}{required ? <em>必填</em> : null}</span>
      <input
        name={name}
        value={value}
        type={type}
        readOnly={readOnly}
        onChange={(event) => onChange(name, event.target.value)}
      />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function MatterWorkbench({ matterId }: { matterId: string }) {
  const { data: matter, isLoading, error: queryError, refetch } = useGetMatterQuery(matterId, {
    pollingInterval: 1500
  });
  const [activeStep, setActiveStep] = useState(1);
  const [draft, setDraft] = useState<{ revision: number; fields: FormState } | null>(null);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [finalChecked, setFinalChecked] = useState(false);

  const [uploadDocument, uploadState] = useUploadDocumentMutation();
  const [saveFacts, saveState] = useSaveFactsMutation();
  const [validateMatter, validateState] = useValidateMatterMutation();
  const [startGeneration, generationStartState] = useStartGenerationMutation();
  const [confirmGeneration, confirmState] = useConfirmGenerationMutation();
  const { data: job } = useGetJobQuery(jobId ?? "", {
    skip: !jobId,
    pollingInterval: jobId ? 800 : 0
  });
  const effectiveGenerationId = generationId ?? matter?.latest_generation_id ?? null;
  const { data: generation, refetch: refetchGeneration } = useGetGenerationQuery(
    effectiveGenerationId ?? "",
    { skip: !effectiveGenerationId, pollingInterval: effectiveGenerationId ? 1000 : 0 }
  );

  useEffect(() => {
    if (job?.status === "completed" || job?.status === "failed_terminal") {
      void refetch();
      if (effectiveGenerationId) void refetchGeneration();
    }
  }, [job?.status, effectiveGenerationId, refetch, refetchGeneration]);

  const gates = useMemo(() => (matter ? deriveStepGates(matter) : [true, false, false, false]), [matter]);
  // 草稿与服务端 revision 绑定；后台任务推进 revision 后，旧草稿自动失效，避免覆盖新数据。
  const fields = draft && matter && draft.revision === matter.revision
    ? draft.fields
    : matter?.facts ?? {};
  const outstanding = calculateOutstanding(fields.judgment_amount ?? "", fields.paid_amount ?? "");

  function updateField(name: string, value: string) {
    if (!matter) return;
    setDraft((current) => mergeDraftField(current, matter.revision, matter.facts, name, value));
  }

  async function handleUpload(kind: DocumentKind, file: File) {
    if (!matter) return;
    setError("");
    try {
      const result = await uploadDocument({
        matterId,
        kind,
        expectedRevision: matter.revision,
        file
      }).unwrap();
      setJobId(result.job_id);
      setDraft(null);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function saveStepOne() {
    if (!matter) return;
    setError("");
    const names = [...STEP_ONE_FIELDS, "document_date", "applicant_identity_address", "respondent_id"];
    const payload = Object.fromEntries(names.filter((name) => fields[name] !== undefined).map((name) => [name, fields[name] ?? ""]));
    try {
      await saveFacts({
        matterId,
        expected_revision: matter.revision,
        fields: payload,
        confirm_fields: names.filter((name) => Boolean(payload[name]?.trim()))
      }).unwrap();
      setDraft(null);
      setActiveStep(2);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function saveStepTwo() {
    if (!matter) return;
    setError("");
    const nextFields: FormState = { ...fields, outstanding_amount: outstanding };
    const names = [...STEP_TWO_FIELDS, "phone", "bank_account", "property_clues"];
    const payload = Object.fromEntries(names.map((name) => [name, nextFields[name] ?? ""]));
    try {
      await saveFacts({
        matterId,
        expected_revision: matter.revision,
        fields: payload,
        confirm_fields: names.filter((name) => Boolean(payload[name]?.trim()))
      }).unwrap();
      setDraft(null);
      setActiveStep(3);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function runValidation() {
    if (!matter) return;
    setError("");
    try {
      const result = await validateMatter({ matterId, expected_revision: matter.revision }).unwrap();
      setValidation(result);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function generate() {
    if (!matter) return;
    setError("");
    try {
      const result = await startGeneration({ matterId, expected_revision: matter.revision }).unwrap();
      setGenerationId(result.generation.id);
      setJobId(result.job_id);
      await refetch();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  async function confirmAndUnlock() {
    if (!matter || !effectiveGenerationId) return;
    setError("");
    try {
      await confirmGeneration({
        generationId: effectiveGenerationId,
        expected_revision: matter.revision
      }).unwrap();
      await refetchGeneration();
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  if (isLoading) return <main className="loading-page"><LoaderCircle className="spin" /> 正在读取本地事项…</main>;
  if (!matter || queryError) return <main className="loading-page">事项读取失败，请返回首页重试。</main>;

  const anyBusy = uploadState.isLoading || saveState.isLoading;
  const generationBusy = job?.status === "pending" || job?.status === "running" || job?.status === "retry_scheduled";

  return (
    <div className="workbench-shell">
      <header className="workbench-header">
        <div className="matter-title">
          <Link href="/" aria-label="返回首页"><ArrowLeft size={20} /></Link>
          <div><span>当前事项</span><strong>{matter.display_title}</strong></div>
        </div>
        <div className="header-meta">
          <StatusBadge tone={matter.title_state === "case_number_ready" ? "success" : "warning"}>
            {matter.title_state === "case_number_ready" ? "案号已确认" : matter.display_title}
          </StatusBadge>
          <span>数据版本 {matter.revision}</span>
        </div>
      </header>

      <div className="workbench-grid">
        <aside className="step-sidebar">
          <span className="step-caption">步骤 {activeStep} / 4</span>
          <nav aria-label="事项步骤">
            {STEP_LABELS.map((label, index) => {
              const step = index + 1;
              const allowed = step <= activeStep || gates[index];
              return (
                <button
                  key={label}
                  className={activeStep === step ? "active" : ""}
                  disabled={!allowed}
                  onClick={() => setActiveStep(step)}
                >
                  <span>{step}</span>{label}
                </button>
              );
            })}
          </nav>
          <p>证件号、电话和账户等敏感字段不写入浏览器持久化存储。</p>
        </aside>

        <main className="workbench-main">
          {error ? <div className="error-banner" role="alert">{error}</div> : null}

          {activeStep === 1 ? (
            <div className="step-page">
              <div className="page-heading"><div><span>步骤 1</span><h1>当事人与执行依据</h1><p>上传后先得到候选值，保存本步骤代表逐项人工确认。</p></div><FileSearch size={30} /></div>
              <section className="panel">
                <h2>执行依据</h2>
                <UploadControl kind="legal_basis" label="民事调解书或民事判决书" accept="PDF、DOCX、JPG、PNG" matter={matter} onUpload={handleUpload} disabled={anyBusy} />
                <div className="field-grid">
                  <Field label="文书类型" name="document_type" value={fields.document_type ?? ""} onChange={updateField} required />
                  <Field label="案号" name="case_number" value={fields.case_number ?? ""} onChange={updateField} required hint={matter.sources.case_number?.[0]?.snippet} />
                  <Field label="文书日期" name="document_date" value={fields.document_date ?? ""} onChange={updateField} type="date" />
                  <Field label="作出法院" name="rendering_court" value={fields.rendering_court ?? ""} onChange={updateField} required hint="不自动等同于申请法院" />
                </div>
              </section>
              <section className="panel">
                <h2><UserRound size={19} /> 申请执行人</h2>
                <div className="upload-grid">
                  <UploadControl kind="applicant_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={handleUpload} disabled={anyBusy} />
                  <UploadControl kind="applicant_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={handleUpload} disabled={anyBusy} />
                </div>
                <div className="field-grid">
                  <Field label="姓名" name="applicant_name" value={fields.applicant_name ?? ""} onChange={updateField} required />
                  <Field label="身份证号" name="applicant_id" value={fields.applicant_id ?? ""} onChange={updateField} required />
                  <Field label="身份证记载住址（仅供核对）" name="applicant_identity_address" value={fields.applicant_identity_address ?? ""} onChange={updateField} hint="不会自动成为送达地址" />
                </div>
              </section>
              <section className="panel">
                <h2><UserRound size={19} /> 被执行人</h2>
                <div className="upload-grid">
                  <UploadControl kind="respondent_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={handleUpload} optional disabled={anyBusy} />
                  <UploadControl kind="respondent_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={handleUpload} optional disabled={anyBusy} />
                </div>
                <div className="field-grid">
                  <Field label="姓名" name="respondent_name" value={fields.respondent_name ?? ""} onChange={updateField} required />
                  <Field label="身份证号（如已知）" name="respondent_id" value={fields.respondent_id ?? ""} onChange={updateField} />
                </div>
              </section>
              <div className="page-actions"><span>保存前请核对每个字段和材料来源。</span><Button variant="primary" disabled={anyBusy} onClick={() => void saveStepOne()}>保存并提取申请内容</Button></div>
            </div>
          ) : null}

          {activeStep === 2 ? (
            <div className="step-page">
              <div className="page-heading"><div><span>步骤 2</span><h1>申请内容</h1><p>金额只做确定性减法；申请法院和送达地址必须单独确认。</p></div><FileText size={30} /></div>
              <section className="panel">
                <h2>未履行金额</h2>
                <div className="amount-row">
                  <Field label="文书确定金额（元）" name="judgment_amount" value={fields.judgment_amount ?? ""} onChange={updateField} type="number" required />
                  <span>−</span>
                  <Field label="已履行金额（元）" name="paid_amount" value={fields.paid_amount ?? "0.00"} onChange={updateField} type="number" required />
                  <span>=</span>
                  <Field label="尚未履行（元）" name="outstanding_amount" value={outstanding} onChange={() => undefined} readOnly required />
                </div>
                <p className="formula">计算结果：{formatMoney(fields.judgment_amount ?? "0")} − {formatMoney(fields.paid_amount ?? "0")} = <strong>{formatMoney(outstanding)}</strong></p>
                <UploadControl kind="performance_evidence" label="履行情况材料" accept="PDF、JPG、PNG" matter={matter} onUpload={handleUpload} optional disabled={anyBusy} />
              </section>
              <section className="panel">
                <h2>请求与联系信息</h2>
                <label className="form-field form-field--wide"><span>请求事项<em>必填</em></span><textarea name="request_text" value={fields.request_text ?? ""} onChange={(event) => updateField("request_text", event.target.value)} rows={5} /></label>
                <div className="field-grid">
                  <Field label="申请法院" name="filing_court" value={fields.filing_court ?? ""} onChange={updateField} required hint="请自行判断并核对管辖" />
                  <Field label="联系电话" name="phone" value={fields.phone ?? ""} onChange={updateField} />
                  <Field label="送达地址" name="service_address" value={fields.service_address ?? ""} onChange={updateField} required hint="不会自动采用身份证住址" />
                  <Field label="收款账户（选填）" name="bank_account" value={fields.bank_account ?? ""} onChange={updateField} />
                  <Field label="已知财产线索（选填）" name="property_clues" value={fields.property_clues ?? ""} onChange={updateField} />
                </div>
              </section>
              <div className="page-actions"><Button onClick={() => setActiveStep(1)}>返回上一步</Button><Button variant="primary" disabled={anyBusy} onClick={() => void saveStepTwo()}>保存并运行检查</Button></div>
            </div>
          ) : null}

          {activeStep === 3 ? (
            <div className="step-page">
              <div className="page-heading"><div><span>步骤 3</span><h1>检查与预览</h1><p>所有阻断项必须修复；警告和提示会保留供人工复核。</p></div><ShieldAlert size={30} /></div>
              <section className="panel">
                <div className="panel-title-row"><h2>规则检查</h2><Button variant="primary" disabled={validateState.isLoading} onClick={() => void runValidation()}>{validateState.isLoading ? "检查中…" : "运行当前版本检查"}</Button></div>
                {validation ? <div className="issue-list">{validation.issues.map((issue, index) => <div key={`${issue.code}-${index}`} className={`issue issue--${issue.severity}`}><StatusBadge tone={issue.severity === "blocking" ? "danger" : issue.severity === "warning" ? "warning" : "info"}>{issue.severity}</StatusBadge><span>{issue.message}</span></div>)}</div> : <p className="muted">尚未运行检查。</p>}
              </section>
              <section className="panel">
                <div className="panel-title-row"><div><h2>生成草稿</h2><p className="muted">只读取当前 revision 的已确认字段。</p></div><Button variant="primary" disabled={!validation || validation.blocking_count > 0 || generationStartState.isLoading || generationBusy} onClick={() => void generate()}>{generationBusy ? `生成中 ${job?.progress ?? 0}%` : "生成材料包"}</Button></div>
                {generation?.status === "completed" && generation.preview_url ? <iframe className="pdf-preview" title="申请执行书草稿预览" src={generation.preview_url} /> : <div className="preview-placeholder">{generation?.status === "failed" ? "生成失败，请根据错误提示重试。" : "通过检查并生成后显示 PDF 预览。"}</div>}
              </section>
              <div className="page-actions"><Button onClick={() => setActiveStep(2)}>返回申请内容</Button><Button variant="primary" disabled={generation?.status !== "completed"} onClick={() => setActiveStep(4)}>预览完成，进入导出</Button></div>
            </div>
          ) : null}

          {activeStep === 4 ? (
            <div className="step-page">
              <div className="page-heading"><div><span>步骤 4</span><h1>导出草稿材料包</h1><p>最终确认不会改变数据版本，只解锁同一生成记录的下载。</p></div><Download size={30} /></div>
              <section className="panel export-panel">
                <h2>当前生成版本</h2>
                <dl><div><dt>数据版本</dt><dd>{generation?.revision ?? "—"}</dd></div><div><dt>状态</dt><dd>{generation?.status ?? "未生成"}</dd></div><div><dt>SHA-256</dt><dd className="hash-value">{generation?.sha256 ?? "—"}</dd></div></dl>
                <label className="confirm-row"><input type="checkbox" checked={finalChecked} onChange={(event) => setFinalChecked(event.target.checked)} /><span>我已预览申请书，并确认下载当前数据版本的草稿材料包。</span></label>
                {!generation?.final_confirmed ? <Button variant="primary" disabled={!finalChecked || confirmState.isLoading || generation?.status !== "completed"} onClick={() => void confirmAndUnlock()}>最终确认并解锁下载</Button> : <a className="download-link" href={generation.download_url ?? "#"}><Download size={18} /> 下载申请强制执行材料包（ZIP）</a>}
                <p className="boundary-note">材料包包含 DOCX、PDF 预览、材料清单、字段来源核对表和版本清单。所有文件均为草稿，系统未向法院提交。</p>
              </section>
              <div className="page-actions"><Button onClick={() => setActiveStep(3)}>返回预览</Button></div>
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
