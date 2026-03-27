from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from ai_invest_agent.analysis import build_recommendations
from ai_invest_agent.document_export import export_report
from ai_invest_agent.models import InvestmentRequest
from ai_invest_agent.providers import MockMarketDataProvider, resolve_provider
from ai_invest_agent.reporting import attach_artifacts, build_report_context
from ai_invest_agent.trading import build_trading_agent


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "generated_reports"


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / ".env")


app = Flask(__name__)
app.json.ensure_ascii = False


DEFAULT_FORM = {
    "asset": "10000000",
    "propensity": "중립형",
    "market": "국내",
    "duration": "중기",
    "data_source": "hybrid",
    "auto_execute": "",
    "execution_broker": "auto",
    "execution_env": "demo",
}


@app.get("/")
def index():
    return render_template("index.html", form=DEFAULT_FORM, result=None, error=None)


@app.get("/api/config-status")
def config_status():
    return jsonify(
        {
            "kis_demo_configured": _has_kis_credentials("demo"),
            "kis_real_configured": _has_kis_credentials("real"),
            "pdf_export_provider": os.getenv("PDF_EXPORT_PROVIDER", "local"),
            "cloudmersive_configured": bool(os.getenv("CLOUDMERSIVE_API_KEY")),
            "reports_dir": str(REPORTS_DIR),
        }
    )


@app.post("/analyze")
def analyze():
    form = _collect_form(request.form)
    try:
        result = _run_analysis(form, auto_execute=form["auto_execute"] == "on")
    except ValueError as exc:
        return render_template("index.html", form=form, result=None, error=str(exc)), 400
    return render_template("index.html", form=form, result=result, error=None)


@app.post("/api/analyze")
def analyze_api():
    payload = request.get_json(silent=True) or {}
    form = _payload_to_form(payload)
    try:
        result = _run_analysis(form, auto_execute=bool(payload.get("auto_execute")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/execute")
def execute_api():
    payload = request.get_json(silent=True) or {}
    signals = payload.get("signals")
    if not isinstance(signals, list):
        return jsonify({"error": "signals must be a list"}), 400

    broker = str(payload.get("execution_broker", "auto")).strip()
    env = str(payload.get("execution_env", "demo")).strip()
    trader = build_trading_agent(broker=broker, env=env)

    normalized_orders = []
    for item in signals:
        if not isinstance(item, dict):
            continue
        normalized_orders.append(
            RecommendationLike(
                symbol=str(item.get("symbol", "")).strip(),
                signal_action=str(item.get("action", "HOLD")).strip().upper(),
                quantity=int(item.get("quantity", 0) or 0),
                entry_price=_optional_float(item.get("entry_price")),
                target_price=_optional_float(item.get("target_price")),
                stop_loss_price=_optional_float(item.get("stop_loss_price")),
                rationale=str(item.get("reason", "external execution request")).strip(),
            )
        )

    try:
        result = trader.execute_recommendations(normalized_orders)
    except Exception as exc:
        return jsonify({"error": str(exc), "broker": broker, "environment": env}), 400
    return jsonify(result)


@app.get("/reports/<path:filename>")
def download_report(filename: str):
    report_path = REPORTS_DIR / filename
    if not report_path.exists():
        return jsonify({"error": "report not found"}), 404
    return send_file(report_path, as_attachment=True, download_name=report_path.name)


def _run_analysis(form: dict, auto_execute: bool = False) -> dict:
    investment_request = InvestmentRequest(
        asset_krw=_parse_asset(form["asset"]),
        propensity=form["propensity"],
        market=form["market"],
        duration=form["duration"],
    )

    provider, resolved_source, provider_warning = resolve_provider(form["data_source"])
    try:
        snapshots = provider.list_candidates(investment_request.market)
    except Exception as exc:
        provider = MockMarketDataProvider()
        resolved_source = "mock"
        prefix = f"{provider_warning} / " if provider_warning else ""
        provider_warning = f"{prefix}Primary provider failed. Mock data fallback applied: {exc}"
        snapshots = provider.list_candidates(investment_request.market)

    recommendations = build_recommendations(investment_request, snapshots)
    result = build_report_context(
        investment_request,
        recommendations,
        snapshots,
        data_source=resolved_source,
        provider_warning=provider_warning,
    )
    pdf_path = _write_pdf_report(result["markdown_report"])

    execution_result = None
    if auto_execute:
        trader = build_trading_agent(
            broker=form["execution_broker"],
            env=form["execution_env"],
        )
        execution_result = trader.execute_recommendations(recommendations)

    result["execution_broker"] = form["execution_broker"]
    result["execution_env"] = form["execution_env"]
    return attach_artifacts(result, pdf_path=pdf_path, execution_result=execution_result)


def _write_pdf_report(report_text: str) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    output_path = REPORTS_DIR / f"investment_report_{timestamp}.pdf"
    export_report(report_text, output_path)
    return output_path


def _collect_form(source) -> dict:
    return {
        "asset": source.get("asset", DEFAULT_FORM["asset"]).strip(),
        "propensity": source.get("propensity", DEFAULT_FORM["propensity"]).strip(),
        "market": source.get("market", DEFAULT_FORM["market"]).strip(),
        "duration": source.get("duration", DEFAULT_FORM["duration"]).strip(),
        "data_source": source.get("data_source", DEFAULT_FORM["data_source"]).strip(),
        "auto_execute": source.get("auto_execute", DEFAULT_FORM["auto_execute"]).strip(),
        "execution_broker": source.get("execution_broker", DEFAULT_FORM["execution_broker"]).strip(),
        "execution_env": source.get("execution_env", DEFAULT_FORM["execution_env"]).strip(),
    }


def _payload_to_form(payload: dict) -> dict:
    return {
        "asset": str(payload.get("asset", DEFAULT_FORM["asset"])).strip(),
        "propensity": str(payload.get("propensity", DEFAULT_FORM["propensity"])).strip(),
        "market": str(payload.get("market", DEFAULT_FORM["market"])).strip(),
        "duration": str(payload.get("duration", DEFAULT_FORM["duration"])).strip(),
        "data_source": str(payload.get("data_source", DEFAULT_FORM["data_source"])).strip(),
        "auto_execute": "on" if bool(payload.get("auto_execute")) else "",
        "execution_broker": str(payload.get("execution_broker", DEFAULT_FORM["execution_broker"])).strip(),
        "execution_env": str(payload.get("execution_env", DEFAULT_FORM["execution_env"])).strip(),
    }


def _parse_asset(raw_asset: str) -> int:
    normalized = raw_asset.replace(",", "").replace("원", "").strip()
    if not normalized.isdigit():
        raise ValueError("자산은 숫자로 입력해야 합니다. 예: 10000000")
    asset = int(normalized)
    if asset <= 0:
        raise ValueError("자산은 0보다 커야 합니다.")
    return asset


def _optional_float(value) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_kis_credentials(env: str) -> bool:
    prefix = "KIS_PAPER_" if env == "demo" else "KIS_"
    return all(
        bool(os.getenv(key))
        for key in (
            f"{prefix}APP_KEY",
            f"{prefix}APP_SECRET",
            f"{prefix}ACCOUNT_NO",
        )
    )


@dataclass
class RecommendationLike:
    symbol: str
    signal_action: str
    quantity: int
    entry_price: float | None
    target_price: float | None
    stop_loss_price: float | None
    rationale: str


if __name__ == "__main__":
    app.run(debug=True)
