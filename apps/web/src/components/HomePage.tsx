"use client";

import Link from "next/link";
import { FileCheck2, HardDrive, LockKeyhole } from "lucide-react";

import { EligibilityGate } from "./EligibilityGate";
import { useCreateEligibleMatter } from "@/features/eligibility/useCreateEligibleMatter";
import { useListMattersQuery } from "@/store/caseApi";

export function HomePage() {
  const { data: matters = [] } = useListMattersQuery();
  const { create, creating, error } = useCreateEligibleMatter();

  return (
    <main className="landing-shell">
      <header className="brand-header">
        <div>
          <span className="brand-name">Case Filing Assistant</span>
          <span className="brand-subtitle">强制执行材料助手</span>
        </div>
        <span className="local-pill"><HardDrive size={15} /> 本机运行</span>
      </header>
      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">本人办理 · 单一被执行人 · 一项金钱义务</span>
          <h1>从现有材料整理申请强制执行草稿</h1>
          <p>上传执行依据和身份材料，逐项核对来源、金额和请求事项，生成可人工复核的申请书与材料清单。</p>
          <div className="boundary-note"><LockKeyhole size={18} />材料保存在本机；系统不会登录法院、代为提交、缴费、送达或联系法院。</div>
        </div>
        <div className="feature-card">
          <FileCheck2 size={28} />
          <h2>输出范围</h2>
          <p>申请执行书草稿、材料清单、字段来源核对表、PDF 预览及版本清单。</p>
        </div>
      </section>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      <section className="home-grid">
        <EligibilityGate onCreate={create} creating={creating} />
        <aside className="recent-card">
          <h2>最近本地事项</h2>
          {matters.length === 0 ? <p className="muted">暂无事项。完成适用确认后新建。</p> : null}
          <div className="recent-list">
            {matters.map((matter) => (
              <Link href={`/matters/${matter.id}`} key={matter.id} className="recent-item">
                <strong>{matter.display_title}</strong>
                <span>数据版本 {matter.revision}</span>
              </Link>
            ))}
          </div>
        </aside>
      </section>
    </main>
  );
}
