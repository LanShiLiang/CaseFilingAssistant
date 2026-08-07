export const WORKFLOW_STEPS = [
  { key: "parties_and_basis", label: "当事人与依据" },
  { key: "application", label: "申请内容" },
  { key: "review", label: "检查与预览" },
  { key: "export", label: "导出" }
] as const;

export type WorkflowStepNumber = 1 | 2 | 3 | 4;
