from __future__ import annotations

import argparse
import sys

from ai_invest_agent.analysis import build_recommendations, build_trade_signals
from ai_invest_agent.models import InvestmentRequest
from ai_invest_agent.providers import MockMarketDataProvider, resolve_provider
from ai_invest_agent.reporting import render_markdown_report, render_trade_signals_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 투자 분석 및 모의매매 에이전트")
    parser.add_argument("--asset", type=int, default=10_000_000, help="투자 자산 (KRW 기준 정수, 기본값: 10,000,000)")
    parser.add_argument("--propensity", default="중립형", help="안정추구형/중립형/공격투자형 (기본값: 중립형)")
    parser.add_argument("--market", default="국내", help="국내/미국 (기본값: 국내)")
    parser.add_argument("--duration", default="중기", help="단타/중기/장기 (기본값: 중기)")
    parser.add_argument("--data-source", default="mock", help="yfinance 또는 mock (기본값: mock)")
    parser.add_argument(
        "--output",
        choices=["signal", "report"],
        default="signal",
        help="출력 형식: signal=TradeSignal JSON (기본값), report=Markdown 리포트",
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    request = InvestmentRequest(
        asset_krw=args.asset,
        propensity=args.propensity,
        market=args.market,
        duration=args.duration,
    )

    provider, resolved_source, provider_warning = resolve_provider(args.data_source)
    try:
        snapshots = provider.list_candidates(request.market)
    except Exception as exc:
        provider = MockMarketDataProvider()
        resolved_source = "mock"
        provider_warning = (
            f"{provider_warning + ' / ' if provider_warning else ''}"
            f"데이터 조회 실패로 mock 데이터로 대체했습니다: {exc}"
        )
        snapshots = provider.list_candidates(request.market)

    if args.output == "signal":
        signals = build_trade_signals(request, snapshots, data_source=resolved_source)
        if provider_warning:
            print(f"[경고] {provider_warning}\n", file=sys.stderr)
        print(render_trade_signals_json(signals))
    else:
        recommendations = build_recommendations(request, snapshots)
        report = render_markdown_report(
            request,
            recommendations,
            snapshots,
            data_source=resolved_source,
            provider_warning=provider_warning,
        )
        print(report)


if __name__ == "__main__":
    main()
