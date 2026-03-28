import React, { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Grid, Line } from '@react-three/drei';
import { Sun, Users, Activity, Layers, Settings, ChevronRight } from 'lucide-react';
import { getSession, type GeoPoint, type OSMBuilding, type OSMRoad } from '../lib/cityscoutSession';

type Projected = { x: number; z: number };

function metersPerDegreeLat(): number {
  return 110_574;
}

function metersPerDegreeLon(atLat: number): number {
  return 111_320 * Math.cos((atLat * Math.PI) / 180);
}

function project(point: GeoPoint, origin: GeoPoint): Projected {
  const x = (point.lon - origin.lon) * metersPerDegreeLon(origin.lat);
  const z = (point.lat - origin.lat) * metersPerDegreeLat();
  return { x, z };
}

function buildingToBox(building: OSMBuilding, origin: GeoPoint) {
  const pts = building.outline.map((p) => project(p, origin));
  const xs = pts.map((p) => p.x);
  const zs = pts.map((p) => p.z);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minZ = Math.min(...zs);
  const maxZ = Math.max(...zs);
  return {
    cx: (minX + maxX) / 2,
    cz: (minZ + maxZ) / 2,
    w: Math.max(maxX - minX, 5),
    d: Math.max(maxZ - minZ, 5),
    h: Math.max(building.height, 3),
  };
}

function roadToLinePoints(road: OSMRoad, origin: GeoPoint): Array<[number, number, number]> {
  return road.line.map((p) => {
    const { x, z } = project(p, origin);
    return [x * SCALE_XZ, 0.02, z * SCALE_XZ];
  });
}

const SCALE_XZ = 0.02;
const SCALE_Y = 0.05;

const OSMWorld = ({ buildings, roads, origin }: { buildings: OSMBuilding[]; roads: OSMRoad[]; origin: GeoPoint }) => {
  const buildingBoxes = useMemo(() => buildings.map((b) => ({ b, box: buildingToBox(b, origin) })), [buildings, origin]);
  const roadLines = useMemo(() => roads.map((r) => roadToLinePoints(r, origin)), [origin, roads]);

  return (
    <group>
      <mesh position={[0, -0.05, 0]} receiveShadow>
        <boxGeometry args={[30, 0.1, 30]} />
        <meshStandardMaterial color="#111827" />
      </mesh>

      {buildingBoxes.map(({ b, box }) => (
        <mesh
          key={b.id}
          position={[box.cx * SCALE_XZ, (box.h * SCALE_Y) / 2, box.cz * SCALE_XZ]}
          castShadow
          receiveShadow
        >
          <boxGeometry args={[box.w * SCALE_XZ, box.h * SCALE_Y, box.d * SCALE_XZ]} />
          <meshStandardMaterial color="#94a3b8" />
        </mesh>
      ))}

      {roadLines.map((points, idx) => {
        if (points.length < 2) return null;
        return <Line key={idx} points={points} color="#22c55e" lineWidth={1} />;
      })}
    </group>
  );
};

const Dashboard = () => {
  const session = useMemo(() => getSession(), []);
  const origin = useMemo(() => {
    if (session.location?.selected.center) return session.location.selected.center;
    const bbox = session.osm?.bbox;
    if (!bbox) return { lat: 0, lon: 0 };
    return {
      lat: (bbox.south + bbox.north) / 2,
      lon: (bbox.west + bbox.east) / 2,
    };
  }, [session.location?.selected.center, session.osm?.bbox]);
  const buildings = session.osm?.buildings ?? [];
  const roads = session.osm?.roads ?? [];

  const metrics = useMemo(() => {
    const bbox = session.location?.bbox ?? session.osm?.bbox;
    if (!bbox) {
      return {
        solarExposure: 0,
        pedestrianFlowLabel: 'N/A',
        pedestrianDelta: 0,
      };
    }

    const heightMeters = (bbox.north - bbox.south) * metersPerDegreeLat();
    const widthMeters = (bbox.east - bbox.west) * metersPerDegreeLon(origin.lat);
    const bboxArea = Math.max(widthMeters * heightMeters, 1);

    const footprintArea = buildings
      .map((b) => buildingToBox(b, origin))
      .reduce((acc, box) => acc + box.w * box.d, 0);

    const coverage = Math.min(footprintArea / bboxArea, 1);
    const solarExposure = Math.round((1 - coverage * 0.8) * 100);

    const footways = roads.filter((r) => /^(footway|path|pedestrian|steps)$/.test(r.tags.highway ?? '')).length;
    const driveways = roads.length - footways;
    const score = footways / Math.max(roads.length, 1);
    const pedestrianFlowLabel = score >= 0.35 ? 'Good' : score >= 0.18 ? 'Fair' : 'Low';
    const pedestrianDelta = Math.round((score - 0.2) * 100);

    return {
      solarExposure: Math.max(0, Math.min(100, solarExposure)),
      pedestrianFlowLabel,
      pedestrianDelta,
      buildings: buildings.length,
      roads: roads.length,
      footways,
      driveways,
    };
  }, [buildings, origin, roads, session.location?.bbox, session.osm?.bbox]);

  return (
    <div className="h-screen bg-zinc-950 flex flex-col">
      <header className="bg-zinc-900/50 border-b border-white/10 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-6 h-6 text-emerald-500" />
          <h1 className="text-lg font-bold text-white">CityScout Dashboard</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 text-emerald-500 rounded-full border border-emerald-500/20 text-sm">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
            Simulation Ready
          </div>
          <button className="p-2 text-zinc-400 hover:text-white transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-80 border-r border-white/10 bg-zinc-900/30 p-6 space-y-8 overflow-y-auto">
          <div>
            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4">Environment Stats</h3>
            <div className="space-y-4">
              <div className="bg-zinc-800/50 p-4 rounded-xl border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <Sun className="w-4 h-4 text-amber-500" />
                  <span className="text-xs text-zinc-400">Solar Exposure</span>
                </div>
                <div className="text-2xl font-bold text-white">{metrics.solarExposure}%</div>
                <div className="w-full h-1 bg-zinc-700 rounded-full mt-3">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: `${metrics.solarExposure}%` }}></div>
                </div>
              </div>
              <div className="bg-zinc-800/50 p-4 rounded-xl border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <Users className="w-4 h-4 text-blue-500" />
                  <span className="text-xs text-zinc-400">Pedestrian Flow</span>
                </div>
                <div className="text-2xl font-bold text-white">{metrics.pedestrianFlowLabel}</div>
                <div className="text-xs text-emerald-500 mt-2 flex items-center">
                  {metrics.pedestrianDelta >= 0 ? '+' : ''}{metrics.pedestrianDelta}% from baseline <ChevronRight className="w-3 h-3 ml-1" />
                </div>
              </div>
              <div className="bg-zinc-800/50 p-4 rounded-xl border border-white/5">
                <div className="flex items-center justify-between mb-2">
                  <Activity className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs text-zinc-400">OSM Objects</span>
                </div>
                <div className="text-sm text-zinc-200">Buildings: {metrics.buildings ?? buildings.length}</div>
                <div className="text-sm text-zinc-200">Roads: {metrics.roads ?? roads.length}</div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4">Analysis Layers</h3>
            <div className="space-y-2">
              {['Terrain Contours', 'Shadow Map', 'Accessibility Heatmap', 'Building Massing'].map((layer, i) => (
                <button key={i} className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-white/5 transition-colors group">
                  <span className="text-sm text-zinc-400 group-hover:text-white">{layer}</span>
                  <div className={`w-10 h-5 rounded-full relative transition-colors ${i < 2 ? 'bg-emerald-500' : 'bg-zinc-700'}`}>
                    <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${i < 2 ? 'left-6' : 'left-1'}`}></div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="flex-1 relative bg-zinc-900">
          <Suspense fallback={<div className="flex items-center justify-center h-full text-zinc-500">Loading 3D Scene...</div>}>
            <Canvas shadows>
              <PerspectiveCamera makeDefault position={[10, 10, 10]} />
              <OrbitControls />
              <ambientLight intensity={0.5} />
              <pointLight position={[10, 10, 10]} castShadow />
              <Environment preset="city" />
              <Grid infiniteGrid fadeDistance={50} sectionSize={5} />
              <OSMWorld buildings={buildings} roads={roads} origin={origin} />
            </Canvas>
          </Suspense>

          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-zinc-900/80 backdrop-blur-xl border border-white/10 p-2 rounded-2xl">
            {['Orbit', 'Top', 'First Person', 'Free'].map((mode, i) => (
              <button key={i} className={`px-4 py-2 text-sm font-medium rounded-xl transition-all ${i === 0 ? 'bg-emerald-600 text-white shadow-lg' : 'text-zinc-400 hover:text-white'}`}>
                {mode}
              </button>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
