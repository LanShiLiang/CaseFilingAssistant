from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.dossier import DossierV2
from app.models import Matter


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    field: str | None = None


STEP_ONE_FIELDS = {
    "document_type": "文书类型",
    "case_number": "案号",
    "rendering_court": "作出法院",
    "applicant_name": "申请执行人姓名",
    "applicant_id": "申请执行人身份证号",
    "respondent_name": "被执行人姓名",
}

STEP_TWO_FIELDS = {
    "judgment_amount": "文书确定金额",
    "paid_amount": "已履行金额",
    "outstanding_amount": "尚未履行金额",
    "request_text": "请求事项",
    "filing_court": "申请法院",
    "service_address": "送达地址",
}

SUPPORTED_DOCUMENT_TYPES = {"民事调解书", "民事判决书"}
SCOPE_MESSAGES = {
    "unsupported_multiple_applicants": "材料疑似包含多名申请执行人或原告，当前版本不适用。",
    "unsupported_multiple_respondents": "材料疑似包含多名被执行人或被告，当前版本不适用。",
    "unsupported_representative": "材料疑似包含代理人信息，请确认是否只是原诉讼信息。",
    "unsupported_organization_party": "材料疑似包含法人或组织主体，当前版本不适用。",
    "unsupported_multiple_obligations": "材料疑似包含多项独立义务，当前版本不适用。",
    "unsupported_complex_obligation": "材料疑似包含复杂履行关系，当前版本不适用。",
}


def _required_issues(dossier: DossierV2, fields: dict[str, str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field, label in fields.items():
        if not dossier.facts.get(field):
            issues.append(
                ValidationIssue(
                    code="required_field_missing",
                    severity="blocking",
                    field=field,
                    message=f"{label}尚未填写。",
                )
            )
        elif dossier.confirmations.get(field) != "confirmed":
            issues.append(
                ValidationIssue(
                    code="field_not_confirmed",
                    severity="blocking",
                    field=field,
                    message=f"{label}尚未完成人工确认。",
                )
            )
    return issues


def validate_matter(matter: Matter) -> list[ValidationIssue]:
    """服务端门禁是唯一权威；前端禁用按钮只能改善体验，不能替代这里。"""

    dossier = DossierV2.from_matter(matter)
    issues: list[ValidationIssue] = []
    if not matter.eligibility_confirmed:
        issues.append(
            ValidationIssue("eligibility_not_confirmed", "blocking", "适用条件尚未确认。")
        )

    kinds = {document.kind for document in matter.documents if document.active}
    if "legal_basis" not in kinds:
        issues.append(ValidationIssue("legal_basis_missing", "blocking", "执行依据尚未上传。"))
    for required_kind, label in (
        ("applicant_id_front", "申请执行人身份证人像面"),
        ("applicant_id_back", "申请执行人身份证国徽面"),
        ("respondent_id_front", "被执行人身份证人像面"),
        ("respondent_id_back", "被执行人身份证国徽面"),
    ):
        if required_kind not in kinds:
            issue_code = (
                "applicant_identity_missing"
                if required_kind.startswith("applicant_")
                else "respondent_identity_missing"
            )
            issues.append(
                ValidationIssue(issue_code, "blocking", f"{label}尚未上传。")
            )

    issues.extend(_required_issues(dossier, STEP_ONE_FIELDS))
    issues.extend(_required_issues(dossier, STEP_TWO_FIELDS))

    if dossier.facts.get("document_type") not in SUPPORTED_DOCUMENT_TYPES:
        issues.append(
            ValidationIssue(
                "unsupported_basis_type",
                "blocking",
                "当前版本只支持民事调解书或民事判决书。",
                "document_type",
            )
        )

    for signal in dossier.scope_signals:
        if signal.status == "open":
            issues.append(
                ValidationIssue(
                    signal.code,
                    "blocking",
                    SCOPE_MESSAGES[signal.code],
                )
            )

    active_documents = {document.id: document for document in matter.documents if document.active}
    for field in (*STEP_ONE_FIELDS, *STEP_TWO_FIELDS):
        if dossier.confirmations.get(field) != "confirmed":
            continue
        references = dossier.sources.get(field, [])
        if not references:
            issues.append(
                ValidationIssue(
                    "confirmed_field_source_missing",
                    "blocking",
                    f"{STEP_ONE_FIELDS.get(field) or STEP_TWO_FIELDS.get(field)}缺少可审计来源。",
                    field,
                )
            )
            continue
        for reference in references:
            if reference.document_id in {"user", "deterministic"}:
                continue
            document = active_documents.get(reference.document_id)
            if document is None or reference.parse_revision != document.parse_revision:
                issues.append(
                    ValidationIssue(
                        "source_reference_invalidated",
                        "blocking",
                        (
                            f"{STEP_ONE_FIELDS.get(field) or STEP_TWO_FIELDS.get(field)}"
                            "引用的材料已失效。"
                        ),
                        field,
                    )
                )
                break

    # 金额关系由 Decimal 精确校验，不能信任前端计算结果或浮点数近似。
    try:
        judgment = Decimal(dossier.facts.get("judgment_amount", ""))
        paid = Decimal(dossier.facts.get("paid_amount", ""))
        outstanding = Decimal(dossier.facts.get("outstanding_amount", ""))
        computation = dossier.amount_computation
        if (
            judgment < 0
            or paid < 0
            or outstanding < 0
            or judgment - paid != outstanding
            or computation is None
            or computation.input_revision != matter.revision
            or computation.judgment_amount != f"{judgment:.2f}"
            or computation.paid_amount != f"{paid:.2f}"
            or computation.result != f"{outstanding:.2f}"
            or computation.confirmation_status != "confirmed"
        ):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        issues.append(
            ValidationIssue(
                "amount_computation_mismatch",
                "blocking",
                "金额必须满足：文书确定金额 - 已履行金额 = 尚未履行金额，且均不小于 0。",
                "outstanding_amount",
            )
        )

    if not dossier.facts.get("document_date"):
        issues.append(
            ValidationIssue(
                "document_date_unconfirmed",
                "warning",
                "执行依据日期尚未确认，请在提交前人工核对。",
                "document_date",
            )
        )
    issues.append(
        ValidationIssue(
            "manual_review_required",
            "info",
            "生成文件必须由用户自行复核、签章并核对地方要求；系统不会提交法院。",
        )
    )
    return issues
