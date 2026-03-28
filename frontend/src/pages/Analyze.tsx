import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Download, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";

import { analyzeInvestment, executeSignals, BASE_URL, type AnalyzeResponse } from "@/lib/api";

const schema = z.object({
  asset: z.string().min(1, "자산을 입력하세요"),
  propensity: z.enum(["안정추구형", "중립형", "공격투자형"]),
  market: z.enum(["국내", "미국"]),
  duration: z.enum(["단기", "중기", "장기"]),
});

type FormValues = Required<z.infer<typeof schema>>;

const riskColor: Record<string, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
};

export default function Analyze() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [tradeStatus, setTradeStatus] = useState("");
  const { toast } = useToast();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      asset: "10,000,000",
      propensity: "중립형",
      market: "국내",
      duration: "중기",
    },
  });

  async function onSubmit(values: FormValues) {
    setLoading(true);
    setResult(null);
    setTradeStatus("");
    try {
      const data = await analyzeInvestment(values);
      setResult(data);
    } catch (err) {
      toast({
        title: "분석 실패",
        description: err instanceof Error ? err.message : "오류가 발생했습니다.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleStartInvest() {
    if (!result?.signals?.length) return;
    setExecuting(true);
    setTradeStatus("모의투자를 시작하는 중입니다...");
    try {
      const signals = result.signals
        .map((s) => {
          try {
            return JSON.parse(s.pretty_json);
          } catch {
            return null;
          }
        })
        .filter(Boolean);
      const body = await executeSignals(signals);
      setTradeStatus(`실행 완료: ${body.executed_count ?? 0}건`);
      window.open("/mock-trading", "_blank");
    } catch (err) {
      setTradeStatus(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-6 py-8">
          <div className="flex items-stretch gap-4">
            <img
              src="/imgicon/jjoayo.png"
              alt="logo"
              className="h-full w-auto max-w-[96px] shrink-0 object-contain"
            />
            <div className="min-w-0">
              <p className="text-sm font-medium text-primary mb-1">Stock Portfolio Korea Investment</p>
              <h1 className="font-display text-3xl font-bold text-charcoal">모의 데이터 기반 SPKI 투자 대시보드</h1>
              <p className="mt-2 text-warm-gray w-full">
                실제 시세 API 없이 모의 데이터를 사용합니다.
                <br />
                분석 결과를 확인한 뒤 투자 시작 버튼을 누르면 자동 주문이 실행되고, 실시간 모의 매수/매도 현황 페이지가 열립니다.
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8 flex flex-col lg:flex-row gap-8 items-start">
        {/* Sidebar Form */}
        <aside className="w-full lg:w-80 shrink-0 lg:sticky lg:top-6">
          <Card>
            <CardHeader>
              <p className="text-xs font-semibold text-primary uppercase tracking-wider">Input</p>
              <CardTitle className="text-xl">투자 조건</CardTitle>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="asset"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>자산 (KRW)</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="10000000"
                            inputMode="numeric"
                            value={field.value}
                            onChange={(event) => {
                              const digits = event.target.value.replace(/[^\d]/g, "");
                              const formatted = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                              field.onChange(formatted);
                            }}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="propensity"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>투자 성향</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {(["안정추구형", "중립형", "공격투자형"] as const).map((o) => (
                              <SelectItem key={o} value={o}>
                                {o}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="market"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>시장</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {(["국내", "미국"] as const).map((o) => (
                              <SelectItem key={o} value={o}>
                                {o}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="duration"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>투자 기간</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {(["단기", "중기", "장기"] as const).map((o) => (
                              <SelectItem key={o} value={o}>
                                {o}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormItem>
                    )}
                  />

                  {result?.signals?.length ? (
                    <>
                      <Button
                        type="button"
                        className="w-full"
                        onClick={handleStartInvest}
                        disabled={executing}
                      >
                        {executing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        투자 시작
                      </Button>
                      <Button
                        type="submit"
                        variant="outline"
                        className="w-full"
                        disabled={loading}
                      >
                        재분석
                      </Button>
                      {tradeStatus && (
                        <p className="text-sm text-warm-gray">{tradeStatus}</p>
                      )}
                    </>
                  ) : (
                    <Button type="submit" className="w-full" disabled={loading}>
                      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      분석 시작
                    </Button>
                  )}
                </form>
              </Form>
            </CardContent>
          </Card>
        </aside>

        {/* Results Area */}
        <main className="flex-1 min-w-0 space-y-6">
          {!result && !loading && (
            <Card className="text-center py-16">
              <CardContent>
                <TrendingUp className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-sm font-medium text-primary mb-2">Ready</p>
                <h2 className="font-display text-xl font-semibold text-charcoal">
                  조건을 입력하면 분석 결과가 표시됩니다.
                </h2>
              </CardContent>
            </Card>
          )}

          {loading && (
            <Card className="text-center py-16">
              <CardContent>
                <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary mb-4" />
                <p className="text-warm-gray">AI가 투자를 분석하는 중입니다...</p>
              </CardContent>
            </Card>
          )}

          {result && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <p className="text-xs font-semibold text-primary uppercase tracking-wider">#1</p>
                  <CardTitle>분석 요약</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {[
                      result.request?.asset_label,
                      result.request?.propensity,
                      result.request?.market,
                      result.request?.duration,
                      result.data_source_label,
                    ]
                      .filter(Boolean)
                      .map((tag, i) => (
                        <Badge key={i} variant="secondary">
                          {tag}
                        </Badge>
                      ))}
                  </div>
                  <p className="text-warm-gray leading-relaxed">{result.summary}</p>
                  <p className="text-sm text-muted-foreground">기준 시각: {result.generated_from}</p>
                  {result.pdf_report && (
                    <a
                      href={`${BASE_URL}/reports/${result.pdf_report.file_name}`}
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      <Download className="h-4 w-4" />
                      PDF 다운로드
                    </a>
                  )}
                </CardContent>
              </Card>

              {result.rows?.length > 0 && (
                <Card>
                  <CardHeader>
                    <p className="text-xs font-semibold text-primary uppercase tracking-wider">#2</p>
                    <CardTitle>추천 종목</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>종목</TableHead>
                            <TableHead>현재가</TableHead>
                            <TableHead>추천 이유</TableHead>
                            <TableHead>핵심 지표</TableHead>
                            <TableHead>위험도</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {result.rows.map((row, i) => (
                            <TableRow key={i}>
                              <TableCell>
                                <div className="font-semibold whitespace-nowrap">{row.name}</div>
                                <div className="text-xs text-muted-foreground">{row.symbol}</div>
                              </TableCell>
                              <TableCell className="whitespace-nowrap">{row.current_price}</TableCell>
                              <TableCell className="text-sm max-w-48">{row.rationale}</TableCell>
                              <TableCell className="text-sm">{row.metrics}</TableCell>
                              <TableCell>
                                <span
                                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                                    riskColor[row.risk_level?.toLowerCase()] ?? "bg-gray-100 text-gray-800"
                                  }`}
                                >
                                  {row.risk_level}
                                </span>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              )}

                {result.metric_charts?.length > 0 && (
                  <Card>
                    <CardHeader>
                      <p className="text-xs font-semibold text-primary uppercase tracking-wider">#3</p>
                      <CardTitle>재무 지표 그래프</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {result.metric_charts.map((chart, i) => (
                          <div key={i} className="border rounded-lg p-4">
                            <h3 className="font-medium text-charcoal mb-3 text-sm">{chart.title}</h3>
                            <div
                              className="overflow-x-auto"
                              dangerouslySetInnerHTML={{ __html: chart.svg }}
                            />
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {result.rows?.length > 0 && (
                  <Card>
                    <CardHeader>
                      <p className="text-xs font-semibold text-primary uppercase tracking-wider">#4</p>
                      <CardTitle>재무 지표 비교 표</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>종목</TableHead>
                              <TableHead>EPS</TableHead>
                              <TableHead>PER</TableHead>
                              <TableHead>ROE</TableHead>
                              <TableHead>BPS</TableHead>
                              <TableHead>PBR</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {result.rows.map((row, i) => (
                              <TableRow key={i}>
                                <TableCell>
                                  <div className="font-semibold whitespace-nowrap">{row.name}</div>
                                  <div className="text-xs text-muted-foreground">{row.symbol}</div>
                                </TableCell>
                                <TableCell>{row.financial_metrics?.eps}</TableCell>
                                <TableCell>{row.financial_metrics?.per}</TableCell>
                                <TableCell>{row.financial_metrics?.roe}</TableCell>
                                <TableCell>{row.financial_metrics?.bps}</TableCell>
                                <TableCell>{row.financial_metrics?.pbr}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
