export type GeoPoint = { lat: number; lon: number };

export type BBox = { south: number; west: number; north: number; east: number };

export type LocationSearchResult = {
  displayName: string;
  center: GeoPoint;
  bbox: BBox;
};

export type OSMBuilding = {
  id: string;
  tags: Record<string, string>;
  height: number;
  center: GeoPoint;
  outline: GeoPoint[];
};

export type OSMRoad = {
  id: string;
  tags: Record<string, string>;
  center: GeoPoint;
  line: GeoPoint[];
};

export type OSMFetchResponse = {
  source: string;
  bbox: BBox;
  counts: { buildings: number; roads: number };
  buildings: OSMBuilding[];
  roads: OSMRoad[];
};

type SessionState = {
  location?: {
    query: string;
    selected: LocationSearchResult;
    radiusKm: number;
    bbox: BBox;
  };
  osm?: OSMFetchResponse;
};

const KEY = 'cityscout:session:v1';

function safeParse(json: string): unknown {
  try {
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function getSession(): SessionState {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return {};
  const parsed = safeParse(raw);
  if (!parsed || typeof parsed !== 'object') return {};
  return parsed as SessionState;
}

export function setSession(patch: Partial<SessionState>): void {
  const current = getSession();
  const next: SessionState = { ...current, ...patch };
  sessionStorage.setItem(KEY, JSON.stringify(next));
}

export function clearSession(): void {
  sessionStorage.removeItem(KEY);
}

export function bboxAround(center: GeoPoint, radiusKm: number): BBox {
  const lat = center.lat;
  const lon = center.lon;
  const latDelta = radiusKm / 110.574;
  const lonDelta = radiusKm / (111.320 * Math.cos((lat * Math.PI) / 180));

  return {
    south: lat - latDelta,
    west: lon - lonDelta,
    north: lat + latDelta,
    east: lon + lonDelta,
  };
}

export function bboxToParam(bbox: BBox): string {
  return `${bbox.south},${bbox.west},${bbox.north},${bbox.east}`;
}

