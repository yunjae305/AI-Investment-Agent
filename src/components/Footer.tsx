import mascot from "@/assets/mascot.png";

const Footer = () => {
  return (
    <footer className="bg-card border-t border-border py-12">
      <div className="container mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <img src={mascot} alt="로고" className="w-8 h-8 object-contain" />
              <span className="font-display text-lg font-bold text-charcoal">InvestAI</span>
            </div>
            <p className="text-sm text-warm-gray leading-relaxed">
              AI 기반 자동 투자 플랫폼으로 더 스마트한 자산 관리를 경험하세요.
            </p>
          </div>
          {[
            { title: "서비스", links: ["AI 투자", "포트폴리오", "리스크 관리", "리포트"] },
            { title: "고객지원", links: ["고객센터", "FAQ", "이용약관", "개인정보처리방침"] },
            { title: "회사", links: ["회사소개", "채용", "블로그", "제휴문의"] },
          ].map((col) => (
            <div key={col.title} className="space-y-4">
              <h4 className="font-display font-semibold text-charcoal">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-sm text-warm-gray hover:text-primary transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 pt-8 border-t border-border text-center text-sm text-warm-gray">
          © 2026 InvestAI. All rights reserved.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
