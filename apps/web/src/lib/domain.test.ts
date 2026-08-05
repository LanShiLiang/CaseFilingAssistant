import { describe, expect, it } from "vitest";

import type { Matter } from "@case-filing/contracts";

import {
  calculateOutstanding,
  deriveStepGates,
  formatMoney,
  mergeDraftField,
  parseApiError
} from "./domain";

function matterFixture(): Matter {
  const required = {
    document_type: "民事调解书",
    case_number: "（2026）示例民初 001 号",
    rendering_court: "示例市示例区人民法院",
    applicant_name: "林示例",
    applicant_id: "TEST-ID-APPLICANT",
    respondent_name: "周示例",
    judgment_amount: "120000.00",
    paid_amount: "20000.00",
    outstanding_amount: "100000.00",
    request_text: "请求支付尚未履行款项。",
    filing_court: "示例市示例区人民法院",
    service_address: "示例地址，仅用于自动化测试"
  };
  return {
    id: "matter-test",
    workflow_profile: "self_single_v1",
    eligibility_version: "self_single_v1.0.0",
    eligibility_confirmed: true,
    revision: 8,
    title_state: "case_number_ready",
    display_title: required.case_number,
    facts: required,
    confirmations: Object.fromEntries(Object.keys(required).map((key) => [key, "confirmed"])),
    sources: {},
    documents: [
      { id: "basis", kind: "legal_basis", filename: "sample.pdf", parse_status: "completed", created_at: "2026-08-06T00:00:00Z" },
      { id: "front", kind: "applicant_id_front", filename: "front.png", parse_status: "completed", created_at: "2026-08-06T00:00:00Z" },
      { id: "back", kind: "applicant_id_back", filename: "back.png", parse_status: "completed", created_at: "2026-08-06T00:00:00Z" }
    ],
    validated_revision: 8,
    generated_revision: 8,
    latest_generation_id: "generation-test",
    created_at: "2026-08-06T00:00:00Z",
    updated_at: "2026-08-06T00:00:00Z"
  };
}

describe("domain helpers", () => {
  it("用确定性减法计算尚未履行金额", () => {
    expect(calculateOutstanding("120000", "20000")).toBe("100000.00");
    expect(calculateOutstanding("invalid", "0")).toBe("");
  });

  it("根据服务端确认与版本状态派生步骤门禁", () => {
    expect(deriveStepGates(matterFixture())).toEqual([true, true, true, true]);
    const missingIdentity = matterFixture();
    missingIdentity.documents = missingIdentity.documents.filter((item) => item.kind !== "applicant_id_back");
    expect(deriveStepGates(missingIdentity)).toEqual([true, false, false, false]);
  });

  it("稳定显示金额与协议错误", () => {
    expect(formatMoney("100000")).toContain("100,000.00");
    expect(parseApiError({ data: { error: { message: "版本冲突" } } })).toBe("版本冲突");
    expect(parseApiError(null)).toBe("操作失败，请稍后重试。");
  });

  it("连续输入字段时合并当前 revision 草稿而不互相覆盖", () => {
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

    const refreshed = mergeDraftField(requestDraft, 7, { judgment_amount: "12000.00" }, "paid_amount", "0.00");
    expect(refreshed).toEqual({
      revision: 7,
      fields: { judgment_amount: "12000.00", paid_amount: "0.00" }
    });
  });
});
