import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { IrrigationResult } from '../../core/api/models';
import { IrrigationPanel } from './irrigation-panel';

const RESULT: IrrigationResult = {
  days: [
    { date: '2026-10-17', et0Mm: 3.66, rainMm: 0, waterNeedMm: 2.38, litersPerTree: 237.9, irrigate: true },
    { date: '2026-10-18', et0Mm: 2.1, rainMm: 5, waterNeedMm: 0, litersPerTree: 0, irrigate: false },
  ],
  alerts: [{ date: '2026-10-18', type: 'FROST', severity: 'HIGH', message: 'Risque de gel (-3 °C)' }],
  modelVersion: 'lstm-et0',
  mock: false,
};

describe('IrrigationPanel', () => {
  let backend: HttpTestingController;

  function render() {
    TestBed.configureTestingModule({
      imports: [IrrigationPanel],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    backend = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(IrrigationPanel);
    fixture.componentRef.setInput('parcelId', 3);
    fixture.detectChanges();
    return fixture;
  }

  it('loads 7 days, shows alerts and totals, reloads 14 days on demand', async () => {
    const fixture = render();
    backend.expectOne('/api/parcels/3/irrigation?days=7').flush(RESULT);
    await fixture.whenStable();

    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('Risque de gel');
    expect(text).toContain('1 / 2'); // days to irrigate
    expect(text).toContain('238 L'); // litres per tree over the period
    expect(text).toContain('LSTM');
    expect(fixture.nativeElement.querySelectorAll('tbody tr.highlight')).toHaveLength(1);
    expect(fixture.nativeElement.querySelector('.badge-mock')).toBeNull();

    const buttons: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('.seg button'));
    buttons[1].click();
    fixture.detectChanges();
    backend.expectOne('/api/parcels/3/irrigation?days=14').flush(RESULT);
    backend.verify();
  });
});
