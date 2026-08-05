from __future__ import annotations

import io

from docx import Document as WordDocument
from PIL import Image, ImageDraw


def legal_basis_docx() -> bytes:
    """生成完全虚构的判决书测试件，避免仓库保存任何案件或身份材料。"""

    document = WordDocument()
    document.add_paragraph("北京市朝阳区人民法院")
    document.add_paragraph("民事判决书")
    document.add_paragraph("（2026）京0105民初123号")
    document.add_paragraph("申请执行人：测试甲")
    document.add_paragraph("被执行人：测试乙")
    document.add_paragraph("被执行人应支付人民币 10000.00 元。")
    document.add_paragraph("二〇二六年八月六日")
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def synthetic_identity_png(side: str) -> bytes:
    """只画测试占位符，不构造可误用的真实身份证样式或号码。"""

    image = Image.new("RGB", (640, 400), "#edf4f1")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 624, 384), outline="#426b61", width=4)
    draw.text((40, 44), f"SYNTHETIC TEST ID - {side}", fill="#173f36")
    draw.text((40, 100), "NOT A REAL IDENTITY DOCUMENT", fill="#b73a33")
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()
