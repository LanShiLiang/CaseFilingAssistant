import type { Matter, ValidationIssue } from "@case-filing/contracts";

import type { FormState, StepOneBlocker } from "./types";

const REQUIRED_DOCUMENTS = [
  { kind: "legal_basis", section: "执行依据", label: "民事调解书或民事判决书" },
  { kind: "applicant_id_front", section: "申请执行人", label: "身份证人像面" },
  { kind: "applicant_id_back", section: "申请执行人", label: "身份证国徽面" },
  { kind: "respondent_id_front", section: "被执行人", label: "身份证人像面" },
  { kind: "respondent_id_back", section: "被执行人", label: "身份证国徽面" }
] as const;

const REQUIRED_FIELDS = [
  { name: "document_type", section: "执行依据", label: "文书类型" },
  { name: "case_number", section: "执行依据", label: "案号" },
  { name: "rendering_court", section: "执行依据", label: "作出法院" },
  { name: "judgment_amount", section: "执行依据", label: "文书确定金额识别结果" },
  { name: "applicant_name", section: "申请执行人", label: "姓名" },
  { name: "applicant_id", section: "申请执行人", label: "身份证号" },
  { name: "respondent_name", section: "被执行人", label: "姓名" },
  { name: "request_text", section: "请求与联系信息", label: "请求事项" },
  { name: "filing_court", section: "请求与联系信息", label: "申请法院" },
  { name: "service_address", section: "请求与联系信息", label: "送达地址" }
] as const;

export const STEP_ONE_SUBMISSION_FIELDS = [
  ...REQUIRED_FIELDS.map(({ name }) => name),
  "document_date",
  "applicant_identity_address",
  "respondent_id",
  "paid_amount",
  "outstanding_amount",
  "phone",
  "bank_account",
  "property_clues"
] as const;

export function collectStepOneBlockers(
  matter: Pick<Matter, "documents">,
  fields: FormState
): StepOneBlocker[] {
  const activeKinds = new Set(
    matter.documents.filter(({ active }) => active).map(({ kind }) => kind)
  );
  const documentBlockers = REQUIRED_DOCUMENTS
    .filter(({ kind }) => !activeKinds.has(kind))
    .map(({ kind, section, label }) => ({
      id: `document:${kind}`,
      section,
      message: `请上传${label}。`
    }));
  const fieldBlockers = REQUIRED_FIELDS
    .filter(({ name }) => !fields[name]?.trim())
    .map(({ name, section, label }) => ({
      id: `field:${name}`,
      section,
      message: name === "judgment_amount"
        ? "未从执行依据中识别到文书确定金额，请更换清晰材料后重试。"
        : `请填写${label}。`
    }));
  return [...documentBlockers, ...fieldBlockers];
}

export function blockingIssuesToStepOneBlockers(
  issues: readonly ValidationIssue[]
): StepOneBlocker[] {
  return issues
    .filter(({ severity }) => severity === "blocking")
    .map(({ code, field, message }, index) => ({
      id: `validation:${code}:${field ?? index}`,
      section: "规则检查",
      message
    }));
}
