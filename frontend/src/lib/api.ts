// In development, Vite proxies /api and /reports to localhost:5000.
// Set VITE_API_BASE_URL in .env to point to a remote server in production.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export { BASE_URL };

export interface AnalyzeRequest {
  asset: string;
  propensity: "안정추구형" | "중립형" | "공격투자형";
  market: "국내" | "미국";
  duration: "단기" | "중기" | "장기";
}

export interface FinancialMetrics {
  eps: string | number;
  per: string | number;
  roe: string | number;
  bps: string | number;
  pbr: string | number;
}

export interface StockRow {
  name: string;
  symbol: string;
  current_price: string | number;
  rationale: string;
  metrics: string;
  risk_level: string;
  financial_metrics: FinancialMetrics;
}

export interface MetricChart {
  title: string;
  svg: string;
}

export interface Signal {
  symbol: string;
  action: string;
  pretty_json: string;
}

export interface PdfReport {
  file_name: string;
}

export interface AnalyzeResponse {
  request: {
    asset_label: string;
    propensity: string;
    market: string;
    duration: string;
  };
  data_source_label: string;
  summary: string;
  generated_from: string;
  pdf_report?: PdfReport;
  rows: StockRow[];
  metric_charts: MetricChart[];
  signals: Signal[];
  error?: string;
}

export interface Order {
  created_at: string;
  symbol_name: string;
  symbol: string;
  action: string;
  quantity: number;
  status: string;
  progress_pct: number;
  filled_quantity: number;
  remaining_quantity: number;
  fill_price: number | null;
  mark_price: number | null;
  pnl_amount: number;
  rationale: string;
}

export interface TradingSummary {
  total: number;
  buy_count: number;
  sell_count: number;
  filled_count: number;
  total_pnl: number;
}

export interface TradingOrdersResponse {
  orders: Order[];
  summary: TradingSummary;
}

export async function analyzeInvestment(data: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? `분석 실패 (${res.status})`);
  }
  return res.json();
}

export async function executeSignals(signals: object[]): Promise<{ executed_count: number }> {
  const res = await fetch(`${BASE_URL}/api/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ signals, trading_mode: "mock" }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error ?? "투자 실행 실패");
  return body;
}

export async function fetchTradingOrders(): Promise<TradingOrdersResponse> {
  const res = await fetch(`${BASE_URL}/api/mock-trading/orders`);
  if (!res.ok) throw new Error("주문 조회 실패");
  return res.json();
}

export async function stopAutoTrading(): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/auto-trading/stop`, { method: "POST" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || !(body as { ok?: boolean }).ok) {
    throw new Error((body as { error?: string }).error ?? "자동매매 중지 실패");
  }
}
