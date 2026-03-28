const stats = [
  { value: "₩2.4조", label: "총 운용 자산", suffix: "" },
  { value: "150만+", label: "활성 사용자", suffix: "" },
  { value: "12.4%", label: "평균 연수익률", suffix: "" },
  { value: "99.9%", label: "시스템 가동률", suffix: "" },
];

const StatsSection = () => {
  return (
    <section className="py-16 bg-card border-y border-border">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center space-y-2">
              <div className="font-display text-3xl md:text-4xl font-bold text-primary">
                {stat.value}
              </div>
              <div className="text-sm text-warm-gray font-medium">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default StatsSection;
