import { Download } from "lucide-react";

import type { Generation } from "@case-filing/contracts";
import { Button } from "@case-filing/ui";

import { StepHeading } from "../components/StepHeading";
import type { ExportCheck, ExportCheckValues } from "../types";

const ATTESTATIONS: ReadonlyArray<{ name: ExportCheck; label: string }> = [
  { name: "critical", label: "我已逐项核对姓名、证件号、金额、履行情况和请求事项。" },
  { name: "review", label: "我理解生成文件必须由本人或专业人员复核，系统未向法院提交。" },
  { name: "local", label: "我已自行核对受理法院及其当前地方材料要求。" }
];

export function ExportStep({
  generation,
  finalChecked,
  checks,
  confirmPending,
  onCheckedChange,
  onConfirm,
  onBack
}: {
  generation: Generation | undefined;
  finalChecked: boolean;
  checks: ExportCheckValues;
  confirmPending: boolean;
  onCheckedChange: (name: ExportCheck, checked: boolean) => void;
  onConfirm: () => Promise<void>;
  onBack: () => void;
}) {
  return (
    <div className="step-page">
      <StepHeading
        step={4}
        title="导出强制执行申请材料"
        description="最终声明不会改变数据版本，只解锁同一生成记录的下载。"
        icon={<Download size={30} />}
      />
      <section className="panel export-panel">
        <h2>当前生成版本</h2>
        <dl><div><dt>数据版本</dt><dd>{generation?.revision ?? "—"}</dd></div><div><dt>状态</dt><dd>{generation?.status ?? "未生成"}</dd></div><div><dt>SHA-256</dt><dd className="hash-value">{generation?.sha256 ?? "—"}</dd></div></dl>
        {ATTESTATIONS.map((item) => (
          <label className="confirm-row" key={item.name}>
            <input type="checkbox" checked={checks[item.name]} onChange={(event) => onCheckedChange(item.name, event.target.checked)} />
            <span>{item.label}</span>
          </label>
        ))}
        {!generation?.final_confirmed ? <Button variant="primary" disabled={!finalChecked || confirmPending || generation?.status !== "completed"} onClick={() => void onConfirm()}>提交三项声明并解锁下载</Button> : <a className="download-link" href={generation.download_url ?? "#"}><Download size={18} /> 下载申请强制执行材料包（ZIP）</a>}
        <p className="boundary-note">材料包包含强制执行申请书 DOCX、由同一 DOCX 转换的 PDF 预览、材料清单、字段来源核对表和版本清单。生成文件必须人工复核，系统未向法院提交。</p>
      </section>
      <div className="page-actions"><Button onClick={onBack}>返回预览</Button></div>
    </div>
  );
}
