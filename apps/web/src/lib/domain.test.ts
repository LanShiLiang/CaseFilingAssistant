import { describe, expect, it } from "vitest";

import {
  applyPendingEdits,
  calculateOutstanding,
  formatMoney,
  mergePendingField,
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

  it("连续输入字段时保留同一事项的未提交值", () => {
    const paidEdit = mergePendingField(null, "matter-1", "paid_amount", "2500.00");
    const requestEdit = mergePendingField(
      paidEdit,
      "matter-1",
      "request_text",
      "请求强制执行人民币7500.00元。"
    );

    expect(applyPendingEdits(
      { judgment_amount: "10000.00" },
      requestEdit,
      "matter-1"
    )).toEqual({
      judgment_amount: "10000.00",
      paid_amount: "2500.00",
      request_text: "请求强制执行人民币7500.00元。"
    });
  });

  it("上传和后台解析推进 revision 后仍以用户编辑字段覆盖新的服务端基线", () => {
    const applicantName = mergePendingField(
      null,
      "matter-1",
      "applicant_name",
      "测试申请执行人"
    );
    const applicantIdentity = mergePendingField(
      applicantName,
      "matter-1",
      "applicant_id",
      "TEST-ID-APPLICANT"
    );

    expect(applyPendingEdits(
      { respondent_name: "测试被执行人" },
      applicantIdentity,
      "matter-1"
    )).toEqual({
      respondent_name: "测试被执行人",
      applicant_name: "测试申请执行人",
      applicant_id: "TEST-ID-APPLICANT"
    });
    expect(applyPendingEdits({}, applicantIdentity, "matter-2")).toEqual({});
  });
});
