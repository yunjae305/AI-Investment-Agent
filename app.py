from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

from ai_invest_agent.analysis import build_recommendations
from ai_invest_agent.document_export import export_report
from ai_invest_agent.models import InvestmentRequest, MultiAgentAnalysis
from ai_invest_agent.multi_agent import get_mcp_config_status, run_multi_agent_analysis
from ai_invest_agent.providers import MockMarketDataProvider
from ai_invest_agent.reporting import attach_artifacts, build_report_context
from ai_invest_agent.trading import build_trading_agent


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "generated_reports"
RESEARCH_ARCHIVE_DIR = BASE_DIR / "collected_reports"
RESEARCH_ARCHIVE_FILE = RESEARCH_ARCHIVE_DIR / "research_findings.jsonl"
MOCK_LEDGER_FILE = BASE_DIR / "mock_trading" / "orders.jsonl"
AUTO_STATE_FILE = BASE_DIR / "mock_trading" / "auto_trader_state.json"
AUTO_TRADE_INTERVAL_SEC = 8
SYMBOL_NAME_MAP = {
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "035420.KS": "NAVER",
    "068270.KS": "셀트리온",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "GOOGL": "Alphabet",
    "AMD": "AMD",
}


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
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

REACT_DIST = BASE_DIR / "static" / "dist"

app = Flask(__name__)
app.json.ensure_ascii = False


DEFAULT_FORM = {
    "asset": "10000000",
    "propensity": "중립형",
    "market": "국내",
    "duration": "중기",
    "data_source": "mock",
    "trading_mode": "mock",
}


def _react_index():
    """React 빌드가 있으면 index.html을 반환, 없으면 None."""
    index_file = REACT_DIST / "index.html"
    if index_file.exists():
        return send_file(index_file)
    return None


@app.get("/assets/<path:filename>")
def react_assets(filename: str):
    return send_from_directory(REACT_DIST / "assets", filename)


@app.get("/")
def index():
    react = _react_index()
    if react is not None:
        return react
    return render_template("index.html", form=DEFAULT_FORM, result=None, error=None)


@app.get("/mock-trading")
def mock_trading_dashboard():
    react = _react_index()
    if react is not None:
        return react
    _ensure_auto_trading_activity()
    orders = _load_mock_orders(limit=300)
    summary = _build_summary(orders)
    return render_template("mock_trading.html", orders=orders, summary=summary)


@app.get("/api/mock-trading/orders")
def mock_trading_orders_api():
    _ensure_auto_trading_activity()
    orders = _load_mock_orders(limit=300)
    return jsonify({"orders": orders, "summary": _build_summary(orders)})


@app.post("/analyze")
def analyze():
    form = _collect_form(request.form)
    try:
        result = _run_analysis(form)
    except ValueError as exc:
        return render_template("index.html", form=form, result=None, error=str(exc)), 400
    return render_template("index.html", form=form, result=result, error=None)


@app.post("/api/analyze")
def analyze_api():
    payload = request.get_json(silent=True) or {}
    form = _payload_to_form(payload)
    try:
        result = _run_analysis(form)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/execute")
def execute_api():
    payload = request.get_json(silent=True) or {}
    signals = payload.get("signals")
    if not isinstance(signals, list):
        return jsonify({"error": "signals must be a list"}), 400

    trader = build_trading_agent(broker="mock", env="demo")

    normalized_orders: list[RecommendationLike] = []
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
        return jsonify({"error": str(exc), "broker": "mock", "environment": "demo"}), 400

    _set_auto_trading_enabled(True)
    _update_auto_watch_symbols([item.symbol for item in normalized_orders if item.symbol])
    result["trading_mode"] = "mock"
    return jsonify(result)


@app.post("/api/auto-trading/stop")
def stop_auto_trading_api():
    _set_auto_trading_enabled(False)
    return jsonify({"ok": True, "auto_trading_enabled": False})


@app.get("/api/config-status")
def config_status_api():
    return jsonify(
        {
            "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "ai_default_model": os.getenv("AI_DEFAULT_MODEL", "").strip() or "gpt-4.1-mini",
            "mcp": get_mcp_config_status(),
            "pdf_export_provider": os.getenv("PDF_EXPORT_PROVIDER", "local").strip() or "local",
            "research_archive_file": str(RESEARCH_ARCHIVE_FILE),
            "research_archive_exists": RESEARCH_ARCHIVE_FILE.exists(),
            "kis_paper_ready": all(
                bool(os.getenv(key, "").strip())
                for key in ("KIS_PAPER_APP_KEY", "KIS_PAPER_APP_SECRET", "KIS_PAPER_ACCOUNT_NO")
            ),
            "kis_real_ready": all(
                bool(os.getenv(key, "").strip())
                for key in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO")
            ),
        }
    )


@app.get("/api/research-archive")
def research_archive_api():
    limit_raw = request.args.get("limit", "200").strip()
    try:
        limit = max(1, min(int(limit_raw), 1000))
    except ValueError:
        limit = 200
    if not RESEARCH_ARCHIVE_FILE.exists():
        return jsonify({"items": [], "total": 0, "archive_file": str(RESEARCH_ARCHIVE_FILE)})
    rows: list[dict] = []
    for raw_line in RESEARCH_ARCHIVE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    rows.reverse()
    sliced = rows[:limit]
    return jsonify({"items": sliced, "total": len(rows), "archive_file": str(RESEARCH_ARCHIVE_FILE)})


@app.get("/reports/<path:filename>")
def download_report(filename: str):
    report_path = REPORTS_DIR / filename
    if not report_path.exists():
        return jsonify({"error": "report not found"}), 404
    return send_file(report_path, as_attachment=True, download_name=report_path.name)


def _run_analysis(form: dict) -> dict:
    investment_request = InvestmentRequest(
        asset_krw=_parse_asset(form["asset"]),
        propensity=form["propensity"],
        market=form["market"],
        duration=form["duration"],
    )

    provider = MockMarketDataProvider()
    snapshots = provider.list_candidates(investment_request.market)
    recommendations = build_recommendations(investment_request, snapshots)

    result = build_report_context(
        investment_request,
        recommendations,
        snapshots,
        data_source="mock",
        provider_warning=None,
    )
    try:
        multi_agent = run_multi_agent_analysis(investment_request, recommendations, snapshots)
        result["multi_agent"] = asdict(multi_agent)
        result["multi_agent_report"] = multi_agent.markdown_report
        _archive_research_findings(investment_request, multi_agent)
    except Exception as exc:
        result["multi_agent_error"] = str(exc)
    pdf_path = _write_pdf_report(result["markdown_report"], result.get("html_report"))
    result["trading_mode"] = "mock"
    return attach_artifacts(result, pdf_path=pdf_path, execution_result=None)


def _write_pdf_report(report_text: str, html_report: str | None = None) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    output_path = REPORTS_DIR / f"investment_report_{timestamp}.pdf"
    export_report(report_text, output_path, html_document=html_report)
    return output_path


def _archive_research_findings(request: InvestmentRequest, analysis: MultiAgentAnalysis) -> None:
    captured_at = datetime.now(timezone.utc).isoformat()
    rows: list[str] = []
    for finding in analysis.research:
        payload = {
            "captured_at": captured_at,
            "market": request.market,
            "duration": request.duration,
            "propensity": request.propensity,
            "symbol": finding.symbol,
            "name": finding.name,
            "facts": finding.facts,
            "negative_news_flags": finding.negative_news_flags,
            "sources": finding.sources,
            "source": finding.source,
        }
        rows.append(json.dumps(payload, ensure_ascii=False))
    if not rows:
        return
    with RESEARCH_ARCHIVE_FILE.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(rows) + "\n")


def _collect_form(source) -> dict:
    return {
        "asset": source.get("asset", DEFAULT_FORM["asset"]).strip(),
        "propensity": source.get("propensity", DEFAULT_FORM["propensity"]).strip(),
        "market": source.get("market", DEFAULT_FORM["market"]).strip(),
        "duration": source.get("duration", DEFAULT_FORM["duration"]).strip(),
        "data_source": "mock",
        "trading_mode": "mock",
    }


def _payload_to_form(payload: dict) -> dict:
    return {
        "asset": str(payload.get("asset", DEFAULT_FORM["asset"])).strip(),
        "propensity": str(payload.get("propensity", DEFAULT_FORM["propensity"])).strip(),
        "market": str(payload.get("market", DEFAULT_FORM["market"])).strip(),
        "duration": str(payload.get("duration", DEFAULT_FORM["duration"])).strip(),
        "data_source": "mock",
        "trading_mode": "mock",
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


def _load_mock_orders(limit: int = 300) -> list[dict]:
    if not MOCK_LEDGER_FILE.exists():
        return []
    raw_rows: list[dict] = []
    for raw_line in MOCK_LEDGER_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            raw_rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    raw_rows.reverse()
    now = datetime.now(timezone.utc)
    return [_simulate_live_order(row, now=now) for row in raw_rows[:limit]]


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _stable_fill_delta(symbol: str, created_at: str) -> float:
    digest = hashlib.sha256(f"{symbol}|{created_at}".encode("utf-8")).digest()
    ratio = int.from_bytes(digest[:2], "big") / 65535
    return (ratio - 0.5) * 0.03


def _simulate_live_order(order: dict, now: datetime) -> dict:
    simulated = dict(order)
    created_at = _parse_iso_utc(str(order.get("created_at", "")).strip())
    qty = int(order.get("quantity", 0) or 0)
    entry_price = float(order.get("entry_price", 0) or 0)
    action = str(order.get("action", "")).upper()
    symbol = str(order.get("symbol", ""))
    seed = str(order.get("created_at", ""))
    delta = _stable_fill_delta(symbol, seed)
    simulated["symbol_name"] = _symbol_to_name(symbol)

    if created_at is None:
        simulated["status"] = str(order.get("status", "submitted")).lower()
        simulated["progress_pct"] = 100 if simulated["status"] == "filled" else 0
        simulated["elapsed_sec"] = 0
        simulated["filled_quantity"] = qty if simulated["status"] == "filled" else 0
        simulated["remaining_quantity"] = 0 if simulated["status"] == "filled" else qty
        simulated["fill_price"] = entry_price if entry_price else None
        simulated["mark_price"] = entry_price if entry_price else None
        simulated["pnl_amount"] = 0.0
        return simulated

    elapsed_sec = max(0, int((now - created_at).total_seconds()))
    fill_price = round(entry_price * (1 + delta), 2) if entry_price else None

    if elapsed_sec < 3:
        status = "queued"
        progress = 5
        filled_qty = 0
    elif elapsed_sec < 8:
        status = "sent"
        progress = 30
        filled_qty = 0
    elif elapsed_sec < 15:
        status = "accepted"
        progress = 55
        filled_qty = max(1, int(qty * 0.2)) if qty else 0
    elif elapsed_sec < 25:
        status = "partial_fill"
        progress = 80
        filled_qty = max(1, int(qty * 0.7)) if qty else 0
    else:
        status = "filled"
        progress = 100
        filled_qty = qty

    simulated["status"] = status
    simulated["progress_pct"] = progress
    simulated["elapsed_sec"] = elapsed_sec
    simulated["filled_quantity"] = filled_qty
    simulated["remaining_quantity"] = max(0, qty - filled_qty)
    simulated["fill_price"] = fill_price

    phase = int.from_bytes(
        hashlib.sha256(f"{symbol}|{seed}|phase".encode("utf-8")).digest()[:2],
        "big",
    )
    wave = math.sin((now.timestamp() + phase) / 8.0) * 0.012
    mark_price = None
    if fill_price:
        mark_price = round(max(0.01, fill_price * (1 + wave)), 2)
    elif entry_price:
        mark_price = round(max(0.01, entry_price * (1 + wave)), 2)
    simulated["mark_price"] = mark_price

    if mark_price is not None and fill_price is not None:
        if action == "SELL":
            pnl_amount = (fill_price - mark_price) * filled_qty
        else:
            pnl_amount = (mark_price - fill_price) * filled_qty
        simulated["pnl_amount"] = round(pnl_amount, 2)
    else:
        simulated["pnl_amount"] = 0.0

    simulated["action"] = action
    return simulated


def _build_summary(orders: list[dict]) -> dict:
    buy_count = sum(1 for order in orders if str(order.get("action", "")).upper() == "BUY")
    sell_count = sum(1 for order in orders if str(order.get("action", "")).upper() == "SELL")
    filled_count = sum(1 for order in orders if order.get("status") == "filled")
    total_pnl = round(sum(float(order.get("pnl_amount", 0) or 0) for order in orders), 2)
    return {
        "mode": "mock",
        "total": len(orders),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "filled_count": filled_count,
        "total_pnl": total_pnl,
        "ledger_file": str(MOCK_LEDGER_FILE),
    }


def _load_auto_state() -> dict:
    if not AUTO_STATE_FILE.exists():
        return {
            "enabled": False,
            "last_generated_at": None,
            "sequence": 0,
            "holdings": {},
            "watch_symbols": ["005930.KS", "000660.KS", "035420.KS"],
        }
    try:
        data = json.loads(AUTO_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid auto state")
        data.setdefault("enabled", False)
        data.setdefault("last_generated_at", None)
        data.setdefault("sequence", 0)
        data.setdefault("holdings", {})
        data.setdefault("watch_symbols", ["005930.KS", "000660.KS", "035420.KS"])
        return data
    except Exception:
        return {
            "enabled": False,
            "last_generated_at": None,
            "sequence": 0,
            "holdings": {},
            "watch_symbols": ["005930.KS", "000660.KS", "035420.KS"],
        }


def _save_auto_state(state: dict) -> None:
    AUTO_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _set_auto_trading_enabled(enabled: bool) -> None:
    state = _load_auto_state()
    state["enabled"] = bool(enabled)
    _save_auto_state(state)


def _update_auto_watch_symbols(symbols: list[str]) -> None:
    cleaned = [item.strip() for item in symbols if item and item.strip()]
    if not cleaned:
        return
    state = _load_auto_state()
    existing = [str(item).strip() for item in state.get("watch_symbols", []) if str(item).strip()]
    merged: list[str] = []
    for symbol in cleaned + existing:
        if symbol not in merged:
            merged.append(symbol)
    state["watch_symbols"] = merged[:10]
    _save_auto_state(state)


def _symbol_base_price(symbol: str) -> float:
    if symbol.endswith(".KS"):
        if symbol == "005930.KS":
            return 84000.0
        if symbol == "000660.KS":
            return 196000.0
        if symbol == "035420.KS":
            return 223000.0
        return 120000.0
    if symbol == "MSFT":
        return 470.0
    if symbol == "NVDA":
        return 990.0
    if symbol == "GOOGL":
        return 183.0
    return 200.0


def _symbol_to_name(symbol: str) -> str:
    return SYMBOL_NAME_MAP.get(symbol, symbol)


def _append_mock_order(order: dict) -> None:
    MOCK_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MOCK_LEDGER_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(order, ensure_ascii=False) + "\n")


def _ensure_auto_trading_activity() -> None:
    state = _load_auto_state()
    if not state.get("enabled"):
        return

    now = datetime.now(timezone.utc)
    last_generated = _parse_iso_utc(str(state.get("last_generated_at", "")).strip())
    if last_generated is None:
        cycles = 1
    else:
        elapsed = int((now - last_generated).total_seconds())
        if elapsed < AUTO_TRADE_INTERVAL_SEC:
            return
        cycles = max(1, min(3, elapsed // AUTO_TRADE_INTERVAL_SEC))

    watch_symbols = [str(s).strip() for s in state.get("watch_symbols", []) if str(s).strip()]
    if not watch_symbols:
        watch_symbols = ["005930.KS", "000660.KS", "035420.KS"]

    holdings = state.get("holdings", {})
    if not isinstance(holdings, dict):
        holdings = {}

    sequence = int(state.get("sequence", 0) or 0)
    anchor_ts = now.timestamp()

    for cycle_index in range(cycles):
        idx = (sequence + cycle_index) % len(watch_symbols)
        symbol = watch_symbols[idx]
        owned_qty = int(holdings.get(symbol, 0) or 0)
        planned_qty = 5 + ((sequence + cycle_index) % 6) * 2

        if owned_qty > 0 and (sequence + cycle_index) % 2 == 1:
            action = "SELL"
            qty = min(owned_qty, planned_qty)
        else:
            action = "BUY"
            qty = planned_qty

        if qty <= 0:
            continue

        base = _symbol_base_price(symbol)
        wave = math.sin((anchor_ts + (sequence + cycle_index) * 17) / 31.0) * 0.025
        entry_price = round(max(0.01, base * (1 + wave)), 2)
        if action == "BUY":
            target_price = round(entry_price * 1.08, 2)
            stop_loss_price = round(entry_price * 0.96, 2)
            holdings[symbol] = owned_qty + qty
            rationale = f"자동 모의매매: {symbol} 추세 관찰 후 분할 매수"
        else:
            target_price = round(entry_price * 0.95, 2)
            stop_loss_price = round(entry_price * 1.03, 2)
            holdings[symbol] = max(0, owned_qty - qty)
            rationale = f"자동 모의매매: {symbol} 보유분 분할 매도"

        order_time = now if cycles == 1 else now.replace(microsecond=max(0, now.microsecond - cycle_index * 1000))
        _append_mock_order(
            {
                "symbol": symbol,
                "action": action,
                "quantity": qty,
                "entry_price": entry_price,
                "target_price": target_price,
                "stop_loss_price": stop_loss_price,
                "rationale": rationale,
                "created_at": order_time.isoformat(),
                "status": "submitted",
            }
        )

    state["holdings"] = holdings
    state["sequence"] = sequence + cycles
    state["last_generated_at"] = now.isoformat()
    _save_auto_state(state)


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
    port = int(os.getenv("PORT", "5000").strip() or "5000")
    app.run(host="0.0.0.0", port=port, debug=True)
