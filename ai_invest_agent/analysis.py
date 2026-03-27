from __future__ import annotations

from ai_invest_agent.models import InvestmentRequest, Recommendation, SecuritySnapshot


PROPENSITY_BUDGET = {
    "안정추구형": 0.18,
    "중립형": 0.24,
    "공격투자형": 0.32,
}


def build_recommendations(
    request: InvestmentRequest,
    snapshots: list[SecuritySnapshot],
) -> list[Recommendation]:
    ranked = sorted(snapshots, key=_score_snapshot, reverse=True)[:5]
    return [_build_single_recommendation(request, snapshot) for snapshot in ranked]


def build_strategy_summary(request: InvestmentRequest, recommendations: list[Recommendation]) -> str:
    invest_ratio = {
        "안정추구형": "주식 55%, 현금 45%",
        "중립형": "주식 70%, 현금 30%",
        "공격투자형": "주식 85%, 현금 15%",
    }.get(request.propensity, "주식 65%, 현금 35%")
    duration_view = {
        "단기": "변동성 관리와 분할 진입이 중요합니다.",
        "중기": "추세와 실적 흐름이 동시에 좋은 종목 위주로 접근합니다.",
        "장기": "가치와 체력을 함께 확인하고 장기 복리 가능성이 있는 종목의 비중을 높입니다.",
    }.get(request.duration, "보수적으로 분할 진입하는 전략을 사용합니다.")
    top_names = ", ".join(item.name for item in recommendations[:3])
    return f"현재 제안 비중은 {invest_ratio}입니다. {duration_view} 우선 검토 종목은 {top_names}입니다."


def build_portfolio_guidance(request: InvestmentRequest) -> list[str]:
    guidance = {
        "안정추구형": [
            "1회 진입 금액을 낮추고 현금 비중을 높게 유지합니다.",
            "배당 또는 저변동성 종목을 우선 검토합니다.",
        ],
        "중립형": [
            "주도 섹터와 방어 섹터를 혼합해 변동성을 완화합니다.",
            "상위 2개 종목에 과도하게 집중하지 않도록 관리합니다.",
        ],
        "공격투자형": [
            "추세가 강한 종목 중심으로 보되 손절 기준을 명확히 둡니다.",
            "고변동 종목은 분할 매수와 분할 매도를 전제로 접근합니다.",
        ],
    }.get(
        request.propensity,
        ["성향 정보가 불명확하므로 보수적인 분할 매수와 현금 비중 유지를 권장합니다."],
    )
    duration_note = {
        "단기": "단기 전략에서는 진입가와 손절가를 함께 관리해야 합니다.",
        "중기": "중기 전략에서는 실적 일정과 추세 지속 여부를 함께 봐야 합니다.",
        "장기": "장기 전략에서는 실적, 밸류에이션, 경쟁력을 함께 봐야 합니다.",
    }.get(request.duration, "투자 기간이 불명확하므로 보수적 전략을 사용합니다.")
    return [duration_note, *guidance]


def _score_snapshot(snapshot: SecuritySnapshot) -> float:
    tech = snapshot.technicals
    fund = snapshot.fundamentals
    risk = snapshot.risk
    score = 0.0
    if tech.rsi is not None:
        score += max(0.0, 30.0 - abs(55.0 - tech.rsi))
    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            score += 18.0
    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        score += 10.0
    if fund.roe is not None:
        score += min(fund.roe, 25.0)
    if fund.per is not None:
        score += max(0.0, 20.0 - min(fund.per / 2.0, 20.0))
    if risk.volatility_30d is not None:
        score -= risk.volatility_30d / 4.0
    score -= len(risk.negative_news_flags) * 2.5
    return round(score, 2)


def _build_single_recommendation(request: InvestmentRequest, snapshot: SecuritySnapshot) -> Recommendation:
    entry = _entry_price(snapshot)
    target = _target_price(snapshot)
    stop = _stop_loss_price(snapshot)
    expected_return = ((target - entry) / entry * 100.0) if entry and target else None
    action = _action(snapshot)
    quantity = _quantity(request, entry)
    warnings = _warnings(snapshot)
    rationale = _rationale(snapshot, request.duration)
    risk_level = _risk_level(snapshot)
    data_note = " / ".join(snapshot.notes) if snapshot.notes else "Additional live data integration recommended."
    return Recommendation(
        symbol=snapshot.symbol,
        name=snapshot.name,
        current_price=snapshot.price,
        rationale=rationale,
        risk_level=risk_level,
        entry_price=entry,
        target_price=target,
        stop_loss_price=stop,
        expected_return_pct=round(expected_return, 2) if expected_return is not None else None,
        signal_action=action,
        quantity=quantity,
        reason=f"{snapshot.name}: {rationale}",
        warnings=warnings,
        data_note=data_note,
    )


def _entry_price(snapshot: SecuritySnapshot) -> float | None:
    if snapshot.price is None:
        return None
    if snapshot.technicals.rsi and snapshot.technicals.rsi >= 70:
        return round(snapshot.price * 0.97, 2)
    return round(snapshot.price * 0.99, 2)


def _target_price(snapshot: SecuritySnapshot) -> float | None:
    if snapshot.price is None:
        return None
    return round(snapshot.price * 1.08, 2)


def _stop_loss_price(snapshot: SecuritySnapshot) -> float | None:
    if snapshot.price is None:
        return None
    risk_mult = 0.94 if _risk_level(snapshot) == "높음" else 0.96
    return round(snapshot.price * risk_mult, 2)


def _action(snapshot: SecuritySnapshot) -> str:
    rsi = snapshot.technicals.rsi
    if rsi is None:
        return "HOLD"
    if rsi >= 75:
        return "HOLD"
    if rsi <= 35:
        return "BUY"
    if snapshot.technicals.macd and snapshot.technicals.macd_signal and snapshot.technicals.macd > snapshot.technicals.macd_signal:
        return "BUY"
    return "HOLD"


def _quantity(request: InvestmentRequest, entry_price: float | None) -> int:
    if entry_price is None or entry_price <= 0:
        return 0
    budget_ratio = PROPENSITY_BUDGET.get(request.propensity, 0.2)
    return int((request.asset_krw * budget_ratio) // entry_price)


def _warnings(snapshot: SecuritySnapshot) -> list[str]:
    warnings: list[str] = []
    rsi = snapshot.technicals.rsi
    if rsi is not None and rsi >= 70:
        warnings.append(f"현재 RSI {rsi:.1f}로 과열 구간에 가까워 추격 매수보다 분할 진입이 적합합니다.")
    if snapshot.risk.volatility_30d is not None and snapshot.risk.volatility_30d >= 35:
        warnings.append("최근 변동성이 높아 손절 라인과 주문 크기 제한이 필요합니다.")
    if snapshot.risk.short_interest_ratio is not None and snapshot.risk.short_interest_ratio >= 1.5:
        warnings.append(f"공매도 관련 지표가 {snapshot.risk.short_interest_ratio:.1f}로 높아 급격한 가격 변동을 주의해야 합니다.")
    for item in snapshot.risk.negative_news_flags:
        warnings.append(f"리스크 요인: {item}")
    if not warnings:
        warnings.append("명확한 위험 경고는 제한적이지만 추가 뉴스 점검이 필요합니다.")
    return warnings


def _rationale(snapshot: SecuritySnapshot, duration: str) -> str:
    tech = snapshot.technicals
    trend: list[str] = []
    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            trend.append("단기와 중기 이동평균이 정배열입니다")
    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        trend.append("MACD가 시그널 상단입니다")
    if duration == "장기" and snapshot.fundamentals.roe is not None:
        trend.append(f"ROE {snapshot.fundamentals.roe:.1f}%로 수익성이 양호합니다")
    if not trend:
        trend.append("추세 신호가 약해 보수적 접근이 필요합니다")
    return ", ".join(trend)


def _risk_level(snapshot: SecuritySnapshot) -> str:
    volatility = snapshot.risk.volatility_30d or 0.0
    if volatility >= 35 or snapshot.risk.delisting_risk == "높음":
        return "높음"
    if volatility >= 25 or snapshot.risk.delisting_risk == "보통":
        return "보통"
    return "낮음"
