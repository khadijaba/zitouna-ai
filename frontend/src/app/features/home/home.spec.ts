import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthResponse, PageResponse, Parcel, PredictionRecord } from '../../core/api/models';
import { Home } from './home';

const PARCEL: Parcel = {
  id: 7, name: 'Henchir Sfax', governorate: 'Sfax', latitude: 34.74, longitude: 10.76, areaHa: 2.5,
  treeCount: 250, variety: 'Chemlali', irrigated: true, createdAt: '2026-10-17T10:00:00Z',
};

describe('Home', () => {
  afterEach(() => localStorage.clear());

  it('greets the farmer, sums the farm and links the tools to the first parcel', async () => {
    const auth: AuthResponse = {
      token: 't', expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
      user: { id: 3, fullName: 'Salah Ben Ali', email: 's@ex.tn', role: 'FARMER' },
    };
    localStorage.setItem('zitouna.auth', JSON.stringify(auth));
    TestBed.configureTestingModule({
      imports: [Home],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const backend = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(Home);
    fixture.detectChanges();

    backend.expectOne('/api/parcels').flush([PARCEL, { ...PARCEL, id: 8, name: 'Zitouna 2', treeCount: 100, areaHa: 1 }]);
    const history: PageResponse<PredictionRecord> = {
      content: [{ id: 1, type: 'IRRIGATION', parcelId: 7, parcelName: 'Henchir Sfax', request: {}, response: {}, mock: false, createdAt: '2026-10-17T10:00:00Z' }],
      page: 0, size: 20, totalElements: 12, totalPages: 1,
    };
    backend.expectOne('/api/history?page=0').flush(history);
    await fixture.whenStable();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('h1')?.textContent).toContain('Bonjour Salah');
    expect(el.textContent).toContain('350'); // trees of both parcels
    expect(el.textContent).toContain('3,5 ha');
    expect(el.textContent).toContain('12'); // AI analyses
    expect(el.querySelectorAll('.tool')).toHaveLength(6);
    const harvest = Array.from(el.querySelectorAll<HTMLAnchorElement>('.tool')).find((a) => a.textContent?.includes('M3'));
    expect(harvest?.getAttribute('href')).toBe('/parcels/7');
    expect(el.textContent).toContain('M2 · Irrigation');
  });
});
