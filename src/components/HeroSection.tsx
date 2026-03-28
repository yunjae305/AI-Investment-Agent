import mascot from "@/assets/mascot.png";
import { Button } from "@/components/ui/button";
import { TrendingUp, Shield, Zap } from "lucide-react";

const HeroSection = () => {
  return (
    <section className="relative gradient-hero overflow-hidden">
      <div className="container mx-auto px-6 py-24 lg:py-32">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-8 animate-fade-in-up">
            <div className="inline-flex items-center gap-2 rounded-full bg-rose-light px-4 py-1.5 text-sm font-medium text-primary">
              <Zap className="w-4 h-4" />
              AI 기반 자동 투자
            </div>
            <h1 className="font-display text-4xl md:text-5xl lg:text-6xl font-bold text-charcoal leading-tight">
              스마트한 투자,
              <br />
              <span className="text-primary">AI가 함께합니다</span>
            </h1>
            <p className="text-warm-gray text-lg max-w-lg leading-relaxed">
              최첨단 AI 에이전트가 시장을 분석하고, 최적의 포트폴리오를 구성합니다. 
              안전하고 똑똑한 투자를 경험하세요.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button variant="hero" size="lg" className="text-base px-8 py-6 rounded-xl">
                무료로 시작하기
              </Button>
              <Button variant="outline" size="lg" className="text-base px-8 py-6 rounded-xl border-primary/30 text-charcoal hover:bg-rose-light">
                더 알아보기
              </Button>
            </div>
            <div className="flex items-center gap-8 pt-4">
              <div className="flex items-center gap-2 text-sm text-warm-gray">
                <Shield className="w-4 h-4 text-primary" />
                안전한 투자
              </div>
              <div className="flex items-center gap-2 text-sm text-warm-gray">
                <TrendingUp className="w-4 h-4 text-accent" />
                평균 수익률 12.4%
              </div>
            </div>
          </div>
          <div className="relative flex justify-center lg:justify-end">
            <div className="relative">
              <div className="absolute inset-0 gradient-rose rounded-full opacity-20 blur-3xl scale-110" />
              <img 
                src={mascot} 
                alt="AI 투자 마스코트" 
                className="relative w-64 h-64 md:w-80 md:h-80 object-contain animate-float drop-shadow-xl"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
