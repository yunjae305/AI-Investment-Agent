from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from ai_invest_agent.analysis import build_recommendations
from ai_invest_agent.models import InvestmentRequest
from ai_invest_agent.providers import MockMarketDataProvider, resolve_provider
from ai_invest_agent.reporting import build_report_context


app = Flask(__name__)
app.json.ensure_ascii = False


DEFAULT_FORM = {
    "asset": "10000000",
    "propensity": "중립형",
    "market": "국내",
    "duration": "중기",
    "data_source": "yfinance",
}


@app.get("/")
def index():
    return render_template("index.html", form=DEFAULT_FORM, result=None, error=None)


@app.post("/analyze")
def analyze():
    form = {
        "asset": request.form.get("asset", DEFAULT_FORM["asset"]).strip(),
        "propensity": request.form.get("propensity", DEFAULT_FORM["propensity"]).strip(),
        "market": request.form.get("market", DEFAULT_FORM["market"]).strip(),
        "duration": request.form.get("duration", DEFAULT_FORM["duration"]).strip(),
        "data_source": request.form.get("data_source", DEFAULT_FORM["data_source"]).strip(),
    }
    try:
        investment_request = InvestmentRequest(
            asset_krw=_parse_asset(form["asset"]),
            propensity=form["propensity"],
            market=form["market"],
            duration=form["duration"],
        )
    except ValueError as exc:
        return render_template("index.html", form=form, result=None, error=str(exc)), 400

    provider, resolved_source, provider_warning = resolve_provider(form["data_source"])
    try:
        snapshots = provider.list_candidates(investment_request.market)
    except Exception as exc:
        provider = MockMarketDataProvider()
        resolved_source = "mock"
        provider_warning = f"{provider_warning + ' / ' if provider_warning else ''}데이터 조회 실패로 mock 데이터로 대체했습니다: {exc}"
        snapshots = provider.list_candidates(investment_request.market)
    recommendations = build_recommendations(investment_request, snapshots)
    result = build_report_context(
        investment_request,
        recommendations,
        snapshots,
        data_source=resolved_source,
        provider_warning=provider_warning,
    )
    return render_template("index.html", form=form, result=result, error=None)


@app.post("/api/analyze")
def analyze_api():
    payload = request.get_json(silent=True) or {}
    try:
        investment_request = InvestmentRequest(
            asset_krw=_parse_asset(str(payload.get("asset", DEFAULT_FORM["asset"]))),
            propensity=str(payload.get("propensity", DEFAULT_FORM["propensity"])).strip(),
            market=str(payload.get("market", DEFAULT_FORM["market"])).strip(),
            duration=str(payload.get("duration", DEFAULT_FORM["duration"])).strip(),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    provider, resolved_source, provider_warning = resolve_provider(str(payload.get("data_source", DEFAULT_FORM["data_source"])))
    try:
        snapshots = provider.list_candidates(investment_request.market)
    except Exception as exc:
        provider = MockMarketDataProvider()
        resolved_source = "mock"
        provider_warning = f"{provider_warning + ' / ' if provider_warning else ''}데이터 조회 실패로 mock 데이터로 대체했습니다: {exc}"
        snapshots = provider.list_candidates(investment_request.market)
    recommendations = build_recommendations(investment_request, snapshots)
    result = build_report_context(
        investment_request,
        recommendations,
        snapshots,
        data_source=resolved_source,
        provider_warning=provider_warning,
    )
    return jsonify(result)


def _parse_asset(raw_asset: str) -> int:
    normalized = raw_asset.replace(",", "").replace("원", "").strip()
    if not normalized.isdigit():
        raise ValueError("자산은 숫자만 입력해야 합니다. 예: 10000000")
    asset = int(normalized)
    if asset <= 0:
        raise ValueError("자산은 0보다 커야 합니다.")
    return asset


if __name__ == "__main__":
    app.run(debug=True)
