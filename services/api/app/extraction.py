from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from docx import Document as WordDocument
from PIL import Image
from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedPage:
    page: int
    text: str
    method: str


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    facts: dict[str, str]
    sources: dict[str, list[dict[str, Any]]]
    warnings: list[str]
    scope_signals: list[dict[str, Any]] = field(default_factory=list)


CASE_NUMBER_RE = re.compile(
    r"[（(]\s*\d{4}\s*[）)]\s*(?:[^\s，。；;]\s*){1,30}?号"
)
COURT_RE = re.compile(r"[\u4e00-\u9fff]{2,40}人民法院")
DATE_RE = re.compile(r"(20\d{2})年(\d{1,2})月(\d{1,2})日")
AMOUNT_RE = re.compile(r"人民币\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*元")
PARTY_RE = re.compile(
    r"(?P<label>申请执行人|申请人|原告|被执行人|被申请人|被告)"
    r"\s*[：:]\s*(?P<name>[\u4e00-\u9fff·]{2,20})"
)
IDENTITY_NUMBER_RE = re.compile(
    r"(?:公民身份号码|公民身份号|身份证号码|身份证号|身份号码)"
    r"\s*[：:]?\s*(?P<number>(?:\d\s*){17}[0-9Xx])"
)
APPLICANT_LABELS = frozenset({"申请执行人", "申请人", "原告"})
RESPONDENT_LABELS = frozenset({"被执行人", "被申请人", "被告"})
IDENTITY_CHECKSUM_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
IDENTITY_CHECKSUM_CODES = "10X98765432"


def image_ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def document_conversion_available() -> bool:
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


def _office_command() -> str:
    command = shutil.which("soffice") or shutil.which("libreoffice")
    if command is None:
        raise ValueError("document_conversion_unavailable")
    return command


def _ocr_image(path: Path) -> tuple[str, str | None]:
    completed = subprocess.run(
        ["tesseract", str(path), "stdout", "-l", "chi_sim+eng"],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        return "", "image_ocr_failed_manual_input_allowed"
    return completed.stdout.strip(), None


def _ocr_pdf(path: Path, page_count: int) -> tuple[list[ExtractedPage], list[str]]:
    warnings: list[str] = []
    if not image_ocr_available() or shutil.which("pdftoppm") is None:
        return [], ["scanned_pdf_requires_manual_input"]
    with tempfile.TemporaryDirectory(prefix="cfa-pdf-ocr-") as directory:
        prefix = Path(directory) / "page"
        completed = subprocess.run(
            ["pdftoppm", "-png", "-r", "200", str(path), str(prefix)],
            capture_output=True,
            text=True,
            timeout=max(120, page_count * 20),
            check=False,
        )
        if completed.returncode != 0:
            return [], ["scanned_pdf_requires_manual_input"]
        pages: list[ExtractedPage] = []
        for index, image_path in enumerate(sorted(Path(directory).glob("page-*.png")), start=1):
            text, warning = _ocr_image(image_path)
            if warning:
                warnings.append(warning)
            pages.append(ExtractedPage(page=index, text=text, method="ocr"))
        return pages, sorted(set(warnings))


def _docx_pages(path: Path, max_pdf_pages: int) -> tuple[list[ExtractedPage], list[str]]:
    if not document_conversion_available():
        document = WordDocument(str(path))
        text = "\n".join(
            paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
        )
        return [ExtractedPage(page=1, text=text, method="text")], [
            "docx_pagination_unavailable"
        ]
    with tempfile.TemporaryDirectory(prefix="cfa-docx-read-") as directory:
        output = Path(directory)
        profile = output / "lo-profile"
        profile.mkdir()
        completed = subprocess.run(
            [
                _office_command(),
                "--headless",
                f"-env:UserInstallation={profile.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output),
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        pdf_path = output / f"{path.stem}.pdf"
        if completed.returncode != 0 or not pdf_path.is_file():
            raise ValueError("docx_conversion_failed")
        return extract_pages(pdf_path, "application/pdf", max_pdf_pages)


def extract_pages(
    path: Path, mime_type: str, max_pdf_pages: int
) -> tuple[list[ExtractedPage], list[str]]:
    warnings: list[str] = []
    suffix = path.suffix.lower()
    # 优先读取文件自身文本层；只有图片进入本地 OCR，任何失败都降级为人工填写而不是猜测事实。
    if mime_type == "application/pdf" or suffix == ".pdf":
        reader = PdfReader(str(path))
        if len(reader.pages) > max_pdf_pages:
            raise ValueError("pdf_page_limit_exceeded")
        pages = [
            ExtractedPage(page=index + 1, text=(page.extract_text() or "").strip(), method="text")
            for index, page in enumerate(reader.pages)
        ]
        if not any(page.text for page in pages):
            ocr_pages, ocr_warnings = _ocr_pdf(path, len(reader.pages))
            if ocr_pages:
                pages = ocr_pages
            warnings.extend(ocr_warnings)
        return pages, warnings
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        return _docx_pages(path, max_pdf_pages)
    if mime_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png"}:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > 40_000_000:
                raise ValueError("image_pixel_limit_exceeded")
            image.verify()
        if not image_ocr_available():
            warnings.append("image_ocr_unavailable_manual_input_allowed")
            return [ExtractedPage(page=1, text="", method="ocr")], warnings
        text, warning = _ocr_image(path)
        if warning:
            warnings.append(warning)
            return [ExtractedPage(page=1, text="", method="ocr")], warnings
        return [ExtractedPage(page=1, text=text, method="ocr")], warnings
    raise ValueError("unsupported_document_type")


def _first_match(
    pattern: re.Pattern[str], pages: list[ExtractedPage]
) -> tuple[str, ExtractedPage] | None:
    for page in pages:
        match = pattern.search(page.text)
        if match:
            return match.group(0).strip(), page
    return None


def _valid_identity_number(value: str) -> bool:
    normalized = value.upper()
    if not re.fullmatch(r"\d{17}[0-9X]", normalized):
        return False
    try:
        datetime.strptime(normalized[6:14], "%Y%m%d")
    except ValueError:
        return False
    checksum_index = sum(
        int(digit) * weight
        for digit, weight in zip(normalized[:17], IDENTITY_CHECKSUM_WEIGHTS, strict=True)
    ) % 11
    return normalized[-1] == IDENTITY_CHECKSUM_CODES[checksum_index]


def _party_fields(
    pages: list[ExtractedPage],
) -> dict[str, tuple[str, ExtractedPage, str]]:
    """从每个当事人段落提取角色绑定的姓名和身份证号，禁止跨角色猜测。"""

    fields: dict[str, tuple[str, ExtractedPage, str]] = {}
    for page in pages:
        matches = list(PARTY_RE.finditer(page.text))
        for index, match in enumerate(matches):
            is_applicant = match.group("label") in APPLICANT_LABELS
            prefix = "applicant" if is_applicant else "respondent"
            name_field = f"{prefix}_name"
            fields.setdefault(name_field, (match.group("name").strip(), page, match.group("name")))

            # 身份证号必须位于当前角色起点与下一个角色起点之间，避免把被告号码写给原告。
            block_end = matches[index + 1].start() if index + 1 < len(matches) else len(page.text)
            party_block = page.text[match.end():block_end]
            compact_block = "".join(party_block.split())
            identity_match = IDENTITY_NUMBER_RE.search(compact_block)
            if identity_match is None:
                continue
            raw_number = identity_match.group("number")
            identity_number = "".join(raw_number.split()).upper()
            if _valid_identity_number(identity_number):
                source_value = (
                    identity_number if identity_number in page.text else match.group("name")
                )
                fields.setdefault(f"{prefix}_id", (identity_number, page, source_value))
    return fields


def _source(
    document_id: str,
    page: ExtractedPage,
    value: str,
    source_value: str | None = None,
) -> dict[str, Any]:
    position = page.text.find(source_value or value)
    if position < 0:
        position = 0
    start = max(0, position - 24)
    end = min(len(page.text), position + len(value) + 48)
    return {
        "document_id": document_id,
        "page": page.page,
        "snippet": page.text[start:end].replace("\n", " ").strip(),
        "extraction_method": page.method,
        "confidence": 0.92 if page.method == "text" else 0.72,
    }


def _scope_signal(
    document_id: str, code: str, page: ExtractedPage, snippet: str
) -> dict[str, Any]:
    identity = hashlib.sha256(
        f"{document_id}|{code}|{page.page}|{snippet}".encode()
    ).hexdigest()[:24]
    return {
        "id": identity,
        "code": code,
        "document_id": document_id,
        "page": page.page,
        "snippet": " ".join(snippet.split())[:160],
        "status": "open",
    }


def _scope_signals(document_id: str, pages: list[ExtractedPage]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    role_patterns = (
        (
            "unsupported_multiple_applicants",
            re.compile(r"(?:申请执行人|申请人|原告)\s*[：:]\s*([\u4e00-\u9fff·]{2,30})"),
        ),
        (
            "unsupported_multiple_respondents",
            re.compile(r"(?:被执行人|被申请人|被告)\s*[：:]\s*([\u4e00-\u9fff·]{2,30})"),
        ),
    )
    full_text = "\n".join(page.text for page in pages)
    for code, pattern in role_patterns:
        matches = []
        for page in pages:
            matches.extend((match.group(1), page) for match in pattern.finditer(page.text))
        unique_names = {name for name, _ in matches}
        if len(unique_names) > 1:
            page = matches[0][1]
            signals.append(_scope_signal(document_id, code, page, "、".join(sorted(unique_names))))

    keyword_groups = (
        (
            "unsupported_representative",
            re.compile(r"委托诉讼代理人|委托代理人|代理律师"),
        ),
        (
            "unsupported_organization_party",
            re.compile(r"法定代表人|统一社会信用代码|(?:有限责任|股份有限)?公司"),
        ),
        (
            "unsupported_multiple_obligations",
            re.compile(r"(?:第一项|第二项|第一笔|第二笔|多项债务)"),
        ),
        (
            "unsupported_complex_obligation",
            re.compile(r"分期履行|条件成就|债权转让|继承|权利承受|抵扣顺序"),
        ),
    )
    for code, pattern in keyword_groups:
        match = pattern.search(full_text)
        if match:
            page = next(page for page in pages if pattern.search(page.text))
            signals.append(_scope_signal(document_id, code, page, match.group(0)))
    return signals


def parse_legal_basis(
    path: Path, mime_type: str, document_id: str, max_pdf_pages: int
) -> ExtractionResult:
    pages, warnings = extract_pages(path, mime_type, max_pdf_pages)
    full_text = "\n\f\n".join(page.text for page in pages)
    facts: dict[str, str] = {}
    sources: dict[str, list[dict[str, Any]]] = {}

    # MVP 只用确定性规则产出候选，同时为每个候选记录页码、片段、方法和置信度。
    mappings: list[tuple[str, tuple[str, ExtractedPage] | None]] = [
        ("case_number", _first_match(CASE_NUMBER_RE, pages)),
        ("rendering_court", _first_match(COURT_RE, pages)),
    ]
    for field_name, candidate in mappings:
        if candidate:
            value, page = candidate
            if field_name == "case_number":
                value = "".join(value.split())
            facts[field_name] = value
            sources[field_name] = [_source(document_id, page, value)]

    for field_name, (value, page, source_value) in _party_fields(pages).items():
        facts[field_name] = value
        sources[field_name] = [_source(document_id, page, value, source_value)]

    date_candidate = _first_match(DATE_RE, pages)
    if date_candidate:
        raw_date, page = date_candidate
        match = DATE_RE.search(raw_date)
        if match:
            facts["document_date"] = (
                f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
            )
            sources["document_date"] = [_source(document_id, page, raw_date)]

    if "调解书" in full_text:
        facts["document_type"] = "民事调解书"
    elif "判决书" in full_text:
        facts["document_type"] = "民事判决书"
    if "document_type" in facts:
        page = next((item for item in pages if facts["document_type"] in item.text), pages[0])
        sources["document_type"] = [_source(document_id, page, facts["document_type"])]

    amount_candidate = _first_match(AMOUNT_RE, pages)
    if amount_candidate:
        raw_amount, page = amount_candidate
        match = AMOUNT_RE.search(raw_amount)
        if match:
            try:
                amount = Decimal(match.group(1).replace(",", ""))
                facts["judgment_amount"] = f"{amount:.2f}"
                sources["judgment_amount"] = [_source(document_id, page, raw_amount)]
            except InvalidOperation:
                warnings.append("amount_candidate_invalid")

    return ExtractionResult(
        text=full_text,
        facts=facts,
        sources=sources,
        warnings=warnings,
        scope_signals=_scope_signals(document_id, pages),
    )
