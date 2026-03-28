import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import mascot from "@/assets/mascot.png";

const Navbar = () => {
  return (
    <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-3">
            <img src={mascot} alt="로고" className="w-8 h-8 object-contain" />
            <span className="font-display text-xl font-bold text-charcoal">SPKI</span>
          </Link>
        </div>
        <div className="hidden md:flex items-center gap-8">
          <Link to="/" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">투자 분석</Link>
          <Link to="/mock-trading" className="text-sm font-medium text-warm-gray hover:text-charcoal transition-colors">모의매매 현황</Link>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="hero" size="sm" className="rounded-lg" asChild>
            <Link to="/">대시보드</Link>
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
