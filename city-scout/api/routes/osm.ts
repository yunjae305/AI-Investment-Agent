import { Router } from 'express';

type OverpassElement = {
  type: 'way' | 'relation' | 'node';
  id: number;
  tags?: Record<string, string>;
  geometry?: Array<{ lat: number; lon: number }>;
};

function parseNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const n = Number.parseFloat(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function parseBbox(raw: string): { south: number; west: number; north: number; east: number } | null {
  const parts = raw.split(',').map((p) => p.trim());
  if (parts.length !== 4) return null;
  const south = parseNumber(parts[0]);
  const west = parseNumber(parts[1]);
  const north = parseNumber(parts[2]);
  const east = parseNumber(parts[3]);
  if (south == null || west == null || north == null || east == null) return null;
  return {
    south: clamp(Math.min(south, north), -90, 90),
    west: clamp(Math.min(west, east), -180, 180),
    north: clamp(Math.max(south, north), -90, 90),
    east: clamp(Math.max(west, east), -180, 180),
  };
}

function centroid(points: Array<{ lat: number; lon: number }>): { lat: number; lon: number } {
  const n = Math.max(points.length, 1);
  const sum = points.reduce(
    (acc, p) => ({ lat: acc.lat + p.lat, lon: acc.lon + p.lon }),
    { lat: 0, lon: 0 },
  );
  return { lat: sum.lat / n, lon: sum.lon / n };
}

function samplePoints<T>(points: T[], maxPoints: number): T[] {
  if (points.length <= maxPoints) return points;
  const step = points.length / maxPoints;
  const sampled: T[] = [];
  for (let i = 0; i < maxPoints; i += 1) {
    sampled.push(points[Math.floor(i * step)]);
  }
  return sampled;
}

function normalizeHeight(tags: Record<string, string> | undefined): number {
  if (!tags) return 10;

  const height = parseNumber(tags.height);
  if (height != null) return clamp(height, 3, 200);

  const levels = parseNumber(tags['building:levels'] ?? tags.levels);
  if (levels != null) return clamp(levels * 3, 3, 200);

  return 10;
}

const router = Router();

router.get('/fetch', async (req, res) => {
  const bboxRaw = String(req.query.bbox ?? '').trim();
  const bbox = bboxRaw ? parseBbox(bboxRaw) : null;
  if (!bbox) {
    res.status(400).json({ error: 'invalid_bbox', expected: 'south,west,north,east' });
    return;
  }

  const maxBuildings = parseNumber(req.query.maxBuildings) ?? 250;
  const maxRoads = parseNumber(req.query.maxRoads) ?? 250;

  const bboxOverpass = `${bbox.south},${bbox.west},${bbox.north},${bbox.east}`;
  const query = `
[out:json][timeout:25];
(
  way["building"](${bboxOverpass});
  way["highway"~"^(footway|path|pedestrian|steps|cycleway|residential|service|tertiary|secondary)$"](${bboxOverpass});
);
out tags geom;
`;

  const response = await fetch('https://overpass-api.de/api/interpreter', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
      'Accept': 'application/json',
      'User-Agent': 'CityScout/0.1 (demo; contact: local)',
      'Referer': 'http://localhost/',
    },
    body: new URLSearchParams({ data: query }).toString(),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    res.status(502).json({ error: 'overpass_failed', status: response.status, detail: text.slice(0, 300) });
    return;
  }

  const data = (await response.json()) as { elements?: OverpassElement[] };
  const elements = Array.isArray(data.elements) ? data.elements : [];

  const buildingWays = elements
    .filter((el) => el.type === 'way' && el.tags?.building && Array.isArray(el.geometry) && el.geometry.length >= 3)
    .slice(0, Math.max(0, Math.floor(maxBuildings)));

  const roadWays = elements
    .filter((el) => el.type === 'way' && el.tags?.highway && Array.isArray(el.geometry) && el.geometry.length >= 2)
    .slice(0, Math.max(0, Math.floor(maxRoads)));

  const buildings = buildingWays.map((way) => {
    const geom = samplePoints(way.geometry ?? [], 60);
    return {
      id: `way/${way.id}`,
      tags: way.tags ?? {},
      height: normalizeHeight(way.tags),
      center: centroid(geom),
      outline: geom,
    };
  });

  const roads = roadWays.map((way) => {
    const geom = samplePoints(way.geometry ?? [], 80);
    return {
      id: `way/${way.id}`,
      tags: way.tags ?? {},
      center: centroid(geom),
      line: geom,
    };
  });

  res.json({
    source: 'overpass',
    bbox,
    counts: {
      buildings: buildings.length,
      roads: roads.length,
    },
    buildings,
    roads,
  });
});

export { router as osmRouter };

