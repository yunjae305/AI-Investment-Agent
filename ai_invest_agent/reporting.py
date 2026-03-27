from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ai_invest_agent.analysis import build_portfolio_guidance, build_strategy_summary
from ai_invest_agent.multi_agent import build_rule_based_multi_agent_analysis, run_multi_agent_analysis
from ai_invest_agent.models import InvestmentRequest, Recommendation, SecuritySnapshot


UNKNOWN_TEXT = "Data unavailable"


def build_report_context(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: Iterable[SecuritySnapshot],
    data_source: str = "mock",
    provider_warning: str | None = None,
) -> dict:
    snapshot_list = list(snapshots)
    snapshot_map = {item.symbol: item for item in snapshot_list}
    try:
        multi_agent = run_multi_agent_analysis(request, recommendations, snapshot_list)
    except Exception as exc:
        fallback_message = f"Multi-agent pipeline fallback applied: {exc}"
        provider_warning = f"{provider_warning} / {fallback_message}" if provider_warning else fallback_message
        multi_agent = build_rule_based_multi_agent_analysis(request, recommendations, snapshot_list[:])
    rows = []
    signal_payloads = []
    risk_cards = []

    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        financial_metrics = {
            "eps": snapshot.fundamentals.eps,
            "per": snapshot.fundamentals.per,
            "roe": snapshot.fundamentals.roe,
            "bps": snapshot.fundamentals.bps,
            "pbr": snapshot.fundamentals.pbr,
        }
        rows.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "current_price": format_price(item.current_price, snapshot.currency),
                "rationale": item.rationale,
                "metrics": (
                    f"RSI(과열/침체 참고 지표) {format_num(snapshot.technicals.rsi)} / "
                    f"PER(주가가 이익 대비 얼마나 비싼지) {format_num(snapshot.fundamentals.per)}"
                ),
                "risk_level": item.risk_level,
                "entry_price": format_price(item.entry_price, snapshot.currency),
                "target_price": format_price(item.target_price, snapshot.currency),
                "stop_loss_price": format_price(item.stop_loss_price, snapshot.currency),
                "expected_return_pct": format_pct(item.expected_return_pct),
                "captured_at": snapshot.captured_at.isoformat(sep=" ") if snapshot.captured_at else UNKNOWN_TEXT,
                "data_note": item.data_note,
                "financial_metrics": {
                    "eps": format_metric(financial_metrics["eps"], snapshot.currency),
                    "per": format_num(financial_metrics["per"]),
                    "roe": format_pct_value(financial_metrics["roe"]),
                    "bps": format_metric(financial_metrics["bps"], snapshot.currency),
                    "pbr": format_num(financial_metrics["pbr"]),
                },
                "financial_metrics_raw": financial_metrics,
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
        risk_cards.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "warnings": item.warnings,
                "data_note": item.data_note,
            }
        )

    company_analysis = [
        _build_company_analysis(snapshot_map[item.symbol], item)
        for item in recommendations
    ]
    market_analysis = _build_market_analysis(request, snapshot_list)
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
        "persona": {
            "summary": multi_agent.persona.summary,
            "risk_tolerance": multi_agent.persona.risk_tolerance,
            "sector_interests": multi_agent.persona.sector_interests,
            "decision_values": multi_agent.persona.decision_values,
            "source": multi_agent.persona.source,
        },
        "multi_agent": {
            "topics": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "rationale": item.rationale,
                    "source": item.source,
                }
                for item in multi_agent.topics
            ],
            "plan": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "focus_priority": item.focus_priority,
                    "keywords": item.keywords,
                    "source": item.source,
                }
                for item in multi_agent.plan
            ],
            "research": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "facts": item.facts,
                    "negative_news_flags": item.negative_news_flags,
                    "source": item.source,
                }
                for item in multi_agent.research
            ],
            "insights": [
                {
                    "symbol": item.symbol,
                    "name": item.name,
                    "thesis": item.thesis,
                    "scenario": item.scenario,
                    "key_risks": item.key_risks,
                    "source": item.source,
                }
                for item in multi_agent.insights
            ],
            "verification": {
                "passed": multi_agent.verification.passed,
                "issues": multi_agent.verification.issues,
                "corrections": multi_agent.verification.corrections,
                "source": multi_agent.verification.source,
            },
            "markdown_report": multi_agent.markdown_report,
            "models": multi_agent.model_map,
        },
        "company_analysis": company_analysis,
        "market_analysis": market_analysis,
        "metric_charts": metric_charts,
        "rows": rows,
        "risk_cards": risk_cards,
        "signals": signal_payloads,
        "disclaimer": "This report is reference material only. Final investment responsibility remains with the user.",
        "uses_mock_data": data_source == "mock",
        "data_source_label": _source_label(data_source),
        "provider_warning": provider_warning,
        "generated_from": _guess_generated_from(snapshot_list),
    }
    context["markdown_report"] = render_markdown_report(
        request=request,
        recommendations=recommendations,
        snapshots=snapshot_list,
        data_source=data_source,
        provider_warning=provider_warning,
        context=context,
    )
    context["html_report"] = render_html_report(context)
    return context


def render_markdown_report(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: Iterable[SecuritySnapshot],
    data_source: str = "mock",
    provider_warning: str | None = None,
    context: dict | None = None,
) -> str:
    if context is None:
        context = build_report_context(request, recommendations, snapshots, data_source, provider_warning)

    top_rows = context["rows"][:3]
    lines: list[str] = []
    lines.append("# Final Conclusion")
    lines.append("")
    lines.append(_plain_summary(context["summary"]))
    lines.append("")
    lines.append("## What To Do First")
    lines.append("")
    for row in top_rows:
        lines.append(
            f"- {row['name']} ({row['symbol']}): "
            f"살펴볼 가격 {row['entry_price']}, "
            f"목표 가격 {row['target_price']}, "
            f"위험 관리 가격 {row['stop_loss_price']}, "
            f"예상 수익률 {row['expected_return_pct']}"
        )
    lines.append("")
    lines.append("## Before You Read")
    lines.append("")
    lines.append(f"- 투자금: {context['request']['asset_label']}")
    lines.append(f"- 시장: {context['request']['market']}")
    lines.append(f"- 투자 기간: {context['request']['duration']}")
    lines.append(f"- 투자 성향: {context['request']['propensity']}")
    lines.append(f"- 데이터 출처: {context['data_source_label']}")
    lines.append(f"- 기준 시점: {context['generated_from']}")
    if context["provider_warning"]:
        lines.append(f"- 참고: {context['provider_warning']}")
    lines.append("")
    lines.append("# Why This Conclusion")
    lines.append("")
    lines.append("## Investor Persona")
    lines.append("")
    lines.append(context["persona"]["summary"])
    lines.append("")
    lines.append(f"- 감당 가능한 위험 수준: {context['persona']['risk_tolerance']}")
    lines.append(f"- 관심을 가질 가능성이 높은 분야: {', '.join(context['persona']['sector_interests'])}")
    lines.append(f"- 투자할 때 중요하게 볼 것: {', '.join(context['persona']['decision_values'])}")
    lines.append("")
    lines.append("## Easy Guide")
    lines.append("")
    for item in context["guidance"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Why These Stocks")
    lines.append("")
    for item in context["multi_agent"]["topics"]:
        lines.append(f"- {item['name']} ({item['symbol']}): {item['rationale']}")
    lines.append("")
    lines.append("## What Was Checked")
    lines.append("")
    for item in context["multi_agent"]["plan"]:
        lines.append(
            f"- {item['name']} ({item['symbol']}): "
            f"중점 확인 항목 {item['focus_priority']} / 확인 키워드 {', '.join(item['keywords'])}"
        )
    lines.append("")
    lines.append("## Facts Found")
    lines.append("")
    for item in context["multi_agent"]["research"]:
        lines.append(f"## {item['name']} ({item['symbol']})")
        for fact in item["facts"]:
            lines.append(f"- {fact}")
        if item["negative_news_flags"]:
            lines.append(f"- 주의할 이슈: {', '.join(item['negative_news_flags'])}")
        lines.append("")
    lines.append("## Easy Interpretation")
    lines.append("")
    for item in context["multi_agent"]["insights"]:
        lines.append(f"## {item['name']} ({item['symbol']})")
        lines.append(f"- 한 줄 해석: {item['thesis']}")
        lines.append(f"- 이렇게 대응하면 됩니다: {item['scenario']}")
        lines.append(f"- 꼭 주의할 점: {', '.join(item['key_risks'])}")
        lines.append("")
    lines.append("## Stock Details")
    lines.append("")
    for row in context["rows"]:
        lines.append(f"## {row['name']} ({row['symbol']})")
        lines.append(f"- 현재 가격: {row['current_price']}")
        lines.append(f"- 추천 이유: {row['rationale']}")
        lines.append(f"- 참고 지표: {row['metrics']}")
        lines.append(f"- 위험 수준: {row['risk_level']}")
        lines.append(f"- 살펴볼 가격: {row['entry_price']}")
        lines.append(f"- 목표 가격: {row['target_price']}")
        lines.append(f"- 위험 관리 가격: {row['stop_loss_price']}")
        lines.append(f"- 예상 수익률: {row['expected_return_pct']}")
        lines.append(
            "- 재무 지표 쉽게 보기: "
            f"EPS(주당순이익) {row['financial_metrics']['eps']} / "
            f"PER(이익 대비 주가 수준) {row['financial_metrics']['per']} / "
            f"ROE(자기자본으로 얼마나 잘 벌었는지) {row['financial_metrics']['roe']} / "
            f"BPS(주당 순자산가치) {row['financial_metrics']['bps']} / "
            f"PBR(순자산 대비 주가 수준) {row['financial_metrics']['pbr']}"
        )
        lines.append("")
    lines.append("## Company Analysis")
    lines.append("")
    for section in context["company_analysis"]:
        lines.append(f"## {section['name']} ({section['symbol']})")
        lines.append(f"- 재무제표를 쉽게 보면: {section['financial_statements']}")
        lines.append(f"- 경영진을 볼 때는: {section['management_assessment']}")
        lines.append(f"- 비슷한 기업과 비교하면: {section['competitor_comparison']}")
        lines.append("")
    lines.append("## Market Trends")
    lines.append("")
    lines.append(f"- 시장 전체 분위기: {context['market_analysis']['macro_economy']}")
    lines.append(f"- 업종 흐름: {context['market_analysis']['industry_trends']}")
    lines.append("")
    lines.append("## Risk Notes")
    lines.append("")
    for card in context["risk_cards"]:
        lines.append(f"## {card['name']} ({card['symbol']})")
        for warning in card["warnings"]:
            lines.append(f"- {warning}")
        lines.append(f"- 참고 데이터 메모: {card['data_note']}")
        lines.append("")
    lines.append("## Execution Payloads")
    lines.append("")
    for signal in context["signals"]:
        lines.append("```json")
        lines.append(signal["pretty_json"])
        lines.append("```")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- 검증 통과 여부: {context['multi_agent']['verification']['passed']}")
    for issue in context["multi_agent"]["verification"]["issues"]:
        lines.append(f"- 확인된 문제: {issue}")
    for correction in context["multi_agent"]["verification"]["corrections"]:
        lines.append(f"- 수정 또는 보완 의견: {correction}")
    lines.append("")
    lines.append("## Multi-Agent Draft")
    lines.append("")
    lines.append(context["multi_agent"]["markdown_report"] if "markdown_report" in context["multi_agent"] else "")
    lines.append("")
    lines.append(context["disclaimer"])
    return "\n".join(lines)


def render_html_report(context: dict) -> str:
    rows_html = "".join(_render_row_html(row) for row in context["rows"])
    top_action_html = "".join(
        (
            f"<li><strong>{row['name']} ({row['symbol']})</strong>: "
            f"Entry {row['entry_price']} / Target {row['target_price']} / "
            f"Stop {row['stop_loss_price']} / Expected {row['expected_return_pct']}</li>"
        )
        for row in context["rows"][:3]
    )
    company_html = "".join(
        (
            f"<section class='card'><h3>{item['name']} ({item['symbol']})</h3>"
            f"<p><strong>재무제표 분석:</strong> {item['financial_statements']}</p>"
            f"<p><strong>경영진 평가:</strong> {item['management_assessment']}</p>"
            f"<p><strong>경쟁사 비교:</strong> {item['competitor_comparison']}</p></section>"
        )
        for item in context["company_analysis"]
    )
    chart_html = "".join(
        f"<section class='card'><h3>{chart['title']}</h3>{chart['svg']}</section>"
        for chart in context["metric_charts"]
    )
    verification = context["multi_agent"]["verification"]
    issue_html = "".join(f"<li>{item}</li>" for item in verification["issues"])
    correction_html = "".join(f"<li>{item}</li>" for item in verification["corrections"])
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <title>Investment Report</title>
    <style>
      body {{
        font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
        color: #111827;
        margin: 28px;
        line-height: 1.5;
        font-size: 12px;
      }}
      h1, h2, h3 {{ margin: 0 0 10px; }}
      h1 {{ font-size: 24px; }}
      h2 {{ font-size: 18px; margin-top: 26px; padding-bottom: 6px; border-bottom: 1px solid #d1d5db; }}
      h3 {{ font-size: 14px; }}
      .meta span {{ display: inline-block; margin-right: 12px; color: #4b5563; }}
      .card {{
        border: 1px solid #dbe4ee;
        border-radius: 10px;
        padding: 14px;
        margin: 12px 0;
        page-break-inside: avoid;
      }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
      th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }}
      ul {{ margin: 6px 0 0 18px; }}
      .muted {{ color: #6b7280; }}
      .grid {{ display: block; }}
      .summary-box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px;
      }}
      .svg-wrap svg {{ width: 100%; height: auto; }}
    </style>
  </head>
  <body>
    <h1>Investment Strategy Report</h1>
    <div class="meta">
      <span>Asset: {context['request']['asset_label']}</span>
      <span>Market: {context['request']['market']}</span>
      <span>Duration: {context['request']['duration']}</span>
      <span>Risk: {context['request']['propensity']}</span>
    </div>

    <h2>Final Conclusion</h2>
    <div class="summary-box">
      <p>{_plain_summary(context['summary'])}</p>
      <p><strong>핵심 결론:</strong> 처음 투자하는 사람이라면 아래 가격대를 기준으로 차분히 보는 것이 좋습니다.</p>
      <ul>{top_action_html}</ul>
    </div>

    <h2>Why This Conclusion</h2>
    <section class="card">
      <p><strong>투자자 성향 요약:</strong> {context['persona']['summary']}</p>
      <p><strong>시장 전체 분위기:</strong> {context['market_analysis']['macro_economy']}</p>
      <p><strong>업종 흐름:</strong> {context['market_analysis']['industry_trends']}</p>
    </section>

    <h2>Recommended Stocks</h2>
    <section class="card">
      <p><strong>선정 이유:</strong> 투자자 성향, 시장 상황, 가격 흐름, 재무 상태를 함께 반영했습니다.</p>
      <p><strong>용어 안내:</strong> entry는 살펴볼 가격, target은 목표 가격, stop은 손실을 줄이기 위해 다시 점검할 가격입니다.</p>
    </section>
    <table>
      <thead>
        <tr>
          <th>종목</th>
          <th>현재가</th>
          <th>추천 사유</th>
          <th>진입/목표/손절</th>
          <th>핵심 재무지표</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>

    <h2>Financial Metric Charts</h2>
    <div class="grid">{chart_html}</div>

    <h2>Company Analysis</h2>
    {company_html}

    <h2>Verification</h2>
    <section class="card">
      <p><strong>검증 통과 여부:</strong> {verification['passed']}</p>
      <p><strong>확인된 문제:</strong></p>
      <ul>{issue_html}</ul>
      <p><strong>수정 또는 보완 의견:</strong></p>
      <ul>{correction_html}</ul>
    </section>

    <h2>Trade Guide</h2>
    <section class="card">
      <p>{context['multi_agent']['markdown_report'].replace(chr(10), '<br>')}</p>
    </section>
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
    return {
        "hybrid": "Hybrid Research",
        "kis": "KIS Open API",
        "yfinance": "Yahoo Finance",
        "defeatbeta": "DefeatBeta Research",
        "mock": "Mock Data",
    }.get(data_source, data_source)


def _build_company_analysis(snapshot: SecuritySnapshot, recommendation: Recommendation) -> dict:
    finance_text = (
        f"회사가 주식 1주당 얼마나 벌고 있는지는 EPS {format_metric(snapshot.fundamentals.eps, snapshot.currency)}로 봤습니다. "
        f"회사가 자기 자본을 얼마나 효율적으로 쓰는지는 ROE {format_pct_value(snapshot.fundamentals.roe)}로 확인했습니다. "
        f"회사가 가진 순자산 가치는 BPS {format_metric(snapshot.fundamentals.bps, snapshot.currency)}를 참고했고, "
        f"현재 주가가 이익과 자산에 비해 비싼지 싼지는 PER {format_num(snapshot.fundamentals.per)}, "
        f"PBR {format_num(snapshot.fundamentals.pbr)}로 쉽게 판단했습니다."
    )
    management_text = (
        f"경영진에 대한 자세한 공개 정보가 제한적이어서, 이번 리포트에서는 숫자와 최근 투자 포인트를 중심으로 봤습니다. "
        f"현재 핵심 포인트는 '{recommendation.rationale}'이며, 안정적으로 사업을 운영하고 있는지 계속 체크하는 것이 중요합니다."
    )
    comparison_text = (
        f"비슷한 후보 종목과 비교했을 때 현재 위험 수준은 {recommendation.risk_level}입니다. "
        f"예상 수익률은 {format_pct(recommendation.expected_return_pct)} 수준으로 계산되며, "
        f"이 값이 다른 후보보다 더 낫거나 비슷한지를 보고 경쟁력을 판단했습니다."
    )
    return {
        "symbol": snapshot.symbol,
        "name": snapshot.name,
        "financial_statements": finance_text,
        "management_assessment": management_text,
        "competitor_comparison": comparison_text,
    }


def _build_market_analysis(request: InvestmentRequest, snapshots: list[SecuritySnapshot]) -> dict:
    avg_volatility = [
        item.risk.volatility_30d for item in snapshots if item.risk.volatility_30d is not None
    ]
    volatility = sum(avg_volatility) / len(avg_volatility) if avg_volatility else None
    macro = (
        f"{request.market} 시장은 최근 평균 30일 변동성이 {format_num(volatility)} 수준입니다. "
        f"쉽게 말해, 가격이 얼마나 크게 흔들리는지 보는 수치입니다. "
        f"{request.duration} 투자 기준에서는 금리, 환율, 시장 자금 흐름 변화가 주가에 영향을 줄 수 있습니다."
    )
    sectors = []
    for item in snapshots:
        for note in item.notes:
            if "Sector:" in note:
                sectors.append(note.split("Sector:", 1)[1].strip())
    sector_text = ", ".join(sorted(set(sectors))) if sectors else "반도체, 플랫폼, 대형 기술주 중심"
    industry = (
        f"지금은 {sector_text} 관련 흐름이 핵심입니다. "
        f"사용자 성향인 {request.propensity}와 투자 기간 {request.duration}를 고려하면, "
        f"실적이 좋아지는지와 주가가 이미 너무 많이 오른 것은 아닌지를 함께 봐야 합니다."
    )
    return {"macro_economy": macro, "industry_trends": industry}


def _build_metric_charts(rows: list[dict]) -> list[dict]:
    charts = []
    for metric_key, title in (
        ("eps", "EPS Comparison (1주당 이익)"),
        ("per", "PER Comparison (이익 대비 주가 수준)"),
        ("roe", "ROE Comparison (자본 활용 효율)"),
        ("bps", "BPS Comparison (1주당 순자산)"),
        ("pbr", "PBR Comparison (자산 대비 주가 수준)"),
    ):
        values = [
            {
                "label": row["symbol"],
                "value": row["financial_metrics_raw"].get(metric_key),
            }
            for row in rows
        ]
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
    bars = []
    axis = [
        f"<line x1='{left}' y1='{height - bottom}' x2='{width - right}' y2='{height - bottom}' stroke='#94a3b8' stroke-width='1' />",
        f"<line x1='{left}' y1='{top}' x2='{left}' y2='{height - bottom}' stroke='#94a3b8' stroke-width='1' />",
    ]
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
        f"<td>살펴볼 가격 {row['entry_price']}<br>목표 가격 {row['target_price']}<br>위험 관리 가격 {row['stop_loss_price']}</td>"
        f"<td>EPS(주당순이익) {metrics['eps']}<br>PER(이익 대비 주가 수준) {metrics['per']}<br>ROE(자본 활용 효율) {metrics['roe']}<br>BPS(주당 순자산) {metrics['bps']}<br>PBR(자산 대비 주가 수준) {metrics['pbr']}</td>"
        "</tr>"
    )


def _plain_summary(summary: str) -> str:
    return (
        summary.replace("현재 제안 비중은", "현재는")
        .replace("우선 검토 종목은", "먼저 볼 종목은")
        .replace("입니다.", "입니다.")
    )
