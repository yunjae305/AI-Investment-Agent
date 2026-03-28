import { Brain, BarChart3, ShieldCheck, Clock, Wallet, LineChart } from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "SPKI 시장 분석",
    description: "딥러닝 기반으로 실시간 시장 데이터를 분석하여 최적의 투자 타이밍을 포착합니다.",
  },
  {
    icon: BarChart3,
    title: "자동 포트폴리오",
    description: "사용자의 투자 성향에 맞춰 SPKI가 자동으로 분산 투자 포트폴리오를 구성합니다.",
  },
  {
    icon: ShieldCheck,
    title: "리스크 관리",
    description: "변동성을 실시간 모니터링하고 자동 손절/익절로 자산을 보호합니다.",
  },
  {
    icon: Clock,
    title: "24/7 자동 매매",
    description: "SPKI가 쉬지 않고 시장을 감시하며 최적의 시점에 자동 매매합니다.",
  },
  {
    icon: Wallet,
    title: "소액 투자 가능",
    description: "1만원부터 시작 가능. 누구나 쉽게 SPKI 투자의 혜택을 누릴 수 있습니다.",
  },
  {
    icon: LineChart,
    title: "실시간 리포트",
    description: "투자 현황과 수익률을 한눈에 확인할 수 있는 직관적인 대시보드를 제공합니다.",
  },
];

const FeaturesSection = () => {
  return (
    <section className="py-24 bg-background">
      <div className="container mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-4">
          <span className="text-sm font-medium text-primary uppercase tracking-wider">Features</span>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-charcoal">
            왜 SPKI인가요?
          </h2>
          <p className="text-warm-gray text-lg">
            감정에 흔들리지 않는 SPKI가 데이터 기반으로 최적의 투자 결정을 내립니다.
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group p-8 rounded-2xl bg-card border border-border shadow-card hover:shadow-soft transition-all duration-300 hover:-translate-y-1"
            >
              <div className="w-12 h-12 rounded-xl gradient-rose flex items-center justify-center mb-5">
                <feature.icon className="w-6 h-6 text-primary-foreground" />
              </div>
              <h3 className="font-display text-xl font-semibold text-charcoal mb-3">
                {feature.title}
              </h3>
              <p className="text-warm-gray leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;
