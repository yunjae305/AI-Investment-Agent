import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

const CTASection = () => {
  return (
    <section className="py-24 bg-background">
      <div className="container mx-auto px-6">
        <div className="relative rounded-3xl gradient-rose p-12 md:p-16 text-center overflow-hidden">
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-10 left-10 w-32 h-32 rounded-full bg-primary-foreground blur-2xl" />
            <div className="absolute bottom-10 right-10 w-48 h-48 rounded-full bg-primary-foreground blur-3xl" />
          </div>
          <div className="relative space-y-6 max-w-2xl mx-auto">
            <h2 className="font-display text-3xl md:text-4xl font-bold text-primary-foreground">
              지금 바로 SPKI와 투자를 시작하세요
            </h2>
            <p className="text-primary-foreground/80 text-lg">
              가입 후 3분 만에 SPKI가 맞춤 포트폴리오를 추천합니다.
              첫 달 수수료 무료!
            </p>
            <Button variant="gold" size="lg" className="text-base px-10 py-6 rounded-xl gap-2">
              지금 시작하기
              <ArrowRight className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CTASection;
