from __future__ import annotations

import argparse
import sys

from ai_invest_agent.analysis import build_recommendations
from ai_invest_agent.models import InvestmentRequest
from ai_invest_agent.providers import MockMarketDataProvider, resolve_provider
from ai_invest_agent.reporting import render_markdown_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 투자 분석 및 모의매매 에이전트")
    parser.add_argument("--asset", type=int, required=True, help="투자 자산 (KRW 기준 정수)")
    parser.add_argument("--propensity", required=True, help="안정추구형/중립형/공격투자형")
    parser.add_argument("--market", required=True, help="국내/미국/해외")
    parser.add_argument("--duration", required=True, help="단타/중기/장기")
    parser.add_argument("--data-source", default="yfinance", help="yfinance 또는 mock")
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
        provider_warning = f"{provider_warning + ' / ' if provider_warning else ''}데이터 조회 실패로 mock 데이터로 대체했습니다: {exc}"
        snapshots = provider.list_candidates(request.market)
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
