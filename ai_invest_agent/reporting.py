from __future__ import annotations

import json
from typing import Iterable

from ai_invest_agent.analysis import build_portfolio_guidance, build_strategy_summary
from ai_invest_agent.models import InvestmentRequest, Recommendation, SecuritySnapshot


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
                "captured_at": snapshot.captured_at.isoformat(sep=" ") if snapshot.captured_at else "실시간 API 호출이 필요합니다",
                "data_note": item.data_note,
            }
        )
        payload = {
            "action": item.signal_action,
            "symbol": item.symbol,
            "quantity": item.quantity,
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
    return {
        "request": {
            "asset_krw": request.asset_krw,
            "asset_label": f"{request.asset_krw:,}원",
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
        "disclaimer": "투자 판단은 참고 정보이며, 최종 투자 책임은 사용자에게 있습니다.",
        "uses_mock_data": data_source == "mock",
        "data_source_label": "Yahoo Finance" if data_source == "yfinance" else "Mock Data",
        "provider_warning": provider_warning,
        "generated_from": _guess_generated_from(snapshot_list),
    }


def render_markdown_report(
    request: InvestmentRequest,
    recommendations: list[Recommendation],
    snapshots: Iterable[SecuritySnapshot],
    data_source: str = "mock",
    provider_warning: str | None = None,
) -> str:
    context = build_report_context(request, recommendations, snapshots, data_source, provider_warning)
    lines: list[str] = []
    lines.append("#1. 투자 전략 요약")
    lines.append("")
    lines.append(context["summary"])
    lines.append("")
    lines.append(f"- 데이터 소스: {context['data_source_label']}")
    lines.append(f"- 산출 기준: {context['generated_from']}")
    if context["provider_warning"]:
        lines.append(f"- 공급자 경고: {context['provider_warning']}")
    for item in context["guidance"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("#2. 상세 종목 추천 리스트 (Table)")
    lines.append("")
    lines.append("| 종목명(티커) | 현재가 | 추천 사유 | 주요 수치(RSI/PER) | 위험도 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for row in context["rows"]:
        lines.append(
            f"| {row['name']}({row['symbol']}) | {row['current_price']} | {row['rationale']} | {row['metrics']} | {row['risk_level']} |"
        )
    lines.append("")
    lines.append("#3. 매매 가이드라인 (Actionable Items)")
    lines.append("")
    for row in context["rows"]:
        lines.append(f"## {row['name']} ({row['symbol']})")
        lines.append(f"- [매수 추천가]: {row['entry_price']}")
        lines.append(f"- [매도 목표가]: {row['target_price']} / 기대 수익률 {row['expected_return_pct']}")
        lines.append(f"- [손절 기준]: {row['stop_loss_price']} 하향 이탈 시 비중 축소")
        lines.append("")
    lines.append("#4. 리스크 센터 (Risk & Warning)")
    lines.append("")
    for card in context["risk_cards"]:
        lines.append(f"## {card['name']} ({card['symbol']})")
        for warning in card["warnings"]:
            lines.append(f"- {warning}")
        lines.append(f"- 데이터 비고: {card['data_note']}")
        lines.append("")
    lines.append("#5. 자동 매매 시그널 (JSON for API)")
    lines.append("")
    for signal in context["signals"]:
        lines.append("```json")
        lines.append(signal["pretty_json"])
        lines.append("```")
    lines.append("")
    lines.append(context["disclaimer"])
    return "\n".join(lines)


def format_num(value: float | None) -> str:
    if value is None:
        return "실시간 API 호출이 필요합니다"
    return f"{value:.1f}"


def format_pct(value: float | None) -> str:
    if value is None:
        return "실시간 API 호출이 필요합니다"
    return f"{value:.2f}%"


def format_price(value: float | None, currency: str) -> str:
    if value is None:
        return "실시간 API 호출이 필요합니다"
    if currency == "KRW":
        return f"{int(round(value)):,}원"
    return f"${value:,.2f}"


def _guess_generated_from(snapshots: list[SecuritySnapshot]) -> str:
    for snapshot in snapshots:
        if snapshot.captured_at is not None:
            return snapshot.captured_at.isoformat(sep=" ")
    return "실시간 API 호출이 필요합니다"
