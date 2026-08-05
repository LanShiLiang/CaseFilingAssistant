from __future__ import annotations

import io
import sys
from pathlib import Path

from docx import Document as WordDocument
from PIL import Image, ImageDraw


def write_legal_basis(target: Path) -> None:
    document = WordDocument()
    document.add_paragraph("北京市朝阳区人民法院")
    document.add_paragraph("民事判决书")
    document.add_paragraph("（2026）京0105民初123号")
    document.add_paragraph("申请执行人：测试甲")
    document.add_paragraph("被执行人：测试乙")
    document.add_paragraph("被执行人应支付人民币 10000.00 元。")
    document.add_paragraph("2026年8月6日")
    document.save(target)


def write_identity(target: Path, side: str) -> None:
    image = Image.new("RGB", (640, 400), "#edf4f1")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 624, 384), outline="#426b61", width=4)
    draw.text((40, 44), f"SYNTHETIC TEST ID - {side}", fill="#173f36")
    draw.text((40, 100), "NOT A REAL IDENTITY DOCUMENT", fill="#b73a33")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    target.write_bytes(stream.getvalue())


def main() -> None:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_legal_basis(output / "synthetic-legal-basis.docx")
    write_identity(output / "synthetic-id-front.png", "FRONT")
    write_identity(output / "synthetic-id-back.png", "BACK")


if __name__ == "__main__":
    main()
