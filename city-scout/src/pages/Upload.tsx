import React, { useMemo, useState } from 'react';
import { MapPin, Search, ArrowRight, Loader2, Ruler } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { bboxAround, bboxToParam, clearSession, setSession, type LocationSearchResult } from '../lib/cityscoutSession';

const Upload = () => {
  const [query, setQuery] = useState('');
  const [radiusKm, setRadiusKm] = useState(1);
  const [results, setResults] = useState<LocationSearchResult[]>([]);
  const [selected, setSelected] = useState<LocationSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const bbox = useMemo(() => {
    if (!selected) return null;
    return bboxAround(selected.center, radiusKm);
  }, [radiusKm, selected]);

  const runSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setSelected(null);

    try {
      const res = await fetch(`/api/location/search?q=${encodeURIComponent(q)}`);
      if (!res.ok) {
        setResults([]);
        setError(`검색 실패 (HTTP ${res.status})`);
        return;
      }
      const json = (await res.json()) as { results?: LocationSearchResult[] };
      const next = Array.isArray(json.results) ? json.results : [];
      setResults(next);
      setSelected(next[0] ?? null);
    } catch (e) {
      setResults([]);
      setError(`검색 중 오류: ${String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleProceed = () => {
    if (!selected || !bbox) return;
    clearSession();
    setSession({
      location: {
        query: query.trim(),
        selected,
        radiusKm,
        bbox,
      },
    });
    navigate('/convert');
  };

  return (
    <div className="min-h-screen bg-zinc-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl border border-zinc-100 overflow-hidden">
          <div className="p-8">
            <div className="text-center mb-10">
              <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <MapPin className="w-8 h-8 text-emerald-600" />
              </div>
              <h2 className="text-3xl font-bold text-zinc-900">주소/지역명으로 분석 시작</h2>
              <p className="text-zinc-600 mt-2">파일 업로드 없이, 장소를 입력하면 필요한 데이터를 자동으로 수집합니다.</p>
            </div>

            <div className="space-y-6">
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') runSearch();
                    }}
                    placeholder="예: 강남역, 서울시청, 건국대학교"
                    className="flex-1 px-4 py-3 rounded-xl border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500"
                  />
                  <button
                    onClick={runSearch}
                    disabled={loading || !query.trim()}
                    className="px-4 py-3 rounded-xl bg-zinc-900 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
                    검색
                  </button>
                </div>

                {error && <div className="text-sm text-red-600">{error}</div>}

                <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                      <Ruler className="w-4 h-4 text-emerald-600" />
                      분석 범위
                    </div>
                    <div className="text-sm font-semibold text-emerald-700">반경 {radiusKm}km</div>
                  </div>
                  <input
                    type="range"
                    min={0.5}
                    max={3}
                    step={0.5}
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(Number(e.target.value))}
                    className="w-full"
                  />
                  {bbox && (
                    <div className="mt-3 text-xs text-zinc-500">
                      bbox: {bboxToParam(bbox)}
                    </div>
                  )}
                </div>
              </div>

              {results.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest">검색 결과</div>
                  <div className="max-h-52 overflow-y-auto rounded-xl border border-zinc-200 bg-white">
                    {results.map((item) => {
                      const active = selected?.displayName === item.displayName;
                      return (
                        <button
                          key={item.displayName}
                          type="button"
                          onClick={() => setSelected(item)}
                          className={`w-full text-left px-4 py-3 border-b border-zinc-100 last:border-b-0 hover:bg-emerald-50 transition-colors ${active ? 'bg-emerald-50' : ''}`}
                        >
                          <div className="text-sm font-semibold text-zinc-900">{item.displayName}</div>
                          <div className="text-xs text-zinc-500">{item.center.lat.toFixed(6)}, {item.center.lon.toFixed(6)}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <button
                onClick={handleProceed}
                disabled={!selected || !bbox}
                className="w-full py-4 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                분석 시작 <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
