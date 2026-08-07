import type { ApiErrorBody } from "@case-filing/contracts";

export type FormDraft = {
  revision: number;
  fields: Record<string, string>;
};

export const STEP_ONE_FIELDS = [
  "document_type",
  "case_number",
  "rendering_court",
  "applicant_name",
  "applicant_id",
  "respondent_name"
] as const;

export const STEP_TWO_FIELDS = [
  "judgment_amount",
  "paid_amount",
  "outstanding_amount",
  "request_text",
  "filing_court",
  "service_address"
] as const;

export function calculateOutstanding(judgment: string, paid: string): string {
  const judgmentValue = Number(judgment);
  const paidValue = Number(paid);
  if (!Number.isFinite(judgmentValue) || !Number.isFinite(paidValue)) return "";
  return Math.max(0, judgmentValue - paidValue).toFixed(2);
}

export function mergeDraftField(
  current: FormDraft | null,
  serverRevision: number,
  serverFields: Record<string, string>,
  name: string,
  value: string
): FormDraft {
  // React 可能批量处理同一轮输入事件；必须从上一个草稿合并，不能用渲染闭包中的旧 fields 覆盖相邻字段。
  const baseFields = current?.revision === serverRevision ? current.fields : serverFields;
  return {
    revision: serverRevision,
    fields: { ...baseFields, [name]: value }
  };
}

export function parseApiError(error: unknown): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "data" in error &&
    typeof error.data === "object" &&
    error.data !== null
  ) {
    const body = error.data as Partial<ApiErrorBody>;
    if (body.error?.message) {
      const suffix = [body.error.code, body.error.request_id]
        .filter(Boolean)
        .join(" · ");
      return suffix ? `${body.error.message}（${suffix}）` : body.error.message;
    }
  }
  return "操作失败，请稍后重试。";
}

export function formatMoney(value: string): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "¥0.00";
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2
  }).format(numeric);
}
