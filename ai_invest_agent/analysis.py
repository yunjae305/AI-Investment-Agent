from __future__ import annotations

from datetime import datetime, timezone

from ai_invest_agent.models import (
    InvestmentRequest,
    Recommendation,
    SecuritySnapshot,
    TradePrices,
    TradeSignal,
    TradeSignalMetadata,
)


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
        "단타": "변동성 관리가 핵심이므로 분할 진입과 짧은 손절 라인이 필요합니다.",
        "중기": "실적과 추세가 동시에 유지되는 종목 위주로 접근합니다.",
        "장기": "밸류에이션과 체력 확인 후 장기 복리 가능성이 높은 종목 비중을 높입니다.",
    }.get(request.duration, "기간 조건이 명확하지 않아 보수적으로 분할 진입 전략을 사용합니다.")
    top_names = ", ".join(item.name for item in recommendations[:3])
    return (
        f"현재 제안 비중은 {invest_ratio}입니다. "
        f"{duration_view} 우선 검토 종목은 {top_names}입니다."
    )


def build_portfolio_guidance(request: InvestmentRequest) -> list[str]:
    guidance = {
        "안정추구형": [
            "1회 진입 금액을 낮추고 현금 비중을 높게 유지합니다.",
            "배당 또는 저변동성 종목 위주로 분산합니다.",
        ],
        "중립형": [
            "주도 섹터와 방어 섹터를 혼합해 변동성을 완화합니다.",
            "상위 2개 종목에 과도하게 집중하지 않도록 관리합니다.",
        ],
        "공격투자형": [
            "추세가 살아 있는 종목 중심으로 비중을 늘리되 손절 기준을 엄격히 적용합니다.",
            "고변동 종목은 분할 매수와 수익 실현 구간 분할이 필요합니다.",
        ],
    }.get(
        request.propensity,
        ["성향 정보가 모호해 분할 매수와 보수적 현금 비중을 적용합니다."],
    )
    duration_note = {
        "단타": "단기 전략이므로 진입 후 손절/익절 실행 속도가 중요합니다.",
        "중기": "중기 전략이므로 실적 일정과 추세 훼손 여부를 함께 점검합니다.",
        "장기": "장기 전략이므로 분기 실적과 밸류에이션 재평가를 핵심 지표로 봅니다.",
    }.get(request.duration, "투자 기간이 명확하지 않아 보수적으로 접근합니다.")
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
    price = snapshot.price
    entry = _entry_price(snapshot)
    target = _target_price(snapshot)
    stop = _stop_loss_price(snapshot)
    expected_return = ((target - entry) / entry * 100.0) if entry and target else None
    action = _action(snapshot)
    quantity = _quantity(request, entry)
    warnings = _warnings(snapshot)
    rationale = _rationale(snapshot, request.duration)
    risk_level = _risk_level(snapshot)
    data_note = " / ".join(snapshot.notes) if snapshot.notes else "실시간 API 연동이 필요합니다."
    return Recommendation(
        symbol=snapshot.symbol,
        name=snapshot.name,
        current_price=price,
        rationale=rationale,
        risk_level=risk_level,
        entry_price=entry,
        target_price=target,
        stop_loss_price=stop,
        expected_return_pct=round(expected_return, 2) if expected_return is not None else None,
        signal_action=action,
        quantity=quantity,
        reason=f"{snapshot.name}은(는) {rationale}",
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
        warnings.append(f"현재 RSI {rsi:.1f}로 과열 구간에 근접해 추격 매수보다 분할 진입이 유리합니다.")
    if snapshot.risk.volatility_30d is not None and snapshot.risk.volatility_30d >= 35:
        warnings.append("최근 변동성이 높아 손절 라인 이탈 시 기계적으로 비중을 축소해야 합니다.")
    if snapshot.risk.short_interest_ratio is not None and snapshot.risk.short_interest_ratio >= 1.5:
        warnings.append(f"공매도/숏 비중 관련 지표가 {snapshot.risk.short_interest_ratio:.1f} 수준이라 수급 변동에 주의가 필요합니다.")
    for item in snapshot.risk.negative_news_flags:
        warnings.append(f"부정 요인: {item}")
    if not warnings:
        warnings.append("유의미한 경고가 제한적이지만, 실시간 뉴스 점검은 별도로 필요합니다.")
    return warnings


def _rationale(snapshot: SecuritySnapshot, duration: str) -> str:
    tech = snapshot.technicals
    trend: list[str] = []
    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            trend.append("단기/중기 이동평균이 정배열입니다")
    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        trend.append("MACD가 시그널 상단입니다")
    if duration == "장기" and snapshot.fundamentals.roe is not None:
        trend.append(f"ROE {snapshot.fundamentals.roe:.1f}%로 수익성이 유지됩니다")
    if not trend:
        trend.append("추세 신호가 혼재되어 보수적 접근이 필요합니다")
    return ", ".join(trend)


def _risk_level(snapshot: SecuritySnapshot) -> str:
    volatility = snapshot.risk.volatility_30d or 0.0
    if volatility >= 35 or snapshot.risk.delisting_risk == "높음":
        return "높음"
    if volatility >= 25 or snapshot.risk.delisting_risk == "보통":
        return "보통"
    return "낮음"


# ──────────────────────────────────────────────
# TradeSignal pipeline (Blueprint JSON schema)
# ──────────────────────────────────────────────

_PROPENSITY_WEIGHTS = {
    "안정추구형": {"technical": 0.4, "fundamental": 0.4, "risk_penalty": 0.2},
    "중립형":     {"technical": 0.5, "fundamental": 0.3, "risk_penalty": 0.2},
    "공격투자형": {"technical": 0.6, "fundamental": 0.2, "risk_penalty": 0.2},
}
_DEFAULT_WEIGHTS = {"technical": 0.5, "fundamental": 0.3, "risk_penalty": 0.2}


def _confidence_score(snapshot: SecuritySnapshot, propensity: str) -> float:
    """0~100 범위의 확신도 점수 산출. 성향별 가중치 적용."""
    weights = _PROPENSITY_WEIGHTS.get(propensity, _DEFAULT_WEIGHTS)
    tech = snapshot.technicals
    fund = snapshot.fundamentals
    risk = snapshot.risk

    # ── 기술적 점수 (0~100) ──
    tech_score = 0.0
    tech_count = 0

    if tech.rsi is not None:
        # RSI 50 근방을 최고점으로, 과열(>70)/과매도(<30) 구간은 감점
        rsi_score = max(0.0, 50.0 - abs(50.0 - tech.rsi))  # 0~50
        tech_score += rsi_score * 2  # 0~100
        tech_count += 1

    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_60:
        # 정배열이면 만점, 역배열이면 0점
        if tech.moving_average_5 >= tech.moving_average_20 >= tech.moving_average_60:
            tech_score += 100
        elif tech.moving_average_5 < tech.moving_average_20:
            tech_score += 0
        else:
            tech_score += 50
        tech_count += 1

    if tech.macd is not None and tech.macd_signal is not None:
        tech_score += 100 if tech.macd >= tech.macd_signal else 30
        tech_count += 1

    tech_final = (tech_score / tech_count) if tech_count else 50.0

    # ── 기본적 점수 (0~100) ──
    fund_score = 0.0
    fund_count = 0

    if fund.per is not None and fund.per > 0:
        # PER 10~25 이상적, 그 이상은 감점
        per_score = max(0.0, 100.0 - max(0.0, fund.per - 10.0) * 2.5)
        fund_score += min(per_score, 100.0)
        fund_count += 1

    if fund.roe is not None:
        roe_score = min(fund.roe * 4.0, 100.0)  # ROE 25%가 만점
        fund_score += roe_score
        fund_count += 1

    if fund.pbr is not None and fund.pbr > 0:
        pbr_score = max(0.0, 100.0 - (fund.pbr - 1.0) * 15.0)
        fund_score += min(pbr_score, 100.0)
        fund_count += 1

    fund_final = (fund_score / fund_count) if fund_count else 50.0

    # ── 리스크 패널티 (0~100, 높을수록 불리) ──
    risk_penalty = 0.0
    if risk.volatility_30d is not None:
        risk_penalty += min(risk.volatility_30d, 50.0)  # 최대 50점 패널티
    risk_penalty += len(risk.negative_news_flags) * 5.0
    risk_penalty = min(risk_penalty, 100.0)

    raw = (
        tech_final * weights["technical"]
        + fund_final * weights["fundamental"]
        - risk_penalty * weights["risk_penalty"]
    )
    return round(max(0.0, min(raw, 100.0)), 1)


def _trade_rationale(snapshot: SecuritySnapshot, propensity: str) -> list[str]:
    tech = snapshot.technicals
    fund = snapshot.fundamentals
    lines: list[str] = []

    if tech.moving_average_5 and tech.moving_average_20 and tech.moving_average_5 >= tech.moving_average_20:
        if tech.moving_average_20 and tech.moving_average_60 and tech.moving_average_20 >= tech.moving_average_60:
            lines.append("단기 이동평균선이 장기 이동평균선을 상향 돌파 (Golden Cross).")
        else:
            lines.append("단기 이동평균이 중기 이동평균 위에 위치해 단기 상승 추세.")

    if tech.macd is not None and tech.macd_signal is not None and tech.macd >= tech.macd_signal:
        lines.append("MACD가 시그널선 위에 위치하여 상승 모멘텀이 유지됩니다.")

    if fund.per is not None and fund.per < 20:
        lines.append(f"PER {fund.per:.1f}로 동종 업계 대비 저평가 구간에 위치.")
    elif fund.per is not None and fund.per >= 40:
        lines.append(f"PER {fund.per:.1f}로 고평가 구간이므로 밸류에이션 부담이 존재.")

    if fund.roe is not None and fund.roe >= 15:
        lines.append(f"ROE {fund.roe:.1f}%로 우수한 자기자본이익률을 유지.")

    propensity_note = {
        "공격투자형": "투자자의 '공격형' 성향에 부합하는 높은 변동성 및 성장 잠재력.",
        "안정추구형": "투자자의 '안정형' 성향에 맞춰 저변동성 및 배당 수익 중심으로 평가.",
        "중립형": "투자자의 '중립형' 성향에 부합하는 균형적 성장/안정 프로파일.",
    }.get(propensity)
    if propensity_note:
        lines.append(propensity_note)

    if not lines:
        lines.append("추세 신호가 혼재하여 추가적인 모니터링이 필요합니다.")

    return lines


def build_trade_signals(
    request: InvestmentRequest,
    snapshots: list[SecuritySnapshot],
    data_source: str = "mock",
) -> list[TradeSignal]:
    """Blueprint JSON 스키마에 맞는 TradeSignal 목록을 반환합니다."""
    analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ranked = sorted(snapshots, key=_score_snapshot, reverse=True)[:5]
    signals: list[TradeSignal] = []
    for snapshot in ranked:
        entry = _entry_price(snapshot)
        target = _target_price(snapshot)
        stop = _stop_loss_price(snapshot)
        signals.append(
            TradeSignal(
                ticker=snapshot.symbol,
                action=_action(snapshot),
                confidence_score=_confidence_score(snapshot, request.propensity),
                prices=TradePrices(
                    current_price=snapshot.price,
                    entry_price=entry,
                    target_price=target,
                    stop_loss=stop,
                ),
                rationale=_trade_rationale(snapshot, request.propensity),
                metadata=TradeSignalMetadata(
                    data_source=data_source,
                    analyzed_at=analyzed_at,
                ),
            )
        )
    return signals
