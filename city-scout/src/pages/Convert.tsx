import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Globe, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { bboxToParam, getSession, setSession } from '../lib/cityscoutSession';

const Convert = () => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const location = useMemo(() => getSession().location ?? null, []);

  useEffect(() => {
    if (!location) {
      navigate('/upload');
      return;
    }

    let cancelled = false;

    const run = async () => {
      setStatus('loading');
      setError(null);
      setProgress(5);

      try {
        setProgress(15);
        const bbox = location.bbox;
        const bboxParam = bboxToParam(bbox);
        const res = await fetch(`/api/osm/fetch?bbox=${encodeURIComponent(bboxParam)}&maxBuildings=250&maxRoads=250`);
        setProgress(65);
        if (!res.ok) {
          const text = await res.text().catch(() => '');
          throw new Error(`OSM 수집 실패 (HTTP ${res.status}) ${text.slice(0, 200)}`);
        }
        const json = await res.json();
        if (cancelled) return;
        setSession({ osm: json });
        setProgress(90);
        setTimeout(() => {
          if (cancelled) return;
          setProgress(100);
          setStatus('done');
          navigate('/dashboard');
        }, 500);
      } catch (e) {
        if (cancelled) return;
        setStatus('error');
        setError(String(e));
        setProgress(0);
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [location, navigate]);

  const steps = [
    { label: '지오코딩 결과 확인', min: 0 },
    { label: 'OSM(Overpass) 데이터 수집', min: 15 },
    { label: '건물/도로 데이터 정리', min: 65 },
    { label: '3D 뷰어 준비', min: 90 },
  ];

  return (
    <div className="min-h-screen bg-zinc-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="relative w-32 h-32 mx-auto mb-12">
          <div className="absolute inset-0 border-4 border-emerald-500/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Globe className="w-12 h-12 text-emerald-500" />
          </div>
        </div>

        <h2 className="text-3xl font-bold text-white mb-2">Converting to 3D</h2>
        <p className="text-zinc-400 mb-12">OSM 데이터를 수집하고 3D 분석을 준비하는 중입니다...</p>

        <div className="space-y-8">
          <div className="relative h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div 
              className="absolute top-0 left-0 h-full bg-emerald-500 transition-all duration-300 ease-out shadow-[0_0_15px_rgba(16,185,129,0.5)]"
              style={{ width: `${progress}%` }}
            ></div>
          </div>

          <div className="grid grid-cols-1 gap-4 text-left">
            {steps.map((step, idx) => (
              <div key={idx} className={`flex items-center gap-3 transition-colors ${progress >= step.min ? 'text-emerald-400' : 'text-zinc-600'}`}>
                {progress >= step.min ? <CheckCircle2 className="w-5 h-5" /> : <Loader2 className="w-5 h-5 animate-spin" />}
                <span className="text-sm font-medium">{step.label}</span>
              </div>
            ))}

            {status === 'error' && (
              <div className="mt-4 bg-red-500/10 border border-red-500/20 p-4 rounded-xl text-red-200">
                <div className="flex items-center gap-2 font-semibold">
                  <AlertTriangle className="w-5 h-5" />
                  데이터 수집 실패
                </div>
                <div className="text-xs mt-2 text-red-200/80 break-words">{error}</div>
                <button
                  onClick={() => window.location.reload()}
                  className="mt-4 px-4 py-2 rounded-lg bg-red-500 text-white font-semibold"
                >
                  다시 시도
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Convert;
