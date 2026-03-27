from __future__ import annotations

from pathlib import Path
from typing import Iterable


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
TOP_MARGIN = 54
BOTTOM_MARGIN = 54
FONT_SIZE = 10
LEADING = 14
MAX_COLUMNS = 54
LINES_PER_PAGE = int((PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN) / LEADING)


def export_report_pdf(report_text: str, output_path: Path, title: str = "Investment Report") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages = _paginate(_normalize_text(report_text).splitlines())
    output_path.write_bytes(_build_pdf_bytes(title=title, pages=pages))
    return output_path


def _normalize_text(text: str) -> str:
    normalized_lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw_line:
            normalized_lines.append("")
            continue
        chunks = [raw_line[idx: idx + MAX_COLUMNS] for idx in range(0, len(raw_line), MAX_COLUMNS)]
        normalized_lines.extend(chunks)
    return "\n".join(normalized_lines)


def _paginate(lines: Iterable[str]) -> list[list[str]]:
    pages: list[list[str]] = []
    page: list[str] = []
    for line in lines:
        page.append(line)
        if len(page) >= LINES_PER_PAGE:
            pages.append(page)
            page = []
    if page or not pages:
        pages.append(page)
    return pages


def _build_pdf_bytes(title: str, pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add_object(payload: str | bytes) -> int:
        data = payload.encode("latin-1", errors="replace") if isinstance(payload, str) else payload
        objects.append(data)
        return len(objects)

    cid_font_id = add_object(
        "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYSMyeongJo-Medium "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) /Supplement 1 >> >>"
    )
    font_id = add_object(
        f"<< /Type /Font /Subtype /Type0 /BaseFont /HYSMyeongJo-Medium "
        f"/Encoding /UniKS-UCS2-H /DescendantFonts [{cid_font_id} 0 R] >>"
    )
    pages_placeholder = add_object("")
    page_ids: list[int] = []

    for lines in pages:
        content_stream = _build_page_stream(lines)
        content_id = add_object(
            f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
            + content_stream
            + b"\nendstream"
        )
        page_ids.append(
            add_object(
                f"<< /Type /Page /Parent {pages_placeholder} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            )
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_placeholder - 1] = (
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("latin-1")
    )
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_placeholder} 0 R >>")
    info_id = add_object(f"<< /Title ({_escape_ascii_text(title)}) /Producer (Codex) >>")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("latin-1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    return bytes(output)


def _build_page_stream(lines: list[str]) -> bytes:
    commands = ["BT", f"/F1 {FONT_SIZE} Tf", f"1 0 0 1 {LEFT_MARGIN} {PAGE_HEIGHT - TOP_MARGIN} Tm"]
    for idx, line in enumerate(lines):
        encoded = _encode_pdf_hex_text(line)
        if idx == 0:
            commands.append(f"<{encoded}> Tj")
        else:
            commands.append(f"0 -{LEADING} Td <{encoded}> Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _encode_pdf_hex_text(value: str) -> str:
    if not value:
        return ""
    encoded = value.encode("utf-16-be")
    return encoded.hex().upper()


def _escape_ascii_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )
