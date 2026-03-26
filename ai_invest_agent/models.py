from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class InvestmentRequest:
    asset_krw: int
    propensity: str
    market: str
    duration: str


@dataclass(frozen=True)
class TechnicalIndicators:
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    moving_average_5: float | None
    moving_average_20: float | None
    moving_average_60: float | None


@dataclass(frozen=True)
class FundamentalIndicators:
    per: float | None
    pbr: float | None
    roe: float | None
    dividend_yield: float | None


@dataclass(frozen=True)
class RiskSnapshot:
    volatility_30d: float | None
    delisting_risk: str
    short_interest_ratio: float | None
    negative_news_flags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SecuritySnapshot:
    symbol: str
    name: str
    market: str
    price: float | None
    currency: str
    captured_at: datetime | None
    technicals: TechnicalIndicators
    fundamentals: FundamentalIndicators
    risk: RiskSnapshot
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Recommendation:
    symbol: str
    name: str
    current_price: float | None
    rationale: str
    risk_level: str
    entry_price: float | None
    target_price: float | None
    stop_loss_price: float | None
    expected_return_pct: float | None
    signal_action: str
    quantity: int
    reason: str
    warnings: List[str]
    data_note: str


@dataclass(frozen=True)
class TradePrices:
    current_price: float | None
    entry_price: float | None
    target_price: float | None
    stop_loss: float | None


@dataclass(frozen=True)
class TradeSignalMetadata:
    data_source: str
    analyzed_at: str


@dataclass(frozen=True)
class TradeSignal:
    ticker: str
    action: str
    confidence_score: float
    prices: TradePrices
    rationale: List[str]
    metadata: TradeSignalMetadata

