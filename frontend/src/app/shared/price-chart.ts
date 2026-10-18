import { Component, computed, input } from '@angular/core';

import { PricePoint } from '../core/api/models';
import { frMonth, frNumber, frShortDate } from './format';

export interface ChartGeometry {
  historyPath: string;
  forecastPath: string;
  bridgePath: string;
  bandPath: string;
  yTicks: { y: number; label: string }[];
  xTicks: { x: number; label: string }[];
}

const PAD = { left: 48, right: 12, top: 12, bottom: 28 };

/** Pure layout of the chart (SVG coordinates), unit-tested in price-chart.spec.ts. */
export function chartGeometry(history: PricePoint[], forecast: PricePoint[], width: number, height: number): ChartGeometry {
  const all = [...history, ...forecast];
  if (all.length === 0) {
    return { historyPath: '', forecastPath: '', bridgePath: '', bandPath: '', yTicks: [], xTicks: [] };
  }
  const times = all.map((p) => Date.parse(p.date));
  const values = all.flatMap((p) => [p.price, p.low ?? p.price, p.high ?? p.price]);
  const t0 = Math.min(...times);
  const t1 = Math.max(...times);
  const spread = Math.max(...values) - Math.min(...values) || 1;
  const v0 = Math.min(...values) - spread * 0.08;
  const v1 = Math.max(...values) + spread * 0.08;

  const x = (date: string) => PAD.left + ((Date.parse(date) - t0) / (t1 - t0 || 1)) * (width - PAD.left - PAD.right);
  const y = (value: number) => PAD.top + (1 - (value - v0) / (v1 - v0)) * (height - PAD.top - PAD.bottom);
  const line = (points: PricePoint[], key: (p: PricePoint) => number = (p) => p.price) =>
    points.map((p, i) => `${i ? 'L' : 'M'}${x(p.date).toFixed(1)},${y(key(p)).toFixed(1)}`).join(' ');

  const lastHistory = history.at(-1);
  const firstForecast = forecast[0];
  const band = forecast.filter((p) => p.low !== null && p.high !== null);

  const yTicks = [0, 1, 2, 3].map((k) => {
    const value = v0 + ((v1 - v0) * (k + 0.5)) / 4;
    return { y: y(value), label: frNumber(value, 1) };
  });
  const xTicks = [history[0], lastHistory, forecast.at(-1)]
    .filter((p): p is PricePoint => !!p)
    .map((p, i) => ({ x: x(p.date), label: i < 2 ? frMonth(p.date) : frShortDate(p.date) }));

  return {
    historyPath: line(history),
    forecastPath: line(forecast),
    bridgePath: lastHistory && firstForecast ? line([lastHistory, firstForecast]) : '',
    bandPath: band.length
      ? `${line(band, (p) => p.high!)} ${[...band].reverse().map((p) => `L${x(p.date).toFixed(1)},${y(p.low!).toFixed(1)}`).join(' ')} Z`
      : '',
    yTicks,
    xTicks,
  };
}

/** History (grey) + forecast (olive) with its interval band. Dependency-free SVG. */
@Component({
  selector: 'app-price-chart',
  template: `
    <svg class="chart" [attr.viewBox]="'0 0 ' + width + ' ' + height" role="img" [attr.aria-label]="label()">
      @for (t of geometry().yTicks; track t.y) {
        <line class="grid-line" [attr.x1]="48" [attr.x2]="width - 12" [attr.y1]="t.y" [attr.y2]="t.y" />
        <text class="tick" x="42" [attr.y]="t.y + 4" text-anchor="end">{{ t.label }}</text>
      }
      @for (t of geometry().xTicks; track $index) {
        <text class="tick" [attr.x]="t.x" [attr.y]="height - 8" [attr.text-anchor]="$index === 0 ? 'start' : 'middle'">
          {{ t.label }}
        </text>
      }
      <path class="band" [attr.d]="geometry().bandPath" />
      <path class="history" [attr.d]="geometry().historyPath" />
      <path class="bridge" [attr.d]="geometry().bridgePath" />
      <path class="forecast" [attr.d]="geometry().forecastPath" />
    </svg>
    <p class="legend">
      <span class="key key-history"></span> prix observés (mensuels)
      <span class="key key-forecast"></span> prévision (hebdomadaire)
      <span class="key key-band"></span> intervalle à 80 %
    </p>
  `,
})
export class PriceChart {
  readonly history = input.required<PricePoint[]>();
  readonly forecast = input.required<PricePoint[]>();
  readonly unit = input('TND/kg');

  protected readonly width = 640;
  protected readonly height = 260;
  protected readonly geometry = computed(() => chartGeometry(this.history(), this.forecast(), this.width, this.height));
  protected readonly label = computed(() => `Prix observés et prévus (${this.unit()})`);
}
