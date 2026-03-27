from __future__ import annotations

import html
import os
from pathlib import Path

import requests

from ai_invest_agent.pdf_export import export_report_pdf


class PdfExportError(RuntimeError):
    pass


def export_report(
    report_text: str,
    output_path: Path,
    title: str = "Investment Report",
) -> tuple[Path, str]:
    provider = os.getenv("PDF_EXPORT_PROVIDER", "local").strip().lower()
    if provider == "cloudmersive":
        try:
            export_with_cloudmersive(report_text, output_path, title=title)
            return output_path, "cloudmersive"
        except Exception:
            pass
    export_report_pdf(report_text, output_path, title=title)
    return output_path, "local"


def export_with_cloudmersive(report_text: str, output_path: Path, title: str = "Investment Report") -> Path:
    api_key = os.getenv("CLOUDMERSIVE_API_KEY", "").strip()
    if not api_key:
        raise PdfExportError("CLOUDMERSIVE_API_KEY is not configured")

    html_payload = _build_html_document(report_text, title=title)
    response = requests.post(
        "https://api.cloudmersive.com/convert/html/to/pdf",
        headers={
            "Apikey": api_key,
            "Content-Type": "text/html",
        },
        data=html_payload.encode("utf-8"),
        timeout=30,
    )
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def _build_html_document(report_text: str, title: str) -> str:
    escaped_title = html.escape(title)
    escaped_text = html.escape(report_text)
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <title>{escaped_title}</title>
    <style>
      body {{
        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
        line-height: 1.6;
        color: #111827;
        margin: 40px;
      }}
      h1 {{
        font-size: 24px;
        margin: 0 0 20px;
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        font-family: 'Malgun Gothic', 'Consolas', monospace;
        font-size: 12px;
      }}
    </style>
  </head>
  <body>
    <h1>{escaped_title}</h1>
    <pre>{escaped_text}</pre>
  </body>
</html>
"""
