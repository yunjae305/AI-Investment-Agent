from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ai_invest_agent.analysis import build_portfolio_guidance, build_strategy_summary
from ai_invest_agent.models import InvestmentRequest, Recommendation, SecuritySnapshot


UNKNOWN_TEXT = "Data unavailable"


def build_report_context(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: Iterable[SecuritySnapshot],
    data_source: str = "mock",
    provider_warning: str | None = None,
) -> dict:
    snapshot_map = {item.symbol: item for item in snapshots}
    rows = []
    signal_payloads = []

    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        rows.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "current_price": format_price(item.current_price, snapshot.currency),
                "rationale": item.rationale,
                "metrics": (
                    f"RSI {format_num(snapshot.technicals.rsi)} / "
                    f"PER {format_num(snapshot.fundamentals.per)}"
                ),
                "risk_level": item.risk_level,
                "entry_price": format_price(item.entry_price, snapshot.currency),
                "target_price": format_price(item.target_price, snapshot.currency),
                "stop_loss_price": format_price(item.stop_loss_price, snapshot.currency),
                "expected_return_pct": format_pct(item.expected_return_pct),
                "financial_metrics": {
                    "eps": format_metric(snapshot.fundamentals.eps, snapshot.currency),
                    "per": format_num(snapshot.fundamentals.per),
                    "roe": format_pct_value(snapshot.fundamentals.roe),
                    "bps": format_metric(snapshot.fundamentals.bps, snapshot.currency),
                    "pbr": format_num(snapshot.fundamentals.pbr),
                },
                "financial_metrics_raw": {
                    "eps": snapshot.fundamentals.eps,
                    "per": snapshot.fundamentals.per,
                    "roe": snapshot.fundamentals.roe,
                    "bps": snapshot.fundamentals.bps,
                    "pbr": snapshot.fundamentals.pbr,
                },
            }
        )

        payload = {
            "action": item.signal_action,
            "symbol": item.symbol,
            "quantity": item.quantity,
            "entry_price": item.entry_price,
            "target_price": item.target_price,
            "stop_loss_price": item.stop_loss_price,
            "reason": item.reason,
        }
        signal_payloads.append(
            {
                "symbol": item.symbol,
                "action": item.signal_action,
                "pretty_json": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        )

    metric_charts = _build_metric_charts(rows)
    context = {
        "request": {
            "asset_krw": request.asset_krw,
            "asset_label": f"{request.asset_krw:,} KRW",
            "propensity": request.propensity,
            "market": request.market,
            "duration": request.duration,
            "data_source": data_source,
        },
        "summary": build_strategy_summary(request, recommendations),
        "guidance": build_portfolio_guidance(request),
        "rows": rows,
        "signals": signal_payloads,
        "metric_charts": metric_charts,
        "provider_warning": provider_warning,
        "data_source_label": _source_label(data_source),
        "generated_from": _guess_generated_from(list(snapshots)),
        "disclaimer": "이 결과는 모의 데이터 기반 참고용입니다. 최종 투자 책임은 사용자에게 있습니다.",
    }
    context["markdown_report"] = render_markdown_report(context)
    context["html_report"] = render_html_report(context)
    return context


def render_markdown_report(context: dict) -> str:
    lines: list[str] = []
    lines.append("# 모의 투자 분석 보고서")
    lines.append("")
    lines.append(f"- 자산: {context['request']['asset_label']}")
    lines.append(f"- 성향: {context['request']['propensity']}")
    lines.append(f"- 시장: {context['request']['market']}")
    lines.append(f"- 기간: {context['request']['duration']}")
    lines.append(f"- 데이터: {context['data_source_label']}")
    lines.append("")
    lines.append("## 요약")
    lines.append(context["summary"])
    lines.append("")
    lines.append("## 추천 종목")
    for row in context["rows"]:
        lines.append(
            f"- {row['name']}({row['symbol']}): 진입 {row['entry_price']}, 목표 {row['target_price']}, "
            f"손절 {row['stop_loss_price']}, 기대수익률 {row['expected_return_pct']}"
        )
    lines.append("")
    lines.append("## 자동 실행 Payload")
    for signal in context["signals"]:
        lines.append("```json")
        lines.append(signal["pretty_json"])
        lines.append("```")
    lines.append("")
    lines.append(context["disclaimer"])
    return "\n".join(lines)


def render_html_report(context: dict) -> str:
    rows_html = "".join(_render_row_html(row) for row in context["rows"])
    return f"""<!doctype html>
<html lang='ko'>
  <head>
    <meta charset='utf-8'>
    <title>모의 투자 분석 보고서</title>
    <style>
      body {{ font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; margin: 24px; color: #111827; }}
      h1 {{ font-size: 24px; }}
      h2 {{ font-size: 18px; margin-top: 24px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
      .muted {{ color: #6b7280; }}
      .svg-wrap svg {{ width: 100%; height: auto; }}
    </style>
  </head>
  <body>
    <h1>모의 투자 분석 보고서</h1>
    <p>자산: {context['request']['asset_label']} / 성향: {context['request']['propensity']} / 시장: {context['request']['market']} / 기간: {context['request']['duration']}</p>

    <h2>요약</h2>
    <p>{context['summary']}</p>

    <h2>추천 종목</h2>
    <table>
      <thead>
        <tr><th>종목</th><th>현재가</th><th>추천 이유</th><th>진입/목표/손절</th><th>핵심 지표</th></tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>

    <h2>지표 그래프</h2>
    {''.join(chart['svg'] for chart in context['metric_charts'])}

    <h2>면책</h2>
    <p>{context['disclaimer']}</p>
  </body>
</html>"""


def attach_artifacts(context: dict, pdf_path: Path | None = None, execution_result: dict | None = None) -> dict:
    if pdf_path is not None:
        context["pdf_report"] = {
            "file_path": str(pdf_path),
            "file_name": pdf_path.name,
        }
    if execution_result is not None:
        context["execution_result"] = execution_result
    return context


def format_num(value: float | None) -> str:
    if value is None:
        return UNKNOWN_TEXT
    return f"{value:.1f}"


def format_metric(value: float | None, currency: str) -> str:
    if value is None:
        return UNKNOWN_TEXT
    if currency == "KRW":
        return f"{value:,.0f} KRW"
    return f"{currency} {value:,.2f}"


def format_pct_value(value: float | None) -> str:
    if value is None:
        return UNKNOWN_TEXT
    return f"{value:.2f}%"


def format_pct(value: float | None) -> str:
    if value is None:
        return UNKNOWN_TEXT
    return f"{value:.2f}%"


def format_price(value: float | None, currency: str) -> str:
    if value is None:
        return UNKNOWN_TEXT
    if currency == "KRW":
        return f"{int(round(value)):,} KRW"
    return f"{currency} {value:,.2f}"


def _guess_generated_from(snapshots: list[SecuritySnapshot]) -> str:
    for snapshot in snapshots:
        if snapshot.captured_at is not None:
            return snapshot.captured_at.isoformat(sep=" ")
    return UNKNOWN_TEXT


def _source_label(data_source: str) -> str:
    return {"mock": "Mock Data"}.get(data_source, data_source)


def _build_metric_charts(rows: list[dict]) -> list[dict]:
    charts = []
    for metric_key, title in (
        ("eps", "EPS 비교"),
        ("per", "PER 비교"),
        ("roe", "ROE 비교"),
        ("bps", "BPS 비교"),
        ("pbr", "PBR 비교"),
    ):
        values = [{"label": row["symbol"], "value": row["financial_metrics_raw"].get(metric_key)} for row in rows]
        charts.append({"title": title, "svg": _build_bar_chart_svg(title, values)})
    return charts


def _build_bar_chart_svg(title: str, values: list[dict]) -> str:
    width = 680
    height = 240
    left = 52
    bottom = 32
    top = 20
    right = 20
    plot_width = width - left - right
    plot_height = height - top - bottom

    numeric_values = [float(item["value"]) for item in values if item["value"] is not None]
    max_value = max(numeric_values) if numeric_values else 1.0
    bar_width = max(24, int(plot_width / max(len(values), 1) * 0.55))
    gap = int((plot_width - bar_width * len(values)) / max(len(values), 1))
    gap = max(gap, 10)

    axis = [
        f"<line x1='{left}' y1='{height - bottom}' x2='{width - right}' y2='{height - bottom}' stroke='#94a3b8' stroke-width='1' />",
        f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height - bottom}' stroke='#94a3b8' stroke-width='1' />",
    ]
    bars = []
    for idx, item in enumerate(values):
        raw = item["value"] or 0
        bar_height = 0 if max_value == 0 else (float(raw) / max_value) * plot_height
        x = left + gap + idx * (bar_width + gap)
        y = height - bottom - bar_height
        bars.append(
            f"<rect x='{x}' y='{y:.1f}' width='{bar_width}' height='{bar_height:.1f}' fill='#1d4ed8' rx='4' />"
            f"<text x='{x + bar_width / 2:.1f}' y='{height - 12}' font-size='10' text-anchor='middle' fill='#334155'>{item['label']}</text>"
            f"<text x='{x + bar_width / 2:.1f}' y='{max(y - 6, 12):.1f}' font-size='10' text-anchor='middle' fill='#0f172a'>{raw if item['value'] is not None else 'N/A'}</text>"
        )

    return (
        f"<div class='svg-wrap'><svg viewBox='0 0 {width} {height}' role='img' aria-label='{title}'>"
        f"<text x='{left}' y='14' font-size='12' fill='#0f172a'>{title}</text>"
        f"{''.join(axis)}{''.join(bars)}</svg></div>"
    )


def _render_row_html(row: dict) -> str:
    metrics = row["financial_metrics"]
    return (
        "<tr>"
        f"<td><strong>{row['name']}</strong><br><span class='muted'>{row['symbol']}</span></td>"
        f"<td>{row['current_price']}</td>"
        f"<td>{row['rationale']}</td>"
        f"<td>진입 {row['entry_price']}<br>목표 {row['target_price']}<br>손절 {row['stop_loss_price']}</td>"
        f"<td>EPS {metrics['eps']}<br>PER {metrics['per']}<br>ROE {metrics['roe']}<br>BPS {metrics['bps']}<br>PBR {metrics['pbr']}</td>"
        "</tr>"
    )
