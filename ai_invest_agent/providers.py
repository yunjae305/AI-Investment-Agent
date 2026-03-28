from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import datetime

from ai_invest_agent.kis_adapter import KisApiClient
from ai_invest_agent.models import (
    FundamentalIndicators,
    RiskSnapshot,
    SecuritySnapshot,
    TechnicalIndicators,
)


class MarketDataProvider(ABC):
    @abstractmethod
    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        raise NotImplementedError


class MockMarketDataProvider(MarketDataProvider):
    """모의투자 전용 고정 데이터 제공자"""

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        market_key = market.strip().lower()
        if market_key in {"국내", "kr", "korea"}:
            return self._kr_candidates()
        return self._us_candidates()

    def _kr_candidates(self) -> list[SecuritySnapshot]:
        timestamp = datetime(2026, 3, 28, 9, 0, 0)
        return [
            SecuritySnapshot(
                symbol="005930.KS",
                name="삼성전자",
                market="국내",
                price=84200,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(52.4, 120.2, 118.4, 87300, 81100, 83900, 83400, 80700),
                fundamentals=FundamentalIndicators(5400, 15.2, 60100, 1.4, 9.8, 2.1),
                risk=RiskSnapshot(22.1, "low", 0.4, ["반도체 수요 변동성"]),
                notes=["Provider: mock"],
            ),
            SecuritySnapshot(
                symbol="000660.KS",
                name="SK하이닉스",
                market="국내",
                price=196500,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(58.1, 210.4, 205.8, 206000, 183500, 194800, 191300, 177200),
                fundamentals=FundamentalIndicators(10230, 18.5, 93480, 2.1, 11.9, 1.0),
                risk=RiskSnapshot(31.8, "medium", 1.2, ["메모리 가격 사이클"]),
                notes=["Provider: mock"],
            ),
            SecuritySnapshot(
                symbol="035420.KS",
                name="NAVER",
                market="국내",
                price=223000,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(63.1, 154.7, 141.2, 231000, 206000, 221200, 215800, 202900),
                fundamentals=FundamentalIndicators(9450, 23.2, 171538, 1.3, 6.5, 0.6),
                risk=RiskSnapshot(28.7, "medium", 0.7, ["광고 경기 민감도"]),
                notes=["Provider: mock"],
            ),
        ]

    def _us_candidates(self) -> list[SecuritySnapshot]:
        timestamp = datetime(2026, 3, 27, 16, 0, 0)
        return [
            SecuritySnapshot(
                symbol="MSFT",
                name="Microsoft",
                market="미국",
                price=468.2,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(54.3, 2.8, 2.3, 479.0, 441.0, 466.1, 460.4, 438.2),
                fundamentals=FundamentalIndicators(13.85, 33.8, 42.95, 10.9, 31.4, 0.7),
                risk=RiskSnapshot(19.4, "low", 0.5, ["AI 인프라 CAPEX 부담"]),
                notes=["Provider: mock"],
            ),
            SecuritySnapshot(
                symbol="NVDA",
                name="NVIDIA",
                market="미국",
                price=992.7,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(68.9, 11.4, 10.1, 1015.0, 901.0, 987.2, 954.4, 880.3),
                fundamentals=FundamentalIndicators(20.22, 49.1, 35.08, 28.3, 56.2, 0.1),
                risk=RiskSnapshot(38.8, "high", 1.1, ["밸류에이션 부담"]),
                notes=["Provider: mock"],
            ),
            SecuritySnapshot(
                symbol="GOOGL",
                name="Alphabet",
                market="미국",
                price=182.9,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(46.7, 1.7, 1.9, 188.0, 176.0, 181.4, 183.2, 177.3),
                fundamentals=FundamentalIndicators(7.56, 24.2, 29.98, 6.1, 24.5, 0.5),
                risk=RiskSnapshot(21.5, "low", 0.4, ["광고 매출 경기 민감도"]),
                notes=["Provider: mock"],
            ),
        ]


class KisMarketDataProvider(MarketDataProvider):
    """KIS OpenAPI 실시간 데이터 제공자"""

    KR_CANDIDATES: list[tuple[str, str]] = [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
        ("035420", "NAVER"),
        ("005380", "현대자동차"),
        ("000270", "기아"),
        ("051910", "LG화학"),
        ("006400", "삼성SDI"),
        ("035720", "카카오"),
        ("068270", "셀트리온"),
        ("105560", "KB금융"),
        ("055550", "신한지주"),
        ("017670", "SK텔레콤"),
        ("030200", "KT"),
        ("086790", "하나금융지주"),
        ("003550", "LG"),
        ("012330", "현대모비스"),
        ("028260", "삼성물산"),
        ("066570", "LG전자"),
        ("032830", "삼성생명"),
        ("096770", "SK이노베이션"),
    ]

    def __init__(self, env: str = "demo") -> None:
        self._client = KisApiClient(env=env)

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        market_key = market.strip().lower()
        if market_key in {"국내", "kr", "korea"}:
            return self._fetch_kr_candidates()
        return []

    def _fetch_kr_candidates(self) -> list[SecuritySnapshot]:
        snapshots = []
        for symbol, fallback_name in self.KR_CANDIDATES:
            try:
                snapshot = self._build_snapshot(symbol, fallback_name)
                if snapshot is not None:
                    snapshots.append(snapshot)
            except Exception:
                continue
        return snapshots

    def _build_snapshot(self, symbol: str, fallback_name: str) -> SecuritySnapshot | None:
        price_data = self._client.domestic_price(symbol)
        daily_data = self._client.inquire_daily_price(symbol, count=60)
        fin_data = self._client.financial_ratio(symbol)

        price = price_data.get("price")
        name = price_data.get("name") or fallback_name
        closes = [d["close"] for d in daily_data if d.get("close") is not None]

        return SecuritySnapshot(
            symbol=f"{symbol}.KS",
            name=name,
            market="국내",
            price=price,
            currency="KRW",
            captured_at=datetime.now(),
            technicals=_calc_technicals(closes),
            fundamentals=FundamentalIndicators(
                eps=fin_data.get("eps"),
                per=fin_data.get("per"),
                bps=fin_data.get("bps"),
                pbr=fin_data.get("pbr"),
                roe=fin_data.get("roe"),
                dividend_yield=fin_data.get("dividend_yield"),
            ),
            risk=RiskSnapshot(
                volatility_30d=_calc_volatility(closes),
                delisting_risk="low",
                short_interest_ratio=None,
                negative_news_flags=[],
            ),
            notes=["Provider: KIS"],
        )


# ── 기술적 지표 계산 헬퍼 ──────────────────────────────────────────────────────

def _ema(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return []
    k = 2.0 / (period + 1)
    result = [sum(prices[:period]) / period]
    for p in prices[period:]:
        result.append(p * k + result[-1] * (1 - k))
    return result


def _calc_technicals(closes: list[float]) -> TechnicalIndicators:
    """closes: KIS API 응답 순서(최신→오래된)를 받아 지표 계산"""
    if len(closes) < 2:
        return TechnicalIndicators(None, None, None, None, None, None, None, None)

    prices = list(reversed(closes))  # 오래된→최신 순으로 변환

    ma5 = round(sum(prices[-5:]) / 5, 2) if len(prices) >= 5 else None
    ma20 = round(sum(prices[-20:]) / 20, 2) if len(prices) >= 20 else None
    ma60 = round(sum(prices[-60:]) / 60, 2) if len(prices) >= 60 else None

    # RSI(14)
    rsi = None
    if len(prices) >= 15:
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        avg_gain = sum(max(0.0, d) for d in deltas[-14:]) / 14
        avg_loss = sum(max(0.0, -d) for d in deltas[-14:]) / 14
        rsi = round(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss), 2)

    # MACD(12, 26, 9)
    macd_val = None
    macd_signal = None
    if len(prices) >= 26:
        ema12 = _ema(prices, 12)
        ema26 = _ema(prices, 26)
        offset = len(ema12) - len(ema26)
        macd_line = [e12 - e26 for e12, e26 in zip(ema12[offset:], ema26)]
        if len(macd_line) >= 9:
            signal_line = _ema(macd_line, 9)
            macd_val = round(macd_line[-1], 4)
            macd_signal = round(signal_line[-1], 4)

    # 볼린저 밴드(20)
    bb_upper = bb_lower = None
    if ma20 is not None and len(prices) >= 20:
        std20 = math.sqrt(sum((p - ma20) ** 2 for p in prices[-20:]) / 20)
        bb_upper = round(ma20 + 2 * std20, 2)
        bb_lower = round(ma20 - 2 * std20, 2)

    return TechnicalIndicators(
        rsi=rsi,
        macd=macd_val,
        macd_signal=macd_signal,
        bollinger_upper=bb_upper,
        bollinger_lower=bb_lower,
        moving_average_5=ma5,
        moving_average_20=ma20,
        moving_average_60=ma60,
    )


def _calc_volatility(closes: list[float]) -> float | None:
    """30일 연환산 변동성(%) 계산"""
    prices = list(reversed(closes))
    if len(prices) < 2:
        return None
    n = min(30, len(prices) - 1)
    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(len(prices) - n, len(prices))]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    return round(math.sqrt(variance) * math.sqrt(252) * 100, 2)


def build_provider(source: str) -> MarketDataProvider:
    _ = source
    if KisApiClient.is_configured("demo"):
        return KisMarketDataProvider("demo")
    if KisApiClient.is_configured("real"):
        return KisMarketDataProvider("real")
    return MockMarketDataProvider()


def resolve_provider(source: str) -> tuple[MarketDataProvider, str, str | None]:
    _ = source
    if KisApiClient.is_configured("demo"):
        return KisMarketDataProvider("demo"), "kis-demo", None
    if KisApiClient.is_configured("real"):
        return KisMarketDataProvider("real"), "kis-real", None
    return MockMarketDataProvider(), "mock", None
