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
    snapshot_list = list(snapshots)
    snapshot_map = {item.symbol: item for item in snapshot_list}
    rows = []
    signal_payloads = []
    risk_cards = []

    for item in recommendations:
        snapshot = snapshot_map[item.symbol]
        rows.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "current_price": format_price(item.current_price, snapshot.currency),
                "rationale": item.rationale,
                "metrics": f"RSI {format_num(snapshot.technicals.rsi)} / PER {format_num(snapshot.fundamentals.per)}",
                "risk_level": item.risk_level,
                "entry_price": format_price(item.entry_price, snapshot.currency),
                "target_price": format_price(item.target_price, snapshot.currency),
                "stop_loss_price": format_price(item.stop_loss_price, snapshot.currency),
                "expected_return_pct": format_pct(item.expected_return_pct),
                "captured_at": snapshot.captured_at.isoformat(sep=" ") if snapshot.captured_at else UNKNOWN_TEXT,
                "data_note": item.data_note,
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

    lines: list[str] = []
    lines.append("# Investment Strategy Summary")
    lines.append("")
    lines.append(context["summary"])
    lines.append("")
    lines.append(f"- Asset: {context['request']['asset_label']}")
    lines.append(f"- Market: {context['request']['market']}")
    lines.append(f"- Duration: {context['request']['duration']}")
    lines.append(f"- Risk profile: {context['request']['propensity']}")
    lines.append(f"- Data source: {context['data_source_label']}")
    lines.append(f"- Generated from: {context['generated_from']}")
    if context["provider_warning"]:
        lines.append(f"- Provider warning: {context['provider_warning']}")
    lines.append("")
    lines.append("# Guidance")
    lines.append("")
    for item in context["guidance"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("# Recommendations")
    lines.append("")
    for row in context["rows"]:
        lines.append(f"## {row['name']} ({row['symbol']})")
        lines.append(f"- Current price: {row['current_price']}")
        lines.append(f"- Thesis: {row['rationale']}")
        lines.append(f"- Metrics: {row['metrics']}")
        lines.append(f"- Risk level: {row['risk_level']}")
        lines.append(f"- Entry: {row['entry_price']}")
        lines.append(f"- Target: {row['target_price']}")
        lines.append(f"- Stop: {row['stop_loss_price']}")
        lines.append(f"- Expected return: {row['expected_return_pct']}")
        lines.append("")
    lines.append("# Risk Notes")
    lines.append("")
    for card in context["risk_cards"]:
        lines.append(f"## {card['name']} ({card['symbol']})")
        for warning in card["warnings"]:
            lines.append(f"- {warning}")
        lines.append(f"- Data note: {card['data_note']}")
        lines.append("")
    lines.append("# Execution Payloads")
    lines.append("")
    for signal in context["signals"]:
        lines.append("```json")
        lines.append(signal["pretty_json"])
        lines.append("```")
    lines.append("")
    lines.append(context["disclaimer"])
    return "\n".join(lines)


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
