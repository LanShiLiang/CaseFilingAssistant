import { FileSearch, UserRound } from "lucide-react";

import { Button } from "@case-filing/ui";

import { Field } from "../components/Field";
import { UploadControl } from "../components/UploadControl";
import type { StepCommonProps, UploadHandler } from "../types";

export function PartiesAndBasisStep({
  matter,
  fields,
  onFieldChange,
  onUpload,
  busy,
  onSave
}: StepCommonProps & {
  onUpload: UploadHandler;
  busy: boolean;
  onSave: () => Promise<void>;
}) {
  return (
    <div className="step-page">
      <div className="page-heading"><div><span>步骤 1</span><h1>当事人与执行依据</h1><p>上传后先得到候选值，保存本步骤代表逐项人工确认。</p></div><FileSearch size={30} /></div>
      <section className="panel">
        <h2>执行依据</h2>
        <UploadControl kind="legal_basis" label="民事调解书或民事判决书" accept="PDF、DOCX、JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
        <div className="field-grid">
          <Field label="文书类型" name="document_type" value={fields.document_type ?? ""} onChange={onFieldChange} required />
          <Field label="案号" name="case_number" value={fields.case_number ?? ""} onChange={onFieldChange} required hint={matter.sources.case_number?.[0]?.snippet} />
          <Field label="文书日期" name="document_date" value={fields.document_date ?? ""} onChange={onFieldChange} type="date" />
          <Field label="作出法院" name="rendering_court" value={fields.rendering_court ?? ""} onChange={onFieldChange} required hint="不自动等同于申请法院" />
        </div>
      </section>

      <section className="panel">
        <h2><UserRound size={19} /> 申请执行人</h2>
        <div className="upload-grid">
          <UploadControl kind="applicant_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
          <UploadControl kind="applicant_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={onUpload} disabled={busy} />
        </div>
        <div className="field-grid">
          <Field label="姓名" name="applicant_name" value={fields.applicant_name ?? ""} onChange={onFieldChange} required />
          <Field label="身份证号" name="applicant_id" value={fields.applicant_id ?? ""} onChange={onFieldChange} required />
          <Field label="身份证记载住址（仅供核对）" name="applicant_identity_address" value={fields.applicant_identity_address ?? ""} onChange={onFieldChange} hint="不会自动成为送达地址" />
        </div>
      </section>

      <section className="panel">
        <h2><UserRound size={19} /> 被执行人</h2>
        <div className="upload-grid">
          <UploadControl kind="respondent_id_front" label="身份证人像面" accept="JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
          <UploadControl kind="respondent_id_back" label="身份证国徽面" accept="JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
        </div>
        <div className="field-grid">
          <Field label="姓名" name="respondent_name" value={fields.respondent_name ?? ""} onChange={onFieldChange} required />
          <Field label="身份证号（如已知）" name="respondent_id" value={fields.respondent_id ?? ""} onChange={onFieldChange} />
        </div>
      </section>

      <div className="page-actions"><span>保存前请核对每个字段和材料来源。</span><Button variant="primary" disabled={busy} onClick={() => void onSave()}>保存并提取申请内容</Button></div>
    </div>
  );
}
