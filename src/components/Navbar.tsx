import { Button } from "@/components/ui/button";
import mascot from "@/assets/mascot.png";

const Navbar = () => {
  return (
    <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={mascot} alt="로고" className="w-8 h-8 object-contain" />
          <span className="font-display text-xl font-bold text-charcoal">InvestAI</span>
        </div>
        <div className="hidden md:flex items-center gap-8">
          <a href="#" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">서비스</a>
          <a href="#" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">수익률</a>
          <a href="#" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">요금제</a>
          <a href="#" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">고객센터</a>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" className="text-charcoal">로그인</Button>
          <Button variant="hero" size="sm" className="rounded-lg">무료 시작</Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
