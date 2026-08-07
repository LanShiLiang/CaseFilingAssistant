# Mainland China Legal-Document Assistant: Product Scope and Implementation Plan

Update note (2026-08-06): the current MVP is a local self-service tool limited to one enforcement applicant, one respondent, and no representative. Desktop Web is the visual and efficiency baseline, while the same application keeps the four-step core flow usable on mobile Web. P0 excludes login, lawyer workspaces, complex party relationships, generative AI, WeChat Mini Program, cloud storage, and court-platform integration. The v0.5 Chinese product, frontend, and backend plans are the implementation source of truth; actor-mode selection, complex roles, Mini Program support, and AI assistance are retained only as later planning.

## 1. Purpose

Build a legal-document assistant focused exclusively on Mainland China legal and judicial rules. The initial MVP helps users generate a review-required application-for-enforcement material package from uploaded legal documents for submission to a Mainland China people's court by the user or their authorized representative.

The assistant must not submit filings, pay fees, serve documents, contact courts, contact opposing parties, or represent that a filing is legally sufficient. Its role is to organize source materials, extract court-relevant facts, generate application materials, flag missing requirements, and prepare a review-ready export.

## 2. Mainland China Scope Boundary

### Included

- People's court application-for-enforcement materials under Mainland China procedure.
- Rules and source tracking for national laws, Supreme People's Court judicial interpretations, Supreme People's Court normative documents, official litigation-document styles, and local court filing guidance.
- Draft package generation in Simplified Chinese by default.
- Support for user-uploaded source documents including judgments, rulings, mediation statements, arbitral awards, notarized creditor-right documents with enforceability effect, proof of legal effectiveness, service materials, party identity documents, enterprise registration materials, payment records, asset clues, powers of attorney, and prior correspondence.
- Human review and approval before export.

### Excluded

- Hong Kong, Macau, Taiwan, or foreign court procedure, except where a later Mainland China recognition-and-enforcement workflow is explicitly scoped.
- External court filing, online filing, fee payment, service, notice, enforcement inquiry submission, or other outbound action.
- Legal advice, strategy recommendation, representation, or final legal sufficiency determination.
- Automatically deciding jurisdiction, limitation-period compliance, enforceability, standing, or admissibility without reviewer confirmation.

## 3. Authoritative Source Strategy

The product should maintain a versioned Mainland China authority registry. Each rules pack and template must identify its source, source URL, issuing body, document name, document number, promulgation date, effective date, amendment status, retrieval date, and reviewer approval status.

Initial authority classes:

- National laws from the National Laws and Regulations Database and China NPC sources, especially the Civil Procedure Law of the People's Republic of China as amended in 2023 and effective from January 1, 2024.
- Supreme People's Court judicial interpretations and official gazette materials, including execution-procedure interpretations and execution objection/reconsideration rules.
- Supreme People's Court execution case filing and closing normative documents.
- Supreme People's Court public litigation guidance and official litigation document styles.
- People's Court Online Litigation Rules and People's Court Online Operation Rules for electronic-material format, clarity, and platform-related requirements, while keeping MVP export-only and non-submitting.
- Local high/intermediate/basic people's court guidance for court-specific material lists, local template variants, copy counts, upload limits, naming conventions, and service-window practices.

Source governance requirements:

- Prefer official sources: `flk.npc.gov.cn`, `npc.gov.cn`, `court.gov.cn`, `gongbao.court.gov.cn`, and official local court domains.
- Treat commercial legal databases, law-firm articles, blogs, and unofficial reposts as secondary references only.
- Do not activate or update a rule in production until a legal reviewer approves the official-source mapping.
- Store every source snapshot or hash where licensing and access rules permit.
- Add an expiration/recheck schedule for every rules pack, with shorter recheck intervals for local court guidance and online-platform requirements.
- Warn users when a rules pack has not been reviewed recently or when a local court requirement has not been configured.

## 4. MVP Scope

### Included

- Local matter workspace for one application-for-enforcement matter.
- Optional target-court selection when known, with nationwide baseline rules available even when no local rules pack exists.
- Enforcement scenario selection, initially:
  - Domestic people's court civil judgment, ruling, or mediation statement.
  - Domestic arbitral award or mediation document, if included in the first approved rules pack.
- Upload flow for PDF, DOCX, images, and text files.
- OCR and Chinese text extraction for scanned materials.
- Document classification for:
  - Effective legal instrument.
  - Proof of effectiveness or enforceability.
  - Proof of service or delivery.
  - Applicant identity/qualification.
  - Respondent identity/qualification.
  - Representative authorization materials.
  - Payment or performance records.
  - Asset clue materials.
  - Prior enforcement-related correspondence.
- Structured extraction of:
  - Case caption, cause of action, case number, issuing court/arbitral institution, document type, and effective date.
  - Applicant, respondent, legal representative, entrusted agent, and contact details.
  - Enforceable obligations, including monetary payment, delivery of property, performance of acts, or non-performance obligations.
  - Principal, interest, delayed-performance interest, costs, accepted payments, and outstanding amount.
  - Performance deadline and start date for limitation-period calculation.
  - Target court, jurisdiction basis, respondent domicile, and property-location clues.
  - Source pages or text spans for every material extracted fact.
- Evidence map linking extracted facts to uploaded source pages.
- Mainland China rules-pack checklist for required materials and court-relevant normative requirements.
- Gap analysis for missing effectiveness proof, missing identity materials, unclear service/effectiveness, inconsistent party names, amount conflicts, missing asset clues, expired or uncertain limitation period, unsupported requested relief, and missing authorization documents.
- Draft package generation using approved Mainland China templates:
  - `强制执行申请书`.
  - Applicant/respondent information sheet, if required by local court.
  - Exhibit/materials list.
  - Calculation schedule for amounts and delayed-performance interest.
  - Authorization or representative-material checklist.
  - Internal legal-review checklist.
- Review UI where users can accept, edit, reject, or manually override extracted facts.
- Export as DOCX and PDF bundle, with a source-backed exhibit list and rule-pack/version appendix.
- Audit trail of uploads, extraction results, template versions, rule-pack versions, user edits, review decisions, and export events.

### Excluded From MVP

- Court platform login or integration.
- Online case filing through People's Court Online Service, local litigation service platforms, WeChat mini-programs, or any other channel.
- Fee calculation as a final payable court amount.
- Court acceptance prediction.
- Enforcement asset search, respondent credit inquiry, or automated access to China enforcement information systems.
- Batch filing or collection-portfolio workflows.
- Foreign judgment, Hong Kong/Macau/Taiwan judgment, or foreign arbitral award recognition-and-enforcement packages unless selected as a later Mainland China-specific expansion.

## 5. Primary User Workflow

1. Create matter workspace.
2. Select Mainland China court, province/city, and enforcement scenario.
3. Upload source legal materials.
4. System parses, OCRs, classifies, and indexes the materials.
5. System extracts candidate facts with source citations.
6. User reviews and confirms facts in Simplified Chinese.
7. System runs Mainland China rules-pack readiness checks.
8. User resolves gaps or marks them as accepted exceptions.
9. System generates application-for-enforcement materials from approved templates.
10. User reviews generated files with highlighted source-backed facts and editable sections.
11. System exports a review-ready material package.

## 6. Product Guardrails

- Display "manual review required / not filed" status throughout the workflow.
- Require user confirmation for all legally material facts.
- Require a source citation or explicit user-entered value for every factual assertion in the generated files.
- Separate uploaded-source facts, user-entered facts, rule-pack requirements, and legal-review notes.
- Do not infer effectiveness, finality, enforceability, jurisdiction, limitation-period compliance, identity authority, or agent authority without supporting source material and reviewer confirmation.
- Flag uncertainty instead of resolving it silently.
- Block clean export when critical placeholders remain unresolved unless a reviewer records an explicit exception.
- Keep Mainland China rule packs and templates versioned, source-linked, and legal-review approved.
- Preserve immutable audit records for generation and export.
- Do not submit, upload, serve, email, mail, message, or otherwise transmit materials externally.

## 7. Mainland China Rules-Pack Requirements

Each rules pack should be court/scenario specific where needed and include:

- Supported legal-instrument types.
- Accepted applicant/respondent identity materials for natural persons, legal persons, and other organizations.
- Authorization material requirements for agents and legal representatives.
- Proof-of-effectiveness requirements.
- Required content of `强制执行申请书`, including parties, facts/reasons, requested enforcement items, enforcement target, known property clues, court name, signature/seal, and date.
- Required attachments and copy requirements.
- Jurisdiction rules and court-selection basis.
- Application deadline rules and calculation prompts.
- Amount-calculation rules, including principal, interest, delayed-performance interest, costs, partial payments, and calculation-through date.
- Requirements for Chinese-language documents, translation, notarization, legalization/apostille, or certification when source materials are not in Simplified Chinese.
- Electronic-file requirements if the user later manually files online, including file type, clarity, naming, page order, and material categorization.
- Local court-specific variants, warnings, and unsupported areas.

## 8. System Architecture

### Frontend

- Matter dashboard.
- Upload and document inventory view.
- OCR quality and document-readability review.
- Extracted-fact review table with page/source preview.
- Mainland China rules-pack checklist view.
- Amount calculation worksheet.
- Draft editor/reviewer with source-backed highlights.
- Export panel with "not filed" status and rule-pack appendix.

### Backend Services

- Authentication, authorization, and tenant isolation.
- File upload, malware scanning, storage, retention, and deletion controls.
- OCR and document text extraction optimized for Simplified Chinese legal documents.
- Document classifier.
- Structured extraction pipeline.
- Authority registry service.
- Rules-pack and template service.
- Validation/checklist engine.
- Amount-calculation service.
- Document assembly service for DOCX/PDF outputs.
- Audit-log service.

### AI Pipeline

- Parse uploaded materials into normalized Chinese text, page references, and document metadata.
- Classify document type and confidence.
- Extract structured candidate facts into a Mainland China enforcement schema.
- Attach extracted facts to source page coordinates or text spans where possible.
- Detect contradictions across names, case numbers, dates, amounts, document types, and performance status.
- Ask focused reviewer questions for missing or ambiguous facts.
- Draft documents only from confirmed facts, approved templates, and approved rules-pack requirements.
- Produce an explanation log showing which source documents, rule-pack entries, and templates were used.

## 9. Suggested Data Model

- `Matter`: workspace, province, city, court, enforcement scenario, language, user/team, status.
- `AuthoritySource`: issuing body, hierarchy, source URL, document number, promulgation date, effective date, amendment status, retrieval date, checksum/snapshot pointer.
- `RulePack`: court/scenario, source mappings, version, effective date, recheck date, reviewer approval status.
- `Template`: document type, court/scenario binding, source basis, version, required facts.
- `Party`: name, role, natural/legal-person type, ID/registration data, domicile, contact details, legal representative.
- `Agent`: attorney or entrusted agent details, authorization basis, license/firm data where supplied.
- `SourceDocument`: file metadata, document type, OCR status, page count, hash, language, source role.
- `SourceSpan`: document id, page, coordinates or text span, extracted text.
- `ExtractedFact`: schema key, value, confidence, source spans, review status, reviewer notes.
- `AmountComponent`: principal, interest, delayed-performance interest, costs, payments, currency, calculation basis, calculation-through date.
- `JurisdictionBasis`: candidate court, basis type, source facts, review status.
- `ValidationIssue`: severity, rule-pack entry, affected fact/document, resolution status.
- `FilingPackage`: included documents, exhibits, validation state, export history, rule-pack/template versions.
- `AuditEvent`: actor, action, timestamp, object id, version/hash.

## 10. Enforcement-Package Readiness Checks

- Mainland China jurisdiction and enforcement scenario selected.
- Target people's court selected or flagged as unresolved.
- Effective legal instrument uploaded and readable.
- Case number, issuing authority, document type, parties, effective date, and enforceable obligations extracted.
- Proof of effectiveness/enforceability present or flagged.
- Applicant and respondent identity materials present or flagged.
- Legal representative and entrusted-agent materials present where applicable.
- Enforcement request does not exceed the obligations confirmed in the effective legal instrument unless separately supported and reviewed.
- Monetary amount, interest, delayed-performance interest, costs, payments, and outstanding balance calculated with visible assumptions.
- Performance deadline and application deadline reviewed.
- Known respondent property clues captured where supplied.
- Required local court materials configured or local-court gap warning shown.
- Exhibits are numbered, referenced, and present.
- Generated files contain no unresolved placeholders.
- User has reviewed all high-impact facts and validation warnings.

## 11. Implementation Phases

### Phase 0: Mainland China Scope Lock

- Confirm the nationwide baseline and first enforcement scenario without limiting MVP to a pilot province, city, or court.
- Collect official national law, SPC, and local court source materials.
- Define the authority registry schema and source refresh process.
- Define legal-review owner for templates and rules packs.
- Decide whether domestic arbitral awards are included in MVP or deferred.
- Decide retention, privacy, and audit requirements for Chinese legal documents and identity materials.

### Phase 1: Source Registry and Prototype

- Build authority registry with source URL, retrieval date, source hierarchy, and reviewer status.
- Build upload, parsing, OCR, and document inventory.
- Implement a Mainland China matter schema.
- Add extraction for parties, case numbers, court/arbitral institution, dates, obligations, and amounts.
- Build source-citation review UI.
- Generate an internal package-readiness checklist from the first approved rules pack.

### Phase 2: MVP Draft Generator

- Implement versioned `强制执行申请书` and materials-list templates.
- Add confirmed-fact workflow.
- Add amount calculation worksheet and reviewer confirmation.
- Generate a DOCX/PDF application package that requires manual review.
- Add exhibit/materials index generation.
- Add validation workflow and export blocking for critical unresolved issues.

### Phase 3: Reliability and Legal Review

- Add regression test corpus using anonymized or synthetic Mainland China enforcement materials.
- Add extraction accuracy evaluation for Chinese legal document formats.
- Add template snapshot tests.
- Add rule-pack versioning, recheck alerts, and legal-review approval flow.
- Add audit-log export.
- Add local court rules-pack update playbook.

### Phase 4: Broader Mainland China Filing Assistant

- Expand to additional courts and local rule packs.
- Add more enforcement scenarios, such as notarized creditor-right documents, domestic arbitral awards, administrative non-litigation enforcement, and recognition/enforcement workflows in Mainland China.
- Add broader civil-case filing package generation.
- Add collaboration, comments, reviewer roles, and task assignments.
- Consider read-only court or public-source integrations only after explicit product approval.
- Consider controlled filing integrations only in a separately approved future product phase.

## 12. MVP Engineering Backlog

1. Create Mainland China matter workspace and metadata model.
2. Implement secure file upload, malware scanning, storage, retention, and deletion controls.
3. Add Chinese PDF/DOCX text extraction and OCR for scanned PDFs/images.
4. Build document classification pipeline for enforcement materials.
5. Define extraction schema and confidence model.
6. Build extracted-fact review UI with source-page viewer.
7. Create authority registry service.
8. Create first Mainland China rules-pack format.
9. Create the first nationwide-baseline `强制执行申请书` template.
10. Implement rules-pack checklist and validation engine.
11. Build amount-calculation worksheet.
12. Build DOCX/PDF assembly service.
13. Build exhibit/materials index generation.
14. Add audit events for uploads, review, generation, rule-pack use, and export.
15. Create synthetic Chinese test set and evaluation harness.
16. Add local audit events, identity-document handling controls, and security logging; defer role-based access to the platform phase.

## 13. Quality and Testing Plan

- Unit tests for schema validation, amount calculations, deadline prompts, checklist rules, and template rendering.
- Golden-file tests for generated DOCX/PDF outputs in Simplified Chinese.
- OCR and extraction tests on synthetic clean and scanned Mainland China legal documents.
- Source-citation tests requiring every generated factual assertion to map to a confirmed fact, approved rule-pack entry, or user-entered value.
- Authority-registry tests ensuring every rule-pack item has an official-source mapping and reviewer status.
- Adversarial tests for conflicting party names, multiple case numbers, amended judgments, missing effective-date proof, partial payments, illegible scans, local court variants, stale templates, and unsupported requested enforcement items.
- Manual legal review of the first rules pack and templates before user-facing release.
- Security tests for file upload handling, tenant isolation, access control, identity-document exposure, and audit log integrity.

## 14. Key Decisions Needed

- Whether any local court rules pack should be bundled as an optional overlay; MVP should not be limited to one province, city, or court.
- First enforcement scenario: domestic civil judgment/ruling/mediation statement only, or include domestic arbitral awards.
- Target users: individuals, enterprises, law firms, in-house legal teams, or collection teams.
- Whether attorney/legal-reviewer approval is required before export in the first release.
- Required retention period and deletion model for uploaded judgments, IDs, business licenses, and authorization materials.
- Whether generated materials must strictly follow one official court template, local court templates, or a configurable template family.
- Whether bilingual support is needed later; MVP should default to Simplified Chinese.

## 15. Initial Official Sources Checked

- National People's Congress, 2023 amendment to the Civil Procedure Law, adopted September 1, 2023 and effective January 1, 2024: https://www.npc.gov.cn/npc/c2/c30834/202309/t20230901_431419.html
- Supreme People's Court, official execution procedure guidance, including enforceable instruments, court selection, timing, materials, and application format: https://www.court.gov.cn/zixun/xiangqing/78732.html
- Supreme People's Court, official `申请书(申请执行用)` document style: https://www.court.gov.cn/susongyangshi/xiangqing/639.html
- Supreme People's Court Gazette, `关于人民法院执行工作若干问题的规定（试行）`: https://gongbao.court.gov.cn/Details/a76a77ab3bdb8ee78e4189146c3444.html
- Supreme People's Court Gazette, `关于执行案件立案、结案若干问题的意见`: https://gongbao.court.gov.cn/Details/0325083e8eba22d4856cfbf76261c2.html
- Supreme People's Court, `人民法院在线诉讼规则`: https://www.court.gov.cn/fabu/xiangqing/309551.html
- Supreme People's Court, `人民法院在线运行规则`: https://www.court.gov.cn/zixun/xiangqing/346471.html

## 16. Recommended First Release Definition

The first release should be a private beta for one Mainland China court or local court cluster and one enforcement scenario. It should produce a `强制执行申请书` package from uploaded materials, with source-backed facts, Mainland China rules-pack validation, a materials/exhibit index, a calculation worksheet, and a human-review export step. It should not file, serve, message, upload, or submit anything externally.

Success criteria:

- The assistant can process a complete synthetic Mainland China enforcement matter and generate a coherent application package.
- At least 95% of generated factual assertions are linked to confirmed facts, approved rule-pack entries, or user-entered values.
- Every rule-pack checklist item maps to an official source and a legal-review status.
- Critical missing information blocks clean export or is explicitly acknowledged by the reviewer.
- A reviewer can trace every material fact in the generated files back to uploaded sources.
- Template and rule-pack versions, official-source references, and retrieval dates are visible in the export audit log.
