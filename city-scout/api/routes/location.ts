import { Router } from 'express';

type NominatimSearchItem = {
  display_name: string;
  lat: string;
  lon: string;
  boundingbox: [string, string, string, string];
};

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function parseFloatSafe(value: string): number | null {
  const n = Number.parseFloat(value);
  if (!Number.isFinite(n)) return null;
  return n;
}

const router = Router();

router.get('/search', async (req, res) => {
  const query = String(req.query.q ?? '').trim();
  if (!query) {
    res.status(400).json({ error: 'missing_query' });
    return;
  }

  const url = new URL('https://nominatim.openstreetmap.org/search');
  url.searchParams.set('format', 'json');
  url.searchParams.set('limit', '5');
  url.searchParams.set('q', query);

  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      'User-Agent': 'CityScout/0.1 (demo; contact: local)',
      'Referer': 'http://localhost/',
    },
  });

  if (!response.ok) {
    res.status(502).json({ error: 'geocoding_failed', status: response.status });
    return;
  }

  const items = (await response.json()) as NominatimSearchItem[];
  const results = items
    .map((item) => {
      const lat = parseFloatSafe(item.lat);
      const lon = parseFloatSafe(item.lon);
      const south = parseFloatSafe(item.boundingbox[0]);
      const north = parseFloatSafe(item.boundingbox[1]);
      const west = parseFloatSafe(item.boundingbox[2]);
      const east = parseFloatSafe(item.boundingbox[3]);
      if (lat == null || lon == null || south == null || north == null || west == null || east == null) return null;

      return {
        displayName: item.display_name,
        center: { lat: clamp(lat, -90, 90), lon: clamp(lon, -180, 180) },
        bbox: {
          south: clamp(Math.min(south, north), -90, 90),
          west: clamp(Math.min(west, east), -180, 180),
          north: clamp(Math.max(south, north), -90, 90),
          east: clamp(Math.max(west, east), -180, 180),
        },
      };
    })
    .filter((v): v is NonNullable<typeof v> => Boolean(v));

  res.json({ query, results });
});

export { router as locationRouter };

