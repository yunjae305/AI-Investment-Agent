from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

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


def build_provider(source: str) -> MarketDataProvider:
    _ = source
    return MockMarketDataProvider()


def resolve_provider(source: str) -> tuple[MarketDataProvider, str, str | None]:
    _ = source
    return MockMarketDataProvider(), "mock", None
