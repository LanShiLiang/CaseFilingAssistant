import { describe, expect, it } from "vitest";

import type { Matter, ValidationIssue } from "@case-filing/contracts";

import {
  blockingIssuesToStepOneBlockers,
  collectStepOneBlockers
} from "./stepOneRequirements";

const requiredFields = {
  document_type: "民事调解书",
  case_number: "（2026）测字1号",
  rendering_court: "测试人民法院",
  judgment_amount: "10000.00",
  applicant_name: "测试申请执行人",
  applicant_id: "TEST-ID-APPLICANT",
  respondent_name: "测试被执行人",
  request_text: "请求依法强制执行。",
  filing_court: "测试人民法院",
  service_address: "测试地址（非真实）"
};

describe("step one requirements", () => {
  it("按业务模块列出缺失的执行依据、双方身份证和输入字段", () => {
    const blockers = collectStepOneBlockers(
      { documents: [] } as unknown as Matter,
      {}
    );

    expect(blockers).toEqual(expect.arrayContaining([
      expect.objectContaining({ section: "执行依据", message: "请上传民事调解书或民事判决书。" }),
      expect.objectContaining({ section: "申请执行人", message: "请上传身份证人像面。" }),
      expect.objectContaining({ section: "被执行人", message: "请上传身份证国徽面。" }),
      expect.objectContaining({ section: "请求与联系信息", message: "请填写送达地址。" })
    ]));
  });

  it("材料和必填字段齐全时不产生前端卡点", () => {
    const matter = {
      documents: [
        "legal_basis",
        "applicant_id_front",
        "applicant_id_back",
        "respondent_id_front",
        "respondent_id_back"
      ].map((kind) => ({ kind, active: true }))
    } as unknown as Matter;

    expect(collectStepOneBlockers(matter, requiredFields)).toEqual([]);
  });

  it("只把服务端 blocking 问题映射回步骤一卡点", () => {
    const issues = [
      { code: "required_field_missing", severity: "blocking", field: "case_number", message: "案号尚未填写。" },
      { code: "manual_review_required", severity: "info", message: "需要人工复核。" }
    ] as ValidationIssue[];

    expect(blockingIssuesToStepOneBlockers(issues)).toEqual([
      expect.objectContaining({ section: "规则检查", message: "案号尚未填写。" })
    ]);
  });
});
