import { FileText } from "lucide-react";

import { Button } from "@case-filing/ui";

import { formatMoney } from "@/lib/domain";

import { Field } from "../components/Field";
import { UploadControl } from "../components/UploadControl";
import type { StepCommonProps, UploadHandler } from "../types";

export function ApplicationStep({
  matter,
  fields,
  onFieldChange,
  onUpload,
  outstanding,
  busy,
  onBack,
  onSave
}: StepCommonProps & {
  onUpload: UploadHandler;
  outstanding: string;
  busy: boolean;
  onBack: () => void;
  onSave: () => Promise<void>;
}) {
  return (
    <div className="step-page">
      <div className="page-heading"><div><span>步骤 2</span><h1>申请内容</h1><p>页面金额是未保存预估；服务端使用 Decimal 重新计算并作为最终权威值。</p></div><FileText size={30} /></div>
      <section className="panel">
        <h2>未履行金额</h2>
        <div className="amount-row">
          <Field label="文书确定金额（元）" name="judgment_amount" value={fields.judgment_amount ?? ""} onChange={onFieldChange} type="number" required />
          <span>−</span>
          <Field label="已履行金额（元）" name="paid_amount" value={fields.paid_amount ?? "0.00"} onChange={onFieldChange} type="number" required />
          <span>=</span>
          <Field label="尚未履行预估（元）" name="outstanding_amount" value={outstanding} onChange={() => undefined} readOnly required />
        </div>
        <p className="formula">未保存预估：{formatMoney(fields.judgment_amount ?? "0")} − {formatMoney(fields.paid_amount ?? "0")} = <strong>{formatMoney(outstanding)}</strong></p>
        <UploadControl kind="performance_evidence" label="履行情况材料" accept="PDF、JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
      </section>

      <section className="panel">
        <h2>请求与联系信息</h2>
        <label className="form-field form-field--wide"><span>请求事项<em>必填</em></span><textarea name="request_text" value={fields.request_text ?? ""} onChange={(event) => onFieldChange("request_text", event.target.value)} rows={5} /></label>
        <div className="field-grid">
          <Field label="申请法院" name="filing_court" value={fields.filing_court ?? ""} onChange={onFieldChange} required hint="请自行判断并核对管辖" />
          <Field label="联系电话" name="phone" value={fields.phone ?? ""} onChange={onFieldChange} />
          <Field label="送达地址" name="service_address" value={fields.service_address ?? ""} onChange={onFieldChange} required hint="不会自动采用身份证住址" />
          <Field label="收款账户（选填）" name="bank_account" value={fields.bank_account ?? ""} onChange={onFieldChange} />
          <Field label="已知财产线索（选填）" name="property_clues" value={fields.property_clues ?? ""} onChange={onFieldChange} />
        </div>
      </section>

      <div className="page-actions"><Button onClick={onBack}>返回上一步</Button><Button variant="primary" disabled={busy} onClick={() => void onSave()}>保存并运行检查</Button></div>
    </div>
  );
}
