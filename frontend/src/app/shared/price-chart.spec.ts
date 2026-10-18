import { PricePoint } from '../core/api/models';
import { chartGeometry } from './price-chart';

const point = (date: string, price: number, low: number | null = null, high: number | null = null): PricePoint => ({
  date,
  price,
  low,
  high,
});

describe('chartGeometry', () => {
  const history = [point('2026-05-15', 18), point('2026-06-15', 18.4), point('2026-07-15', 18.5)];
  const forecast = [point('2026-10-24', 18.6, 17.9, 19.3), point('2026-10-31', 18.7, 17.8, 19.6)];

  it('draws history, forecast, the bridge between them and a closed band', () => {
    const g = chartGeometry(history, forecast, 640, 260);
    expect(g.historyPath.split('L')).toHaveLength(3);
    expect(g.forecastPath.startsWith('M')).toBe(true);
    expect(g.bridgePath.split('L')).toHaveLength(2);
    expect(g.bandPath.endsWith('Z')).toBe(true);
    expect(g.yTicks).toHaveLength(4);
    expect(g.xTicks).toHaveLength(3);
  });

  it('keeps every point inside the drawing area, higher prices higher on screen', () => {
    const g = chartGeometry(history, forecast, 640, 260);
    const coords = [...g.historyPath.matchAll(/[ML]([\d.]+),([\d.]+)/g)].map((m) => [+m[1], +m[2]]);
    for (const [x, y] of coords) {
      expect(x).toBeGreaterThanOrEqual(48);
      expect(x).toBeLessThanOrEqual(628);
      expect(y).toBeGreaterThanOrEqual(12);
      expect(y).toBeLessThanOrEqual(232);
    }
    expect(coords[2][1]).toBeLessThan(coords[0][1]); // 18.5 is drawn above 18
  });

  it('handles empty data', () => {
    expect(chartGeometry([], [], 640, 260).historyPath).toBe('');
  });
});
