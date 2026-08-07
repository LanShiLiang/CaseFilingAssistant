import { FileText } from "lucide-react";

import { Button } from "@case-filing/ui";

import { formatMoney } from "@/lib/domain";

import { MatterField, useMatterForm } from "../MatterForm";
import { StepHeading } from "../components/StepHeading";
import { UploadControl } from "../components/UploadControl";
import type { UploadHandler } from "../types";

type ApplicationStepProps = {
  onUpload: UploadHandler;
  outstanding: string;
  busy: boolean;
  onBack: () => void;
  onSave: () => Promise<void>;
};

export function ApplicationStep(props: ApplicationStepProps) {
  const {
    onUpload,
    outstanding,
    busy,
    onBack,
    onSave
  } = props;
  const { matter, fields } = useMatterForm();
  return (
    <div className="step-page">
      <StepHeading
        step={2}
        title="申请内容"
        description="页面金额是未保存预估；服务端使用 Decimal 重新计算并作为最终权威值。"
        icon={<FileText size={30} />}
      />
      <section className="panel">
        <h2>未履行金额</h2>
        <div className="amount-row">
          <MatterField label="文书确定金额（元）" name="judgment_amount" type="number" required />
          <span>−</span>
          <MatterField
            label="已履行金额（元）"
            name="paid_amount"
            type="number"
            required
            valueOverride={fields.paid_amount ?? "0.00"}
          />
          <span>=</span>
          <MatterField
            label="尚未履行预估（元）"
            name="outstanding_amount"
            readOnly
            required
            valueOverride={outstanding}
          />
        </div>
        <p className="formula">未保存预估：{formatMoney(fields.judgment_amount ?? "0")} − {formatMoney(fields.paid_amount ?? "0")} = <strong>{formatMoney(outstanding)}</strong></p>
        <UploadControl kind="performance_evidence" label="履行情况材料" accept="PDF、JPG、PNG" matter={matter} onUpload={onUpload} optional disabled={busy} />
      </section>

      <section className="panel">
        <h2>请求与联系信息</h2>
        <div className="form-field--wide"><MatterField label="请求事项" name="request_text" required multiline /></div>
        <div className="field-grid">
          <MatterField label="申请法院" name="filing_court" required hint="请自行判断并核对管辖" />
          <MatterField label="联系电话" name="phone" sensitive />
          <MatterField label="送达地址" name="service_address" required hint="不会自动采用身份证住址" sensitive />
          <MatterField label="收款账户（选填）" name="bank_account" sensitive />
          <MatterField label="已知财产线索（选填）" name="property_clues" sensitive />
        </div>
      </section>

      <div className="page-actions"><Button onClick={onBack}>返回上一步</Button><Button variant="primary" disabled={busy} onClick={() => void onSave()}>保存并运行检查</Button></div>
    </div>
  );
}
