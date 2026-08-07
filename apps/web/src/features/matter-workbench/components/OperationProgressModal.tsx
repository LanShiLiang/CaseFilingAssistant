"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, LoaderCircle } from "lucide-react";

import { Button } from "@case-filing/ui";

import type { WorkbenchOperation } from "../types";

function operationCopy(operation: Exclude<WorkbenchOperation, { kind: "blocked" }>) {
  if (operation.kind === "save") {
    if (operation.phase === "collecting") {
      return {
        title: "正在收集步骤一资料",
        description: "正在汇总必传材料、已填写字段和来源信息。",
        progress: 20
      };
    }
    if (operation.phase === "saving") {
      return {
        title: "正在保存事项资料",
        description: "正在保存当事人、执行依据和请求信息。",
        progress: 55
      };
    }
    return {
      title: "正在检查当前数据",
      description: "资料已保存，正在基于最新数据版本运行规则检查。",
      progress: 85
    };
  }
  return operation.phase === "starting"
    ? {
        title: "正在创建预览任务",
        description: "正在冻结当前已确认数据并创建强制执行申请书预览任务。",
        progress: undefined
      }
    : {
        title: "正在生成申请书预览",
        description: "后台正在生成材料包并转换 PDF，完成前请保持当前页面打开。",
        progress: undefined
      };
}

export function OperationProgressModal({
  operation,
  jobProgress,
  onDismiss
}: {
  operation: WorkbenchOperation | null;
  jobProgress?: number | null | undefined;
  onDismiss: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const operationKind = operation?.kind;

  useEffect(() => {
    if (!operationKind) return undefined;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => previousFocusRef.current?.focus();
  }, [operationKind]);

  if (!operation) return null;
  if (operation.kind === "blocked") {
    return (
      <div className="operation-modal-backdrop">
        <div
          ref={dialogRef}
          className="operation-modal operation-modal--blocked"
          role="dialog"
          aria-modal="true"
          aria-labelledby="operation-modal-title"
          aria-describedby="operation-modal-description"
          tabIndex={-1}
          onKeyDown={(event) => {
            if (event.key === "Escape") onDismiss();
          }}
        >
          <AlertTriangle className="operation-modal-icon" aria-hidden="true" />
          <div>
            <span className="section-kicker">暂时无法继续</span>
            <h2 id="operation-modal-title">步骤一还有必填项未完成</h2>
            <p id="operation-modal-description">请按下面的模块补全资料，再重新保存。</p>
          </div>
          <ul className="operation-blocker-list">
            {operation.blockers.map((blocker) => (
              <li key={blocker.id}>
                <strong>{blocker.section}</strong>
                <span>{blocker.message}</span>
              </li>
            ))}
          </ul>
          <div className="operation-modal-actions">
            <Button variant="primary" onClick={onDismiss}>返回补充资料</Button>
          </div>
        </div>
      </div>
    );
  }
  const copy = operationCopy(operation);
  const progress = operation.kind === "preview" && operation.phase === "running"
    ? jobProgress ?? undefined
    : copy.progress;

  return (
    <div className="operation-modal-backdrop">
      <div
        ref={dialogRef}
        className="operation-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="operation-modal-title"
        aria-describedby="operation-modal-description operation-modal-lock-note"
        tabIndex={-1}
      >
        <LoaderCircle className="spin operation-modal-icon" aria-hidden="true" />
        <div>
          <span className="section-kicker">处理中</span>
          <h2 id="operation-modal-title">{copy.title}</h2>
          <p id="operation-modal-description">{copy.description}</p>
        </div>
        <progress
          className="operation-progress"
          aria-label={progress === undefined ? "正在处理" : `处理进度 ${progress}%`}
          max={100}
          value={progress}
        />
        <p id="operation-modal-lock-note" className="operation-lock-note">
          为避免数据版本冲突，处理完成前表单已锁定，完成后会自动恢复编辑。
        </p>
      </div>
    </div>
  );
}
