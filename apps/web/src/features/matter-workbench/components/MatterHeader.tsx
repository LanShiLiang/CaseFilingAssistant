import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import type { Matter } from "@case-filing/contracts";
import { StatusBadge } from "@case-filing/ui";

export function MatterHeader({ matter }: { matter: Matter }) {
  const titleReady = matter.title_state === "case_number_ready";

  return (
    <header className="workbench-header">
      <div className="matter-title">
        <Link href="/" aria-label="返回首页"><ArrowLeft size={20} /></Link>
        <div><span>当前事项</span><strong>{matter.display_title}</strong></div>
      </div>
      <div className="header-meta">
        <StatusBadge tone={titleReady ? "success" : "warning"}>
          {titleReady ? "案号已确认" : "待上传执行依据"}
        </StatusBadge>
        <span>数据版本 {matter.revision}</span>
      </div>
    </header>
  );
}
