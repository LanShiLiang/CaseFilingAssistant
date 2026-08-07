from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from docx import Document as WordDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject

FIELD_LABELS = {
    "document_type": "文书类型",
    "case_number": "案号",
    "document_date": "文书日期",
    "rendering_court": "作出法院",
    "applicant_name": "申请执行人姓名",
    "applicant_id": "申请执行人身份证号",
    "applicant_identity_address": "身份证记载住址",
    "respondent_name": "被执行人姓名",
    "respondent_id": "被执行人身份证号",
    "judgment_amount": "文书确定金额",
    "paid_amount": "已履行金额",
    "outstanding_amount": "尚未履行金额",
    "request_text": "请求事项",
    "filing_court": "申请法院",
    "service_address": "送达地址",
    "phone": "联系电话",
    "bank_account": "收款账户",
    "property_clues": "财产线索",
}


@dataclass(frozen=True)
class GeneratedPackage:
    package_bytes: bytes
    preview_pdf: bytes
    package_sha256: str
    preview_sha256: str
    manifest: dict[str, Any]


class GenerationContext(BaseModel):
    """文书渲染的唯一输入；不得包含 ORM、未确认候选或 OCR 全文。"""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["generation_input_v1"]
    matter_id: str
    revision: int
    workflow_profile: str
    facts: dict[str, str]
    sources: dict[str, list[dict[str, Any]]]
    amount_computation: dict[str, Any]
    validation_run_id: str
    template_version: str
    rule_set_version: str
    generated_at: datetime

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> GenerationContext:
        return cls.model_validate(payload)


def _set_run_font(run, *, size: float = 12, bold: bool = False, name: str = "宋体") -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Times New Roman")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Times New Roman")


def _configure_document(document: WordDocument, generated_at: datetime) -> None:
    """命名覆盖 cn_legal_application：A4、2.54cm 页边距、宋体正文、无装饰标题。"""

    section = document.sections[0]
    fixed_time = generated_at.replace(tzinfo=None, microsecond=0)
    document.core_properties.created = fixed_time
    document.core_properties.modified = fixed_time
    document.core_properties.revision = 1
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)

    normal = document.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(12)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("需人工复核 · 未提交法院")
    _set_run_font(run, size=9)


def _add_title(document: WordDocument, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(20)
    run = paragraph.add_run(text)
    _set_run_font(run, size=22, bold=True, name="黑体")


def _add_label_paragraph(document: WordDocument, label: str, value: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Pt(0)
    label_run = paragraph.add_run(label)
    _set_run_font(label_run, bold=True)
    value_run = paragraph.add_run(value)
    _set_run_font(value_run)


def _add_body_paragraph(document: WordDocument, text: str, *, indent: bool = True) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        paragraph.paragraph_format.first_line_indent = Pt(24)
    run = paragraph.add_run(text)
    _set_run_font(run)


def _normalized_zip(content: bytes) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(content))
    output = io.BytesIO()
    with source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, source.read(name), compresslevel=9)
    return output.getvalue()


def _document_bytes(document: WordDocument) -> bytes:
    stream = io.BytesIO()
    document.save(stream)
    return _normalized_zip(stream.getvalue())


def build_application_docx(context: GenerationContext) -> bytes:
    facts = context.facts
    document = WordDocument()
    _configure_document(document, context.generated_at)
    _add_title(document, "强制执行申请书")
    _add_label_paragraph(document, "申请执行人：", facts["applicant_name"])
    _add_label_paragraph(document, "身份证号：", facts["applicant_id"])
    _add_label_paragraph(document, "送达地址：", facts["service_address"])
    if facts.get("phone"):
        _add_label_paragraph(document, "联系电话：", facts["phone"])
    _add_label_paragraph(document, "被执行人：", facts["respondent_name"])

    heading = document.add_paragraph()
    heading.paragraph_format.space_before = Pt(14)
    heading.paragraph_format.space_after = Pt(8)
    run = heading.add_run("申请事项")
    _set_run_font(run, size=14, bold=True, name="黑体")
    for index, line in enumerate(filter(None, facts["request_text"].splitlines()), start=1):
        text = line if line[:2].rstrip("、.").isdigit() else f"{index}、{line}"
        _add_body_paragraph(document, text, indent=False)

    heading = document.add_paragraph()
    heading.paragraph_format.space_before = Pt(14)
    run = heading.add_run("事实与理由")
    _set_run_font(run, size=14, bold=True, name="黑体")
    amount = Decimal(facts["outstanding_amount"])
    document_date = facts.get("document_date", "日期待核对")
    reason = (
        f"{facts['rendering_court']}作出的{facts['document_type']}"
        f"（案号：{facts['case_number']}，文书日期：{document_date}）已经确定金钱给付义务。"
        f"截至本次生成时，文书确定金额为人民币{Decimal(facts['judgment_amount']):,.2f}元，"
        f"已履行人民币{Decimal(facts['paid_amount']):,.2f}元，尚未履行人民币{amount:,.2f}元。"
        "上述金额和履行情况均由申请执行人根据材料人工确认。现申请依法强制执行。"
    )
    _add_body_paragraph(document, reason)
    _add_body_paragraph(document, "此致", indent=False)
    court = document.add_paragraph()
    court.alignment = WD_ALIGN_PARAGRAPH.LEFT
    court.paragraph_format.left_indent = Cm(1.5)
    run = court.add_run(facts["filing_court"])
    _set_run_font(run, bold=True)

    document.add_paragraph()
    signature = document.add_paragraph()
    signature.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_run_font(signature.add_run("申请执行人（签名）：____________"))
    signature_date = document.add_paragraph()
    signature_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_run_font(signature_date.add_run("日期：____年__月__日"))

    notice = document.add_paragraph()
    notice.paragraph_format.space_before = Pt(18)
    notice.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = notice.add_run("本文件由本地工具生成，仅供人工审阅，不代表已向法院提交。")
    _set_run_font(run, size=9, bold=True)

    return _document_bytes(document)


def _set_cell_text(cell, text: str, *, bold: bool = False, size: float = 10.5) -> None:
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.2
    run = paragraph.add_run(text)
    _set_run_font(run, size=size, bold=bold)


def _keep_row_together(row, *, repeat_header: bool = False) -> None:
    """避免审核表的一条记录被分页拆开，并让表头在每页重复。"""

    properties = row._tr.get_or_add_trPr()
    properties.append(OxmlElement("w:cantSplit"))
    if repeat_header:
        properties.append(OxmlElement("w:tblHeader"))


def build_material_list_docx(context: GenerationContext) -> bytes:
    document = WordDocument()
    _configure_document(document, context.generated_at)
    _add_title(document, "强制执行申请材料清单")
    _add_label_paragraph(document, "事项案号：", context.facts["case_number"])

    rows = [
        ("1", "强制执行申请书", "系统生成，打印前需人工复核并签名"),
        ("2", context.facts["document_type"], "执行依据，请按目标法院要求准备份数"),
        ("3", "申请执行人身份证明", "身份证正反面复印件；必要时核对原件要求"),
        ("4", "收款账户信息", "如目标法院要求，另行填写并人工确认"),
    ]
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [Cm(1.2), Cm(5.2), Cm(8.0)]
    for cell, width in zip(table.rows[0].cells, widths, strict=True):
        cell.width = width
    for cell, text in zip(table.rows[0].cells, ("序号", "材料", "核对说明"), strict=True):
        _set_cell_text(cell, text, bold=True)
    _keep_row_together(table.rows[0], repeat_header=True)
    for sequence, name, note in rows:
        row = table.add_row()
        cells = row.cells
        for cell, width in zip(cells, widths, strict=True):
            cell.width = width
        _set_cell_text(cells[0], sequence)
        _set_cell_text(cells[1], name)
        _set_cell_text(cells[2], note)
        _keep_row_together(row)

    _add_body_paragraph(
        document,
        "提示：本清单仅依据全国基础规则和当前已确认信息生成。各地法院的份数、格式、附件和窗口要求可能不同，提交前必须自行核对。",
    )
    return _document_bytes(document)


def build_source_audit_docx(context: GenerationContext) -> bytes:
    document = WordDocument()
    _configure_document(document, context.generated_at)
    _add_title(document, "字段来源核对表（内部审阅）")
    rows: list[tuple[str, str, str, str]] = []
    for field, value in context.facts.items():
        if not value:
            continue
        references = context.sources.get(field, [])
        source = "用户填写"
        if references:
            first = references[0]
            method = first.get("extraction_method")
            if method == "deterministic":
                source = "确定性计算：文书确定金额 - 已履行金额"
            elif method == "user":
                source = "用户填写或编辑后确认"
            else:
                snippet = " ".join(str(first.get("snippet", "")).split())
                if len(snippet) > 72:
                    snippet = f"{snippet[:72]}…"
                source = f"材料第{first.get('page') or '?'}页：{snippet}"
        rows.append(
            (
                FIELD_LABELS.get(field, field),
                value,
                source,
                "已确认",
            )
        )

    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [Cm(3.0), Cm(4.0), Cm(6.2), Cm(2.0)]
    for cell, text in zip(table.rows[0].cells, ("字段", "确认值", "来源", "状态"), strict=True):
        _set_cell_text(cell, text, bold=True, size=9.5)
    _keep_row_together(table.rows[0], repeat_header=True)
    for field, value, source, status in rows:
        row = table.add_row()
        cells = row.cells
        for cell, width in zip(cells, widths, strict=True):
            cell.width = width
        for cell, text in zip(cells, (field, value, source, status), strict=True):
            _set_cell_text(cell, text, size=9.5)
        _keep_row_together(row)
    return _document_bytes(document)


def _office_command() -> str:
    command = shutil.which("soffice") or shutil.which("libreoffice")
    if command is None:
        raise RuntimeError("document_conversion_unavailable")
    return command


def build_preview_pdf(application_docx: bytes, context: GenerationContext) -> bytes:
    """预览必须来自 ZIP 中同一份申请书 DOCX，不维护第二套正文 renderer。"""

    with tempfile.TemporaryDirectory(prefix="cfa-docx-preview-") as directory:
        root = Path(directory)
        profile = root / "lo-profile"
        profile.mkdir()
        source = root / "application.docx"
        source.write_bytes(application_docx)
        completed = subprocess.run(
            [
                _office_command(),
                "--headless",
                f"-env:UserInstallation={profile.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(root),
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        rendered = root / "application.pdf"
        if completed.returncode != 0 or not rendered.is_file():
            raise RuntimeError("document_conversion_failed")
        reader = PdfReader(rendered)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)
        fixed = context.generated_at.replace(microsecond=0).isoformat()
        writer.add_metadata(
            {
                "/Title": "强制执行申请书",
                "/Author": "Case Filing Assistant",
                "/CreationDate": fixed,
                "/ModDate": fixed,
            }
        )
        identity = hashlib.sha256(application_docx).digest()[:16]
        writer._ID = ArrayObject([ByteStringObject(identity), ByteStringObject(identity)])
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()


def generate_package(context: GenerationContext) -> GeneratedPackage:
    # 调用方已冻结并校验输入；这里不再读取数据库最新状态，只做确定性渲染。
    application = build_application_docx(context)
    checklist = build_material_list_docx(context)
    source_audit = build_source_audit_docx(context)
    preview = build_preview_pdf(application, context)
    manifest = {
        "matter_id": context.matter_id,
        "revision": context.revision,
        "workflow_profile": context.workflow_profile,
        "generation_input_schema": context.schema_version,
        "validation_run_id": context.validation_run_id,
        "template_version": context.template_version,
        "rule_set_version": context.rule_set_version,
        "generated_at": context.generated_at.replace(microsecond=0).isoformat(),
        "requires_manual_review": True,
        "files": {},
    }
    files = {
        "强制执行申请书.docx": application,
        "强制执行申请材料清单.docx": checklist,
        "字段来源核对表_内部审阅.docx": source_audit,
        "强制执行申请书.pdf": preview,
    }
    # 清单同时固定规则/模板版本和逐文件摘要，便于人工审阅时核对材料包是否被替换。
    manifest["files"] = {
        name: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        for name, content in files.items()
    }
    package_stream = io.BytesIO()
    with zipfile.ZipFile(package_stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content, compresslevel=9)
        manifest_info = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.external_attr = 0o600 << 16
        archive.writestr(
            manifest_info,
            json.dumps(
                manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
            compresslevel=9,
        )
    package_bytes = package_stream.getvalue()
    return GeneratedPackage(
        package_bytes=package_bytes,
        preview_pdf=preview,
        package_sha256=hashlib.sha256(package_bytes).hexdigest(),
        preview_sha256=hashlib.sha256(preview).hexdigest(),
        manifest=manifest,
    )
