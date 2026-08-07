import { Download } from "lucide-react";

import type { Generation } from "@case-filing/contracts";
import { Button } from "@case-filing/ui";

export function ExportStep({
  generation,
  finalChecked,
  confirmPending,
  onCheckedChange,
  onConfirm,
  onBack
}: {
  generation: Generation | undefined;
  finalChecked: boolean;
  confirmPending: boolean;
  onCheckedChange: (checked: boolean) => void;
  onConfirm: () => Promise<void>;
  onBack: () => void;
}) {
  return (
    <div className="step-page">
      <div className="page-heading"><div><span>步骤 4</span><h1>导出草稿材料包</h1><p>最终确认不会改变数据版本，只解锁同一生成记录的下载。</p></div><Download size={30} /></div>
      <section className="panel export-panel">
        <h2>当前生成版本</h2>
        <dl><div><dt>数据版本</dt><dd>{generation?.revision ?? "—"}</dd></div><div><dt>状态</dt><dd>{generation?.status ?? "未生成"}</dd></div><div><dt>SHA-256</dt><dd className="hash-value">{generation?.sha256 ?? "—"}</dd></div></dl>
        <label className="confirm-row"><input type="checkbox" checked={finalChecked} onChange={(event) => onCheckedChange(event.target.checked)} /><span>我已预览申请书，并确认下载当前数据版本的草稿材料包。</span></label>
        {!generation?.final_confirmed ? <Button variant="primary" disabled={!finalChecked || confirmPending || generation?.status !== "completed"} onClick={() => void onConfirm()}>最终确认并解锁下载</Button> : <a className="download-link" href={generation.download_url ?? "#"}><Download size={18} /> 下载申请强制执行材料包（ZIP）</a>}
        <p className="boundary-note">材料包包含 DOCX、PDF 预览、材料清单、字段来源核对表和版本清单。所有文件均为草稿，系统未向法院提交。</p>
      </section>
      <div className="page-actions"><Button onClick={onBack}>返回预览</Button></div>
    </div>
  );
}
