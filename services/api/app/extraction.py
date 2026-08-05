from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
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


CASE_NUMBER_RE = re.compile(r"[（(]\s*\d{4}\s*[）)][^\s，。；;]{1,30}?号")
COURT_RE = re.compile(r"[\u4e00-\u9fff]{2,40}人民法院")
DATE_RE = re.compile(r"(20\d{2})年(\d{1,2})月(\d{1,2})日")
AMOUNT_RE = re.compile(r"人民币\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*元")


def image_ocr_available() -> bool:
    return shutil.which("tesseract") is not None


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
            warnings.append("scanned_pdf_requires_manual_input")
        return pages, warnings
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or suffix == ".docx"
    ):
        document = WordDocument(str(path))
        text = "\n".join(
            paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
        )
        return [ExtractedPage(page=1, text=text, method="text")], warnings
    if mime_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png"}:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > 40_000_000:
                raise ValueError("image_pixel_limit_exceeded")
            image.verify()
        if not image_ocr_available():
            warnings.append("image_ocr_unavailable_manual_input_allowed")
            return [ExtractedPage(page=1, text="", method="ocr")], warnings
        completed = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", "chi_sim+eng"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if completed.returncode != 0:
            warnings.append("image_ocr_failed_manual_input_allowed")
            return [ExtractedPage(page=1, text="", method="ocr")], warnings
        return [ExtractedPage(page=1, text=completed.stdout.strip(), method="ocr")], warnings
    raise ValueError("unsupported_document_type")


def _first_match(
    pattern: re.Pattern[str], pages: list[ExtractedPage]
) -> tuple[str, ExtractedPage] | None:
    for page in pages:
        match = pattern.search(page.text)
        if match:
            return match.group(0).strip(), page
    return None


def _named_value(label: str, pages: list[ExtractedPage]) -> tuple[str, ExtractedPage] | None:
    pattern = re.compile(rf"{re.escape(label)}\s*[：:]\s*([\u4e00-\u9fff·]{{2,20}})")
    for page in pages:
        match = pattern.search(page.text)
        if match:
            return match.group(1).strip(), page
    return None


def _source(document_id: str, page: ExtractedPage, value: str) -> dict[str, Any]:
    position = page.text.find(value)
    start = max(0, position - 24)
    end = min(len(page.text), position + len(value) + 48)
    return {
        "document_id": document_id,
        "page": page.page,
        "snippet": page.text[start:end].replace("\n", " ").strip(),
        "extraction_method": page.method,
        "confidence": 0.92 if page.method == "text" else 0.72,
    }


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
        ("applicant_name", _named_value("申请执行人", pages) or _named_value("申请人", pages)),
        ("respondent_name", _named_value("被执行人", pages) or _named_value("被申请人", pages)),
    ]
    for field, candidate in mappings:
        if candidate:
            value, page = candidate
            facts[field] = value
            sources[field] = [_source(document_id, page, value)]

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
    )
