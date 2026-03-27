from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from math import isnan
from pathlib import Path
import sys

from ai_invest_agent.kis_adapter import KisApiClient, infer_overseas_exchange
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
    """Deterministic fallback provider for local development and demos."""

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        market_key = market.strip().lower()
        if market_key in {"국내", "kr", "korea"}:
            return self._kr_candidates()
        return self._us_candidates()

    def _kr_candidates(self) -> list[SecuritySnapshot]:
        timestamp = datetime(2026, 3, 26, 9, 0, 0)
        return [
            SecuritySnapshot(
                symbol="005930.KS",
                name="삼성전자",
                market="국내",
                price=84200,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(48.2, 121.0, 118.5, 87000, 81000, 83800, 84550, 80120),
                fundamentals=FundamentalIndicators(15.4, 1.4, 9.8, 2.2),
                risk=RiskSnapshot(22.0, "낮음", 0.3, ["메모리 가격 민감도"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="000660.KS",
                name="SK하이닉스",
                market="국내",
                price=196500,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(57.8, 211.0, 204.0, 205000, 182000, 194800, 191200, 176900),
                fundamentals=FundamentalIndicators(18.7, 2.1, 11.9, 1.1),
                risk=RiskSnapshot(31.0, "낮음", 1.4, ["반도체 업황 변동성"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="035420.KS",
                name="NAVER",
                market="국내",
                price=223000,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(63.1, 155.0, 140.0, 230000, 205000, 221000, 215500, 202400),
                fundamentals=FundamentalIndicators(23.6, 1.3, 6.5, 0.6),
                risk=RiskSnapshot(28.5, "낮음", 0.6, ["광고 경기 둔화 가능성"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="068270.KS",
                name="셀트리온",
                market="국내",
                price=188400,
                currency="KRW",
                captured_at=timestamp,
                technicals=TechnicalIndicators(71.4, 96.0, 81.0, 191500, 172000, 186900, 181200, 174100),
                fundamentals=FundamentalIndicators(34.2, 2.4, 7.1, 0.4),
                risk=RiskSnapshot(35.4, "보통", 1.9, ["바이오 규제 이벤트 민감"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
        ]

    def _us_candidates(self) -> list[SecuritySnapshot]:
        timestamp = datetime(2026, 3, 25, 16, 0, 0)
        return [
            SecuritySnapshot(
                symbol="MSFT",
                name="Microsoft",
                market="미국",
                price=468.2,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(54.3, 2.8, 2.3, 479.0, 441.0, 466.1, 460.4, 438.2),
                fundamentals=FundamentalIndicators(33.8, 10.9, 31.4, 0.7),
                risk=RiskSnapshot(19.4, "낮음", 0.5, ["AI CAPEX 확대"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="NVDA",
                name="NVIDIA",
                market="미국",
                price=992.7,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(68.9, 11.4, 10.1, 1015.0, 901.0, 987.2, 954.4, 880.3),
                fundamentals=FundamentalIndicators(49.1, 28.3, 56.2, 0.1),
                risk=RiskSnapshot(38.8, "보통", 1.1, ["고밸류에이션", "실적 기대치 부담"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="GOOGL",
                name="Alphabet",
                market="미국",
                price=182.9,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(46.7, 1.7, 1.9, 188.0, 176.0, 181.4, 183.2, 177.3),
                fundamentals=FundamentalIndicators(24.2, 6.1, 24.5, 0.5),
                risk=RiskSnapshot(21.5, "낮음", 0.4, ["광고 경기 민감도"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
            SecuritySnapshot(
                symbol="AMD",
                name="AMD",
                market="미국",
                price=173.6,
                currency="USD",
                captured_at=timestamp,
                technicals=TechnicalIndicators(59.1, 3.6, 3.2, 178.0, 161.0, 172.2, 168.4, 155.8),
                fundamentals=FundamentalIndicators(41.7, 4.3, 10.2, 0.0),
                risk=RiskSnapshot(36.1, "보통", 1.0, ["경쟁 심화"]),
                notes=["Provider: mock", "실시간 API 연동 전 개발용 샘플"],
            ),
        ]


class YFinanceMarketDataProvider(MarketDataProvider):
    """Yahoo Finance backed provider using yfinance download/history APIs."""

    KR_CANDIDATES = ["005930.KS", "000660.KS", "035420.KS", "068270.KS"]
    US_CANDIDATES = ["MSFT", "NVDA", "GOOGL", "AMD"]

    def __init__(self) -> None:
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:
            raise RuntimeError("yfinance 패키지가 필요합니다. requirements.txt를 설치하세요.") from exc
        cache_dir = Path(__file__).resolve().parent.parent / ".cache" / "yfinance"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        self.yf = yf

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        market_key = market.strip().lower()
        symbols = self.KR_CANDIDATES if market_key in {"국내", "kr", "korea"} else self.US_CANDIDATES
        snapshots: list[SecuritySnapshot] = []
        for symbol in symbols:
            snapshot = self._build_snapshot(symbol, market)
            if snapshot is not None:
                snapshots.append(snapshot)
        if not snapshots:
            raise RuntimeError("Yahoo Finance에서 데이터를 가져오지 못했습니다.")
        return snapshots

    def _build_snapshot(self, symbol: str, market: str) -> SecuritySnapshot | None:
        ticker = self.yf.Ticker(symbol)
        history = ticker.history(period="6mo", auto_adjust=False)
        if history.empty:
            return None

        close = history["Close"].dropna()
        if close.empty:
            return None

        latest_close = _safe_float(close.iloc[-1])
        timestamp = _normalize_timestamp(close.index[-1])
        info = getattr(ticker, "info", {}) or {}
        currency = str(info.get("currency") or _default_currency(symbol))
        high_band, low_band = _bollinger_bands(close, 20)
        macd, macd_signal = _macd(close)
        volatility = _annualized_volatility(close)
        short_ratio = _safe_float(info.get("shortRatio"))
        notes = [
            "Provider: yfinance",
            "Yahoo Finance 시세/히스토리 기반 계산",
        ]
        if not info:
            notes.append("일부 기본적 지표는 Yahoo Finance 응답 부재로 비어 있을 수 있습니다.")

        return SecuritySnapshot(
            symbol=symbol,
            name=str(info.get("shortName") or info.get("longName") or symbol),
            market=market,
            price=latest_close,
            currency=currency,
            captured_at=timestamp,
            technicals=TechnicalIndicators(
                rsi=_rsi(close, 14),
                macd=macd,
                macd_signal=macd_signal,
                bollinger_upper=high_band,
                bollinger_lower=low_band,
                moving_average_5=_rolling_mean(close, 5),
                moving_average_20=_rolling_mean(close, 20),
                moving_average_60=_rolling_mean(close, 60),
            ),
            fundamentals=FundamentalIndicators(
                per=_safe_float(info.get("trailingPE") or info.get("forwardPE")),
                pbr=_safe_float(info.get("priceToBook")),
                roe=_roe_from_info(info),
                dividend_yield=_dividend_yield_from_info(info),
            ),
            risk=RiskSnapshot(
                volatility_30d=volatility,
                delisting_risk="낮음",
                short_interest_ratio=short_ratio,
                negative_news_flags=_build_negative_flags(info, volatility),
            ),
            notes=notes,
        )


def build_provider(source: str) -> MarketDataProvider:
    source_key = source.strip().lower()
    if source_key == "kis":
        return KisMarketDataProvider()
    if source_key == "hybrid":
        return HybridMarketDataProvider()
    if source_key == "defeatbeta":
        return DefeatBetaResearchMarketDataProvider()
    if source_key == "yfinance":
        return YFinanceMarketDataProvider()
    return MockMarketDataProvider()


def resolve_provider(source: str) -> tuple[MarketDataProvider, str, str | None]:
    try:
        provider = build_provider(source)
        return provider, source.strip().lower() or "mock", None
    except Exception as exc:
        return MockMarketDataProvider(), "mock", f"{source} 공급자 초기화 실패: {exc}"


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if isnan(parsed):
        return None
    return round(parsed, 4)


def _rolling_mean(series, window: int) -> float | None:
    if len(series) < window:
        return None
    return _safe_float(series.rolling(window).mean().iloc[-1])


def _rsi(series, period: int) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(period).mean()
    avg_loss = losses.rolling(period).mean()
    last_loss = avg_loss.iloc[-1]
    if last_loss is None or last_loss == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / last_loss
    return _safe_float(100 - (100 / (1 + rs)))


def _macd(series) -> tuple[float | None, float | None]:
    if len(series) < 26:
        return None, None
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return _safe_float(macd.iloc[-1]), _safe_float(signal.iloc[-1])


def _bollinger_bands(series, window: int) -> tuple[float | None, float | None]:
    if len(series) < window:
        return None, None
    ma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = ma + (std * 2)
    lower = ma - (std * 2)
    return _safe_float(upper.iloc[-1]), _safe_float(lower.iloc[-1])


def _annualized_volatility(series) -> float | None:
    returns = series.pct_change().dropna()
    if returns.empty:
        return None
    return _safe_float(returns.tail(30).std() * (252 ** 0.5) * 100)


def _roe_from_info(info: dict) -> float | None:
    roe = _safe_float(info.get("returnOnEquity"))
    if roe is None:
        return None
    return round(roe * 100, 2) if roe <= 1 else roe


def _dividend_yield_from_info(info: dict) -> float | None:
    value = _safe_float(info.get("dividendYield"))
    if value is None:
        return None
    return round(value * 100, 2) if value <= 1 else value


def _build_negative_flags(info: dict, volatility: float | None) -> list[str]:
    flags: list[str] = []
    pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"))
    if pe is not None and pe >= 40:
        flags.append("밸류에이션 부담")
    if volatility is not None and volatility >= 35:
        flags.append("단기 변동성 확대")
    if _safe_float(info.get("shortRatio")) and float(info.get("shortRatio")) >= 3:
        flags.append("숏 비중 경계")
    sector = info.get("sector")
    if isinstance(sector, str) and sector:
        flags.append(f"{sector} 섹터 민감도")
    return flags[:3]


def _normalize_timestamp(value) -> datetime | None:
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return None


def _default_currency(symbol: str) -> str:
    return "KRW" if symbol.endswith(".KS") else "USD"


class KisMarketDataProvider(MarketDataProvider):
    """Fetch current prices from Korea Investment Open API for KR and US presets."""

    def __init__(self, env: str = "demo") -> None:
        self.client = KisApiClient(env=env)
        self.mock = MockMarketDataProvider()
        self.env = env

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        base_snapshots = self.mock.list_candidates(market)
        enriched: list[SecuritySnapshot] = []
        market_key = market.strip().lower()
        for snapshot in base_snapshots:
            try:
                if market_key in {"국내", "kr", "korea"}:
                    quote = self.client.domestic_price(snapshot.symbol.replace(".KS", ""))
                    name = quote["name"] or snapshot.name
                else:
                    quote = self.client.overseas_price(snapshot.symbol, exchange_code=infer_overseas_exchange(snapshot.symbol)[:3])
                    name = quote["name"] or snapshot.name
                enriched.append(
                    SecuritySnapshot(
                        symbol=snapshot.symbol,
                        name=name,
                        market=snapshot.market,
                        price=quote["price"] or snapshot.price,
                        currency=snapshot.currency,
                        captured_at=datetime.utcnow(),
                        technicals=snapshot.technicals,
                        fundamentals=snapshot.fundamentals,
                        risk=snapshot.risk,
                        notes=list(snapshot.notes) + [f"Provider: KIS Open API ({self.env})"],
                    )
                )
            except Exception as exc:
                snapshot.notes.append(f"KIS quote unavailable: {exc}")
                enriched.append(snapshot)
        return enriched


class HybridMarketDataProvider(MarketDataProvider):
    """Use yfinance coverage and enrich US symbols with defeatbeta research when possible."""

    def __init__(self) -> None:
        self.base_provider = YFinanceMarketDataProvider()
        self.research_provider = DefeatBetaResearchMarketDataProvider(raise_on_init_error=False)

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        snapshots = self.base_provider.list_candidates(market)
        if self.research_provider.available and market.strip().lower() not in {"국내", "kr", "korea"}:
            return self.research_provider.enrich_snapshots(snapshots)
        return snapshots


class DefeatBetaResearchMarketDataProvider(MarketDataProvider):
    """Research-oriented provider backed by defeatbeta when dependencies are available."""

    def __init__(self, raise_on_init_error: bool = True) -> None:
        self.available = False
        self.ticker_cls = None
        self.fallback_provider = YFinanceMarketDataProvider()
        try:
            repo_root = Path(__file__).resolve().parent.parent / "defeatbeta-api"
            if repo_root.exists():
                sys.path.insert(0, str(repo_root))
            from defeatbeta_api.data.ticker import Ticker  # type: ignore

            self.ticker_cls = Ticker
            self.available = True
        except Exception:
            if raise_on_init_error:
                raise

    def list_candidates(self, market: str) -> list[SecuritySnapshot]:
        snapshots = self.fallback_provider.list_candidates(market)
        if market.strip().lower() in {"국내", "kr", "korea"}:
            for item in snapshots:
                item.notes.append("Research provider is currently limited to US symbols.")
            return snapshots
        return self.enrich_snapshots(snapshots)

    def enrich_snapshots(self, snapshots: list[SecuritySnapshot]) -> list[SecuritySnapshot]:
        if not self.available or self.ticker_cls is None:
            return snapshots

        enriched: list[SecuritySnapshot] = []
        for snapshot in snapshots:
            if snapshot.symbol.endswith(".KS"):
                enriched.append(snapshot)
                continue
            try:
                research = self._load_research(snapshot.symbol)
                notes = list(snapshot.notes) + research["notes"]
                negative_flags = list(snapshot.risk.negative_news_flags) + research["negative_flags"]
                enriched.append(
                    SecuritySnapshot(
                        symbol=snapshot.symbol,
                        name=snapshot.name,
                        market=snapshot.market,
                        price=snapshot.price,
                        currency=snapshot.currency,
                        captured_at=snapshot.captured_at,
                        technicals=snapshot.technicals,
                        fundamentals=FundamentalIndicators(
                            per=research["per"] or snapshot.fundamentals.per,
                            pbr=research["pbr"] or snapshot.fundamentals.pbr,
                            roe=research["roe"] or snapshot.fundamentals.roe,
                            dividend_yield=snapshot.fundamentals.dividend_yield,
                        ),
                        risk=RiskSnapshot(
                            volatility_30d=snapshot.risk.volatility_30d,
                            delisting_risk=snapshot.risk.delisting_risk,
                            short_interest_ratio=snapshot.risk.short_interest_ratio,
                            negative_news_flags=negative_flags[:4],
                        ),
                        notes=notes[:5],
                    )
                )
            except Exception as exc:
                snapshot.notes.append(f"defeatbeta research unavailable: {exc}")
                enriched.append(snapshot)
        return enriched

    def _load_research(self, symbol: str) -> dict:
        ticker = self.ticker_cls(symbol)  # type: ignore[misc]
        notes = ["Provider: defeatbeta research"]
        negative_flags: list[str] = []
        per = None
        pbr = None
        roe = None

        try:
            info_df = ticker.info()
            if info_df is not None and not info_df.empty:
                industry = info_df.iloc[0].get("industry")
                sector = info_df.iloc[0].get("sector")
                if industry:
                    notes.append(f"Industry: {industry}")
                if sector:
                    notes.append(f"Sector: {sector}")
        except Exception:
            pass

        try:
            per_df = ticker.ttm_pe()
            if not per_df.empty:
                per = _safe_float(per_df.iloc[-1].get("ttm_pe"))
        except Exception:
            pass

        try:
            pbr_df = ticker.pb_ratio()
            if not pbr_df.empty:
                pbr = _safe_float(pbr_df.iloc[-1].get("pb_ratio"))
        except Exception:
            pass

        try:
            roe_df = ticker.roe()
            if not roe_df.empty:
                roe = _safe_float(roe_df.iloc[-1].get("roe"))
        except Exception:
            pass

        try:
            news_client = ticker.news()
            news_df = news_client.get_news_list() if hasattr(news_client, "get_news_list") else None
            if news_df is not None and not news_df.empty:
                for _, row in news_df.head(2).iterrows():
                    title = str(row.get("title") or row.get("headline") or "").strip()
                    publisher = str(row.get("publisher") or row.get("source") or "").strip()
                    if title:
                        notes.append(f"News: {title[:80]}")
                    if publisher:
                        negative_flags.append(f"Recent coverage from {publisher}")
        except Exception:
            pass

        return {
            "per": per,
            "pbr": pbr,
            "roe": roe,
            "notes": notes,
            "negative_flags": negative_flags,
        }
