"use client";

import { useState } from "react";
import { CheckCircle2, ShieldCheck } from "lucide-react";

import { Button } from "@case-filing/ui";

const CONDITIONS = [
  "我是生效法律文书中享有权利、准备本人办理申请执行的当事人，不委托律师或其他代理人。",
  "本次申请只有一名自然人申请执行人和一名自然人被执行人。",
  "执行依据是民事调解书或民事判决书，且只有一项明确的金钱给付义务。",
  "我会人工核对姓名、证件号、金额、履行情况和请求事项。"
] as const;

export function EligibilityGate({
  onCreate,
  creating = false
}: {
  onCreate: () => Promise<void>;
  creating?: boolean;
}) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <section className="eligibility-card" aria-labelledby="eligibility-title">
      <div className="section-kicker"><ShieldCheck size={18} /> 使用范围门禁</div>
      <h2 id="eligibility-title">开始前确认适用条件</h2>
      <p className="muted">以下条件全部满足，才适合使用当前版本。</p>
      <ol className="condition-list">
        {CONDITIONS.map((condition) => (
          <li key={condition}><CheckCircle2 size={18} aria-hidden="true" /><span>{condition}</span></li>
        ))}
      </ol>
      <label className="confirm-row">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(event) => setConfirmed(event.target.checked)}
        />
        <span>我已阅读并确认以上 4 项全部符合。</span>
      </label>
      <Button variant="primary" disabled={!confirmed || creating} onClick={() => void onCreate()}>
        {creating ? "正在新建…" : "新建强制执行事项"}
      </Button>
    </section>
  );
}
