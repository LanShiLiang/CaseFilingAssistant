import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import type { Matter } from "@case-filing/contracts";
import { StatusBadge } from "@case-filing/ui";

export function MatterHeader({ matter }: { matter: Matter }) {
  const titleReady = matter.title_state === "case_number_ready";
  const statusLabel: Record<Matter["title_state"], string> = {
    pending_upload: "待上传执行依据",
    processing: "正在识别材料",
    pending_confirmation: "案号待人工确认",
    case_number_ready: "案号已确认"
  };

  return (
    <header className="workbench-header">
      <div className="matter-title">
        <Link href="/" aria-label="返回首页"><ArrowLeft size={20} /></Link>
        <div><span>当前事项</span><strong>{matter.display_title}</strong></div>
      </div>
      <div className="header-meta">
        <StatusBadge tone={titleReady ? "success" : "warning"}>
          {statusLabel[matter.title_state]}
        </StatusBadge>
        <span>数据版本 {matter.revision}</span>
      </div>
    </header>
  );
}
