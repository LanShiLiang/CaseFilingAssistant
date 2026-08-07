export const WORKFLOW_STEPS = [
  { key: "details", gateKey: "parties_and_basis", label: "资料填写" },
  { key: "review", gateKey: "review", label: "检查与预览" },
  { key: "export", gateKey: "export", label: "导出" }
] as const;

export type WorkflowStepNumber = 1 | 2 | 3;
