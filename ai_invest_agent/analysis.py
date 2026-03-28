from __future__ import annotations

from ai_invest_agent.models import InvestmentRequest, Recommendation, SecuritySnapshot


PROPENSITY_BUDGET = {
    "안정추구형": 0.18,
    "중립형": 0.24,
    "공격투자형": 0.32,
}


def build_recommendations(request: InvestmentRequest, snapshots: list[SecuritySnapshot]) -> list[Recommendation]:
    ranked = sorted(snapshots, key=_score_snapshot, reverse=True)[:5]
    return [_build_single_recommendation(request, snapshot) for snapshot in ranked]


def build_strategy_summary(request: InvestmentRequest, recommendations: list[Recommendation]) -> str:
    invest_ratio = {
        "안정추구형": "주식 55%, 현금 45%",
        "중립형": "주식 70%, 현금 30%",
        "공격투자형": "주식 85%, 현금 15%",
    }.get(request.propensity, "주식 65%, 현금 35%")
    top_names = ", ".join(item.name for item in recommendations[:3])
    return f"권장 자산 배분은 {invest_ratio}입니다. 현재 모의 데이터 기준 상위 관심 종목은 {top_names}입니다."


def build_portfolio_guidance(request: InvestmentRequest) -> list[str]:
    base = {
        "안정추구형": [
            "1회 진입금액을 작게 나누고 현금 비중을 충분히 유지하세요.",
            "변동성이 낮은 종목을 우선 확인하세요.",
        ],
        "중립형": [
            "성장주와 방어주를 섞어 포트폴리오를 구성하세요.",
            "상위 2~3개 종목에 과도하게 몰리지 않게 관리하세요.",
        ],
        "공격투자형": [
            "추세가 강한 종목 중심으로 대응하되 손절 기준을 반드시 지키세요.",
            "분할 매수/분할 매도 규칙을 먼저 정해두세요.",
        ],
    }.get(request.propensity, ["성향 정보가 불명확하므로 보수적으로 접근하세요."])

    duration_note = {
        "단기": "단기 투자에서는 진입가와 손절가를 엄격히 관리하세요.",
        "중기": "중기 투자에서는 실적과 추세 변화를 함께 확인하세요.",
        "장기": "장기 투자에서는 밸류에이션과 사업 체력을 함께 보세요.",
    }.get(request.duration, "투자 기간에 맞는 분할 전략을 사용하세요.")

    return [duration_note, *base]


def _score_snapshot(snapshot: SecuritySnapshot) -> float:
    tech = snapshot.technicals
    fund = snapshot.fundamentals
    risk = snapshot.risk
    score = 0.0

    if tech.rsi is not None:
        score += max(0.0, 30.0 - abs(55.0 - tech.rsi))
    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            score += 16.0
    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        score += 10.0
    if fund.roe is not None:
        score += min(fund.roe, 25.0)
    if fund.per is not None:
        score += max(0.0, 20.0 - min(fund.per / 2.0, 20.0))
    if risk.volatility_30d is not None:
        score -= risk.volatility_30d / 4.0
    score -= len(risk.negative_news_flags) * 2.0
    return round(score, 2)


def _build_single_recommendation(request: InvestmentRequest, snapshot: SecuritySnapshot) -> Recommendation:
    entry = _entry_price(snapshot)
    target = _target_price(snapshot)
    stop = _stop_loss_price(snapshot)
    expected_return = ((target - entry) / entry * 100.0) if entry and target else None
    action = _action(snapshot)
    quantity = _quantity(request, entry)
    warnings = _warnings(snapshot)
    rationale = _rationale(snapshot)
    risk_level = _risk_level(snapshot)
    data_note = " / ".join(snapshot.notes) if snapshot.notes else "mock"

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
    return round(snapshot.price * (0.97 if (snapshot.technicals.rsi or 50) >= 70 else 0.99), 2)


def _target_price(snapshot: SecuritySnapshot) -> float | None:
    if snapshot.price is None:
        return None
    return round(snapshot.price * 1.08, 2)


def _stop_loss_price(snapshot: SecuritySnapshot) -> float | None:
    if snapshot.price is None:
        return None
    return round(snapshot.price * (0.94 if _risk_level(snapshot) == "high" else 0.96), 2)


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
        warnings.append(f"RSI {rsi:.1f}로 과열 구간에 가깝습니다. 분할 진입이 유리합니다.")
    if snapshot.risk.volatility_30d is not None and snapshot.risk.volatility_30d >= 35:
        warnings.append("30일 변동성이 높아 손절 기준을 더 짧게 가져가야 합니다.")
    if snapshot.risk.short_interest_ratio is not None and snapshot.risk.short_interest_ratio >= 1.5:
        warnings.append("공매도 비율이 높아 단기 급락 가능성을 주의하세요.")
    for item in snapshot.risk.negative_news_flags:
        warnings.append(f"리스크 요인: {item}")
    if not warnings:
        warnings.append("특이 리스크는 제한적이지만 분할 진입을 권장합니다.")
    return warnings


def _rationale(snapshot: SecuritySnapshot) -> str:
    trend: list[str] = []
    tech = snapshot.technicals

    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            trend.append("단기·중기 이동평균 정배열")
    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        trend.append("MACD 시그널 상단")
    if snapshot.fundamentals.roe is not None and snapshot.fundamentals.roe >= 10:
        trend.append("ROE가 양호한 수준")
    if not trend:
        trend.append("추세 확인이 필요해 보수적 접근 권장")

    return ", ".join(trend)


def _risk_level(snapshot: SecuritySnapshot) -> str:
    volatility = snapshot.risk.volatility_30d or 0.0
    if volatility >= 35 or snapshot.risk.delisting_risk == "high":
        return "high"
    if volatility >= 25 or snapshot.risk.delisting_risk == "medium":
        return "medium"
    return "low"
