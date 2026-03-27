from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol

from ai_invest_agent.kis_adapter import KisApiClient, infer_overseas_exchange
from ai_invest_agent.models import Recommendation


class RecommendationLike(Protocol):
    symbol: str
    signal_action: str
    quantity: int
    entry_price: float | None
    target_price: float | None
    stop_loss_price: float | None
    rationale: str


@dataclass(frozen=True)
class PaperTradeOrder:
    symbol: str
    action: str
    quantity: int
    entry_price: float | None
    target_price: float | None
    stop_loss_price: float | None
    rationale: str
    created_at: str
    status: str


class MockTradingAgent:
    broker_name = "local-paper-broker"

    def __init__(self, ledger_dir: Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.ledger_dir = ledger_dir or (base_dir / "mock_trading")
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.ledger_dir / "orders.jsonl"

    def execute_recommendations(
        self,
        recommendations: Iterable[RecommendationLike],
        max_orders: int = 3,
    ) -> dict:
        recommendation_list = list(recommendations)
        executed: list[dict] = []
        skipped: list[dict] = []
        executed_symbols: set[str] = set()

        for item in recommendation_list:
            if item.signal_action != "BUY":
                skipped.append({"symbol": item.symbol, "reason": f"signal={item.signal_action}"})
                continue
            if item.quantity <= 0:
                skipped.append({"symbol": item.symbol, "reason": "quantity=0"})
                continue
            if len(executed) >= max_orders:
                skipped.append({"symbol": item.symbol, "reason": "max_orders_reached"})
                continue

            order = PaperTradeOrder(
                symbol=item.symbol,
                action=item.signal_action,
                quantity=item.quantity,
                entry_price=item.entry_price,
                target_price=item.target_price,
                stop_loss_price=item.stop_loss_price,
                rationale=item.rationale,
                created_at=datetime.now(timezone.utc).isoformat(),
                status="submitted",
            )
            serialized = asdict(order)
            self._append_order(serialized)
            executed.append(serialized)
            executed_symbols.add(item.symbol)

        return {
            "broker": self.broker_name,
            "ledger_file": str(self.ledger_file),
            "executed_count": len(executed),
            "executed_orders": executed,
            "skipped_orders": skipped,
            "executed_symbols": sorted(executed_symbols),
        }

    def _append_order(self, order: dict) -> None:
        with self.ledger_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(order, ensure_ascii=False) + "\n")


class KisTradingAgent:
    broker_name = "koreainvestment-openapi"

    def __init__(self, env: str = "demo", ledger_dir: Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.ledger_dir = ledger_dir or (base_dir / "kis_trading")
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.ledger_dir / f"orders_{env}.jsonl"
        self.client = KisApiClient(env=env)
        self.env = env

    @staticmethod
    def is_available(env: str = "demo") -> bool:
        return KisApiClient.is_configured(env)

    def execute_recommendations(
        self,
        recommendations: Iterable[RecommendationLike],
        max_orders: int = 3,
    ) -> dict:
        recommendation_list = list(recommendations)
        executed: list[dict] = []
        skipped: list[dict] = []

        for item in recommendation_list:
            if item.signal_action != "BUY":
                skipped.append({"symbol": item.symbol, "reason": f"signal={item.signal_action}"})
                continue
            if item.quantity <= 0:
                skipped.append({"symbol": item.symbol, "reason": "quantity=0"})
                continue
            if len(executed) >= max_orders:
                skipped.append({"symbol": item.symbol, "reason": "max_orders_reached"})
                continue
            if item.entry_price is None:
                skipped.append({"symbol": item.symbol, "reason": "entry_price_missing"})
                continue

            order_result = self._submit_order(item)
            serialized = {
                "symbol": item.symbol,
                "action": item.signal_action,
                "quantity": item.quantity,
                "entry_price": item.entry_price,
                "target_price": item.target_price,
                "stop_loss_price": item.stop_loss_price,
                "rationale": item.rationale,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "submitted",
                "broker_response": order_result,
            }
            self._append_order(serialized)
            executed.append(serialized)

        return {
            "broker": self.broker_name,
            "environment": self.env,
            "ledger_file": str(self.ledger_file),
            "executed_count": len(executed),
            "executed_orders": executed,
            "skipped_orders": skipped,
            "executed_symbols": sorted([item["symbol"] for item in executed]),
        }

    def _submit_order(self, item: RecommendationLike) -> dict:
        if item.symbol.endswith(".KS"):
            return self.client.order_domestic(
                symbol=item.symbol.replace(".KS", ""),
                side="buy",
                quantity=item.quantity,
                price=item.entry_price or 0.0,
            )
        return self.client.order_overseas(
            symbol=item.symbol,
            side="buy",
            quantity=item.quantity,
            price=item.entry_price or 0.0,
            exchange_code=infer_overseas_exchange(item.symbol),
        )

    def _append_order(self, order: dict) -> None:
        with self.ledger_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(order, ensure_ascii=False) + "\n")


def build_trading_agent(broker: str = "auto", env: str = "demo") -> MockTradingAgent | KisTradingAgent:
    broker_key = broker.strip().lower()
    if broker_key == "kis":
        return KisTradingAgent(env=env)
    if broker_key == "mock":
        return MockTradingAgent()
    if KisTradingAgent.is_available(env=env):
        return KisTradingAgent(env=env)
    return MockTradingAgent()
