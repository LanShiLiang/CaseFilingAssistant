import type { ApiErrorBody } from "@case-filing/contracts";

export type PendingFormEdits = {
  matterId: string;
  values: Record<string, string>;
  editedFields: string[];
};

export function mergePendingField(
  current: PendingFormEdits | null,
  matterId: string,
  name: string,
  value: string
): PendingFormEdits {
  // 上传和后台解析会推进服务端 revision；未提交输入按字段保存，不能随权威状态刷新一起丢弃。
  const base = current?.matterId === matterId
    ? current
    : { matterId, values: {}, editedFields: [] };
  return {
    matterId,
    values: { ...base.values, [name]: value },
    editedFields: [...new Set([...base.editedFields, name])]
  };
}

export function applyPendingEdits(
  serverFields: Record<string, string>,
  pending: PendingFormEdits | null,
  matterId: string
): Record<string, string> {
  if (pending?.matterId !== matterId) return serverFields;
  return { ...serverFields, ...pending.values };
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
