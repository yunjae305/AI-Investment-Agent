import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { fetchTradingOrders, stopAutoTrading, resumeAutoTrading, fetchTradingStatus, type Order, type TradingSummary } from "@/lib/api";

const statusStyle: Record<string, string> = {
  queued: "bg-gray-100 text-gray-700",
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-indigo-100 text-indigo-700",
  partial_fill: "bg-yellow-100 text-yellow-800",
  filled: "bg-green-100 text-green-800",
};

const statusLabel: Record<string, string> = {
  queued: "대기",
  sent: "전송됨",
  accepted: "접수",
  partial_fill: "부분 체결",
  filled: "체결 완료",
};

const defaultSummary: TradingSummary = {
  total: 0,
  buy_count: 0,
  sell_count: 0,
  filled_count: 0,
  total_pnl: 0,
};

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function formatKst(isoString: string) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const kstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
  return `${kstDate.getUTCFullYear()}-${pad2(kstDate.getUTCMonth() + 1)}-${pad2(kstDate.getUTCDate())} ${pad2(
    kstDate.getUTCHours(),
  )}:${pad2(kstDate.getUTCMinutes())}`;
}

function humanizeRationale(order: Order) {
  const symbol = (order.symbol ?? "").trim();
  const symbolName = (order.symbol_name ?? "").trim();
  const action = (order.action ?? "").trim().toUpperCase();

  const fallback =
    symbolName || symbol
      ? `${symbolName || symbol} ${action === "BUY" ? "매수" : action === "SELL" ? "매도" : "관망"} 신호`
      : "자동매매 신호";

  let text = (order.rationale ?? "").trim();
  if (!text) return fallback;

  text = text.replace(/^자동\s*모의매매\s*:\s*/u, "자동매매: ");
  if (symbol) {
    const replacement = symbolName ? `${symbolName}(${symbol})` : symbol;
    text = text.split(symbol).join(replacement);
  }
  return text;
}

export default function Trading() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [summary, setSummary] = useState<TradingSummary>(defaultSummary);
  const [isTrading, setIsTrading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    try {
      const data = await fetchTradingOrders();
      setOrders(data.orders);
      setSummary(data.summary);
    } catch {
      // keep-alive: polling continues silently on error
    }
  };

  useEffect(() => {
    fetchTradingStatus().then((s) => setIsTrading(s.auto_trading_enabled)).catch(() => {});
    refresh();
    intervalRef.current = setInterval(refresh, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleStop = async () => {
    setActionLoading(true);
    setStatusMsg("자동매매 중지 요청 중...");
    try {
      await stopAutoTrading();
      setIsTrading(false);
      setStatusMsg("자동매매가 중지되었습니다.");
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : "중지 중 오류가 발생했습니다.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    setStatusMsg("자동매매 재개 요청 중...");
    try {
      await resumeAutoTrading();
      setIsTrading(true);
      setStatusMsg("자동매매가 재개되었습니다.");
    } catch (err) {
      setStatusMsg(err instanceof Error ? err.message : "재개 중 오류가 발생했습니다.");
    } finally {
      setActionLoading(false);
    }
  };

  const pnlBase = orders.reduce((acc, order) => {
    const fillPrice = typeof order.fill_price === "number" ? order.fill_price : 0;
    const filledQty = typeof order.filled_quantity === "number" ? order.filled_quantity : 0;
    if (!fillPrice || !filledQty) return acc;
    return acc + Math.abs(fillPrice) * Math.abs(filledQty);
  }, 0);
  const pnlPct = pnlBase > 0 ? (summary.total_pnl / pnlBase) * 100 : 0;
  const pnlPctRounded = Number(pnlPct.toFixed(2));
  const characterSrc =
    pnlPctRounded <= -10
      ? "/imgicon/ggang.png"
      : pnlPctRounded < 0
        ? "/imgicon/heeng.png"
        : pnlPctRounded === 0
          ? "/imgicon/yolsimehat.png"
          : "/imgicon/jjoayo.png";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-8 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div>
            <p className="text-sm font-medium text-primary mb-1">SPKI Trading Dashboard</p>
            <h1 className="font-display text-3xl font-bold text-charcoal">모의 매수/매도 현황</h1>
            <p className="mt-2 text-warm-gray max-w-xl">
              주문을 기준으로 최근 모의 거래 내역과 체결 진행률, 실시간 손익을 표시합니다.
            </p>
          </div>

          <div className="flex items-stretch gap-4 shrink-0 w-full max-w-xl">
            <img
              src={characterSrc}
              alt="character"
              className="hidden sm:block h-full w-1/2 object-contain"
            />
            <Card className="w-full sm:w-1/2">
              <CardHeader className="pb-2">
                <p className="text-xs font-semibold text-primary uppercase tracking-wider">Summary</p>
              </CardHeader>
              <CardContent className="space-y-1.5 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-warm-gray">전체 주문</span>
                  <span className="font-semibold">{summary.total}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-warm-gray">매수</span>
                  <span className="font-semibold">{summary.buy_count}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-warm-gray">매도</span>
                  <span className="font-semibold">{summary.sell_count}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-warm-gray">체결 완료</span>
                  <span className="font-semibold">{summary.filled_count}</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-warm-gray">실시간 평가손익</span>
                  <span
                    className={`font-semibold ${
                      summary.total_pnl >= 0 ? "text-green-600" : "text-red-600"
                    }`}
                  >
                  {summary.total_pnl.toFixed(2)} ({pnlPctRounded.toFixed(2)}%)
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-primary uppercase tracking-wider">Live</p>
                <CardTitle>주문 내역</CardTitle>
              </div>
              <div className="flex items-center gap-3">
                {isTrading ? (
                  <Button variant="outline" onClick={handleStop} disabled={actionLoading}>
                    {actionLoading ? "중지 중..." : "자동매매 중지"}
                  </Button>
                ) : (
                  <Button variant="default" onClick={handleResume} disabled={actionLoading}>
                    {actionLoading ? "재개 중..." : "매매 재개"}
                  </Button>
                )}
                {statusMsg && <span className="text-sm text-warm-gray">{statusMsg}</span>}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="whitespace-nowrap">시간(KST)</TableHead>
                    <TableHead>종목</TableHead>
                    <TableHead>액션</TableHead>
                    <TableHead>수량</TableHead>
                    <TableHead>상태</TableHead>
                    <TableHead className="whitespace-nowrap">체결률</TableHead>
                    <TableHead className="whitespace-nowrap">체결수량</TableHead>
                    <TableHead>잔량</TableHead>
                    <TableHead>체결가</TableHead>
                    <TableHead>현재가</TableHead>
                    <TableHead>손익</TableHead>
                    <TableHead>사유</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orders.map((order, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatKst(order.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold whitespace-nowrap">{order.symbol_name}</div>
                        <div className="text-xs text-muted-foreground">{order.symbol}</div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={order.action === "BUY" ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {order.action}
                        </Badge>
                      </TableCell>
                      <TableCell>{order.quantity}</TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                            statusStyle[order.status] ?? "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {statusLabel[order.status] ?? order.status}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Progress value={order.progress_pct} className="h-1.5 w-16 mb-1" />
                        <span className="text-xs text-muted-foreground">{order.progress_pct}%</span>
                      </TableCell>
                      <TableCell>{order.filled_quantity}</TableCell>
                      <TableCell>{order.remaining_quantity}</TableCell>
                      <TableCell className="whitespace-nowrap">{order.fill_price ?? "-"}</TableCell>
                      <TableCell className="whitespace-nowrap">{order.mark_price ?? "-"}</TableCell>
                      <TableCell
                        className={`font-medium whitespace-nowrap ${
                          order.pnl_amount >= 0 ? "text-green-600" : "text-red-600"
                        }`}
                      >
                        {order.pnl_amount.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-sm max-w-40">
                        <span className="line-clamp-2">{humanizeRationale(order)}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {orders.length === 0 && (
                <div className="text-center py-12 text-warm-gray">아직 주문이 없습니다.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
