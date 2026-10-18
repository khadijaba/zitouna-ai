import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { PriceResult } from '../../core/api/models';
import { Price } from './price';

const RESULT: PriceResult = {
  currency: 'TND',
  unit: 'kg',
  history: [
    { date: '2026-06-15', price: 18.44, low: null, high: null },
    { date: '2026-07-15', price: 18.54, low: null, high: null },
  ],
  forecast: [
    { date: '2026-10-24', price: 19.1, low: 18.2, high: 20.0 },
    { date: '2026-10-31', price: 19.6, low: 18.4, high: 20.9 },
  ],
  recommendation: 'STORE',
  reason: 'Le prix pourrait atteindre 19.60 TND/kg vers le 31/10.',
  expectedGainTnd: 630,
  modelVersion: 'sarima',
  mock: false,
  source: 'FMI — prix mondial',
};

describe('Price', () => {
  it('asks 12 weeks by default and shows the advice, the key figures, the chart and the source', async () => {
    TestBed.configureTestingModule({
      imports: [Price],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const backend = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(Price);
    fixture.detectChanges();

    backend.expectOne('/api/ai/price?horizonWeeks=12').flush(RESULT);
    await fixture.whenStable();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.rec-store')?.textContent).toContain('stocker');
    expect(el.textContent).toContain('630');
    expect(el.textContent).toContain('19,60'); // best forecast price, French format
    expect(el.textContent).toContain('FMI — prix mondial');
    expect(el.querySelector('svg.chart path.forecast')?.getAttribute('d')).toMatch(/^M/);
    expect(el.querySelectorAll('details tbody tr')).toHaveLength(2);
    backend.verify();
  });
});
