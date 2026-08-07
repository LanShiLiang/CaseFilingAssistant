import { describe, expect, it } from "vitest";

import {
  calculateOutstanding,
  formatMoney,
  mergeDraftField,
  parseApiError
} from "./domain";

describe("domain helpers", () => {
  it("计算尚未履行金额的页面预估", () => {
    expect(calculateOutstanding("120000", "20000")).toBe("100000.00");
    expect(calculateOutstanding("invalid", "0")).toBe("");
  });

  it("稳定显示金额与协议错误", () => {
    expect(formatMoney("100000")).toContain("100,000.00");
    expect(parseApiError({ data: { error: { message: "版本冲突" } } })).toBe("版本冲突");
    expect(parseApiError(null)).toBe("操作失败，请稍后重试。");
  });

  it("连续输入字段时合并当前 revision 草稿而不相互覆盖", () => {
    const serverFields = { judgment_amount: "10000.00" };
    const paidDraft = mergeDraftField(null, 6, serverFields, "paid_amount", "2500.00");
    const requestDraft = mergeDraftField(
      paidDraft,
      6,
      serverFields,
      "request_text",
      "请求强制执行人民币7500.00元。"
    );

    expect(requestDraft.fields).toEqual({
      judgment_amount: "10000.00",
      paid_amount: "2500.00",
      request_text: "请求强制执行人民币7500.00元。"
    });

    const refreshed = mergeDraftField(
      requestDraft,
      7,
      { judgment_amount: "12000.00" },
      "paid_amount",
      "0.00"
    );
    expect(refreshed).toEqual({
      revision: 7,
      fields: { judgment_amount: "12000.00", paid_amount: "0.00" }
    });
  });
});
