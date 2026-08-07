import { MatterField } from "../MatterForm";

export function ApplicationDetails() {
  return (
    <section className="panel">
      <h2>请求与联系信息</h2>
      <div className="form-field--wide">
        <MatterField label="请求事项" name="request_text" required multiline />
      </div>
      <div className="field-grid">
        <MatterField label="申请法院" name="filing_court" required hint="请自行判断并核对管辖" />
        <MatterField label="联系电话" name="phone" />
        <MatterField label="送达地址" name="service_address" required hint="不会自动采用身份证住址" />
        <MatterField label="收款账户（选填）" name="bank_account" />
        <MatterField label="已知财产线索（选填）" name="property_clues" />
      </div>
    </section>
  );
}
