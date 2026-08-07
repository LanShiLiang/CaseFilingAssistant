import { FileSearch, UserRound } from "lucide-react";

import { Button } from "@case-filing/ui";

import { MatterField, useMatterForm } from "../MatterForm";
import { StepHeading } from "../components/StepHeading";
import { UploadControl } from "../components/UploadControl";
import type { UploadHandler } from "../types";

type PartiesAndBasisStepProps = {
  onUpload: UploadHandler;
  busy: boolean;
  onSave: () => Promise<void>;
  dismissedScopeSignalIds: readonly string[];
  onScopeSignalDismissalChange: (id: string, dismissed: boolean) => void;
};

export function PartiesAndBasisStep(props: PartiesAndBasisStepProps) {
  const {
    onUpload,
    busy,
    onSave,
    dismissedScopeSignalIds,
    onScopeSignalDismissalChange
  } = props;
  const { matter } = useMatterForm();
  return (
    <div className="step-page">
      <StepHeading
        step={1}
        title="当事人与执行依据"
        description="上传后先得到候选值；保存本步骤表示已核对并确认当前非空字段。"
        icon={<FileSearch size={30} />}
      />
      <section className="panel">
        <h2>执行依据</h2>
        <UploadControl kind="legal_basis" label="民事调解书或民事判决书" accept="PDF、DOCX、JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
        <div className="field-grid">
          <MatterField label="文书类型" name="document_type" required />
          <MatterField label="案号" name="case_number" required />
          <MatterField label="文书日期" name="document_date" type="date" />
          <MatterField label="作出法院" name="rendering_court" required hint="不自动等同于申请法院" />
        </div>
      </section>

      <section className="panel">
        <h2><UserRound size={19} /> 申请执行人</h2>
        <div className="upload-grid">
          <UploadControl kind="applicant_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
          <UploadControl kind="applicant_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
        </div>
        <div className="field-grid">
          <MatterField label="姓名" name="applicant_name" required />
          <MatterField label="身份证号" name="applicant_id" required sensitive />
          <MatterField label="身份证记载住址（仅供核对）" name="applicant_identity_address" hint="不会自动成为送达地址" sensitive />
        </div>
      </section>

      <section className="panel">
        <h2><UserRound size={19} /> 被执行人</h2>
        <div className="upload-grid">
          <UploadControl kind="respondent_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
          <UploadControl kind="respondent_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
        </div>
        <div className="field-grid">
          <MatterField label="姓名" name="respondent_name" required />
          <MatterField label="身份证号（如已知）" name="respondent_id" sensitive />
        </div>
      </section>

      {matter.scope_signals.length ? (
        <section className="panel scope-signals" aria-labelledby="scope-signals-title">
          <h2 id="scope-signals-title">适用范围风险信号</h2>
          <p className="muted">信号默认阻断生成。只有确认属于识别误报时才能逐项排除。</p>
          {matter.scope_signals.map((signal) => (
            <label className="confirm-row" key={signal.id}>
              <input
                type="checkbox"
                checked={
                  signal.status === "dismissed_as_parse_error" ||
                  dismissedScopeSignalIds.includes(signal.id)
                }
                onChange={(event) =>
                  onScopeSignalDismissalChange(signal.id, event.target.checked)
                }
              />
              <span>{signal.code}：{signal.snippet}（材料第 {signal.page ?? "?"} 页）— 我确认这是识别误报</span>
            </label>
          ))}
        </section>
      ) : null}

      <div className="page-actions"><span>保存前请核对每个字段和材料来源。</span><Button variant="primary" disabled={busy} onClick={() => void onSave()}>保存并提取申请内容</Button></div>
    </div>
  );
}
