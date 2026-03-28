import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { fetchTradingOrders, stopAutoTrading, type Order, type TradingSummary } from "@/lib/api";

const statusStyle: Record<string, string> = {
  queued: "bg-gray-100 text-gray-700",
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-indigo-100 text-indigo-700",
  partial_fill: "bg-yellow-100 text-yellow-800",
  filled: "bg-green-100 text-green-800",
};

const defaultSummary: TradingSummary = {
  total: 0,
  buy_count: 0,
  sell_count: 0,
  filled_count: 0,
  total_pnl: 0,
};

export default function Trading() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [summary, setSummary] = useState<TradingSummary>(defaultSummary);
  const [stopping, setStopping] = useState(false);
  const [stopStatus, setStopStatus] = useState("");
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
    refresh();
    intervalRef.current = setInterval(refresh, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleStop = async () => {
    setStopping(true);
    setStopStatus("자동매매 중지 요청 중...");
    try {
      await stopAutoTrading();
      setStopStatus("자동매매가 중지되었습니다.");
    } catch (err) {
      setStopStatus(err instanceof Error ? err.message : "중지 중 오류가 발생했습니다.");
      setStopping(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-8 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div>
            <p className="text-sm font-medium text-primary mb-1">Mock Trading Dashboard</p>
            <h1 className="font-display text-3xl font-bold text-charcoal">모의 매수/매도 현황</h1>
            <p className="mt-2 text-warm-gray max-w-xl">
              주문 원장을 기준으로 최근 모의 거래 내역과 체결 진행률, 실시간 손익을 표시합니다.
            </p>
          </div>

          <Card className="min-w-56 shrink-0">
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
                  {summary.total_pnl.toFixed(2)}
                </span>
              </div>
            </CardContent>
          </Card>
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
                <Button variant="outline" onClick={handleStop} disabled={stopping}>
                  {stopping ? "중지 중..." : "자동매매 중지"}
                </Button>
                {stopStatus && <span className="text-sm text-warm-gray">{stopStatus}</span>}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="whitespace-nowrap">시간(UTC)</TableHead>
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
                        {order.created_at}
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
                          {order.status}
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
                        <span className="line-clamp-2">{order.rationale}</span>
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
