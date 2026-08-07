import { ShieldAlert } from "lucide-react";

import type { Generation, Job, ValidationResult } from "@case-filing/contracts";
import { Button, StatusBadge } from "@case-filing/ui";

export function ReviewStep({
  validation,
  generation,
  job,
  validationPending,
  generationPending,
  generationBusy,
  retryPending,
  onValidate,
  onGenerate,
  onBack,
  onContinue,
  onRetry
}: {
  validation: ValidationResult | null;
  generation: Generation | undefined;
  job: Job | undefined;
  validationPending: boolean;
  generationPending: boolean;
  generationBusy: boolean;
  retryPending: boolean;
  onValidate: () => Promise<void>;
  onGenerate: () => Promise<void>;
  onBack: () => void;
  onContinue: () => void;
  onRetry: () => Promise<void>;
}) {
  return (
    <div className="step-page">
      <div className="page-heading"><div><span>步骤 3</span><h1>检查与预览</h1><p>所有阻断项必须修复；警告和提示会保留供人工复核。</p></div><ShieldAlert size={30} /></div>
      <section className="panel">
        <div className="panel-title-row"><h2>规则检查</h2><Button variant="primary" disabled={validationPending} onClick={() => void onValidate()}>{validationPending ? "检查中…" : "运行当前版本检查"}</Button></div>
        {validation ? <div className="issue-list">{validation.issues.map((issue, index) => <div key={`${issue.code}-${index}`} className={`issue issue--${issue.severity}`}><StatusBadge tone={issue.severity === "blocking" ? "danger" : issue.severity === "warning" ? "warning" : "info"}>{issue.severity}</StatusBadge><span>{issue.message}</span></div>)}</div> : <p className="muted">尚未运行检查。</p>}
      </section>

      <section className="panel">
        <div className="panel-title-row"><div><h2>生成草稿</h2><p className="muted">只读取当前 revision 冻结的已确认字段。</p></div><Button variant="primary" disabled={!validation || validation.blocking_count > 0 || generationPending || generationBusy} onClick={() => void onGenerate()}>{generationBusy ? `生成中 ${job?.progress ?? 0}%` : "生成材料包"}</Button></div>
        {generation?.status === "completed" && generation.preview_url ? <iframe className="pdf-preview" title="申请执行书草稿预览" src={generation.preview_url} /> : <div className="preview-placeholder">{generation?.status === "failed" ? "生成失败，请根据错误提示重试。" : "通过检查并生成后显示 PDF 预览。"}</div>}
        {job?.retryable ? <Button disabled={retryPending} onClick={() => void onRetry()}>{retryPending ? "正在安排重试…" : "重试当前任务"}</Button> : null}
      </section>

      <div className="page-actions"><Button onClick={onBack}>返回申请内容</Button><Button variant="primary" disabled={generation?.status !== "completed"} onClick={onContinue}>预览完成，进入导出</Button></div>
    </div>
  );
}
