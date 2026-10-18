import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, UrlTree } from '@angular/router';

import { AdminStats, AdminUser, AuthResponse, PageResponse } from '../../core/api/models';
import { adminGuard } from '../../core/auth/auth.guard';
import { AdminDashboard } from './admin-dashboard';
import { AdminUsers } from './admin-users';

function session(role: 'FARMER' | 'ADMIN', id = 1): void {
  const auth: AuthResponse = {
    token: 't',
    expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
    user: { id, fullName: 'Test', email: 'test@zitouna.tn', role },
  };
  localStorage.setItem('zitouna.auth', JSON.stringify(auth));
}

function setup() {
  TestBed.configureTestingModule({
    providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
  });
  return TestBed.inject(HttpTestingController);
}

afterEach(() => localStorage.clear());

describe('home after login', () => {
  it('sends the admin to the back-office and a farmer to their dashboard', async () => {
    const { routes } = await import('../../app.routes');
    const home = routes.find((r) => r.path === '')!.children!.find((r) => r.path === '')!;
    const redirect = home.redirectTo as () => string;

    session('ADMIN');
    setup();
    expect(TestBed.runInInjectionContext(redirect)).toBe('admin');

    TestBed.resetTestingModule();
    session('FARMER');
    setup();
    expect(TestBed.runInInjectionContext(redirect)).toBe('home');
  });
});

describe('adminGuard', () => {
  it('sends farmers back to their dashboard and lets admins in', () => {
    session('FARMER');
    setup();
    const farmer = TestBed.runInInjectionContext(() => adminGuard({} as never, {} as never));
    expect(farmer instanceof UrlTree && TestBed.inject(Router).serializeUrl(farmer)).toBe('/home');

    TestBed.resetTestingModule();
    session('ADMIN');
    setup();
    expect(TestBed.runInInjectionContext(() => adminGuard({} as never, {} as never))).toBe(true);
  });
});

describe('AdminDashboard', () => {
  it('shows the totals, the usage per module and the live state of the models', async () => {
    session('ADMIN');
    const backend = setup();
    const fixture = TestBed.createComponent(AdminDashboard);
    fixture.detectChanges();
    const stats: AdminStats = {
      users: 12, admins: 1, parcels: 7, trees: 1750, areaHa: 17.5, predictions: 40, mockPredictions: 4,
      predictionsByType: { DISEASE: 10, IRRIGATION: 8, YIELD: 6, PRICE: 6, CHAT: 5, TREE_COUNT: 3, HARVEST_PLAN: 2 },
      last30Days: Array.from({ length: 30 }, (_, i) => ({ date: `2026-10-${String(i + 1).padStart(2, '0')}`, count: i % 4 })),
      parcelsByGovernorate: [{ governorate: 'Sfax', parcels: 5 }, { governorate: 'Sousse', parcels: 2 }],
      status: {
        application: { name: 'b', version: 'dev', springBootVersion: '4.1.1', javaVersion: '21', uptimeSeconds: 60 },
        database: { up: true, product: 'PostgreSQL', version: '17' },
        modules: [
          { id: 'M1', name: 'Maladies', type: 'Vision', up: true, modelLoaded: true, latencyMs: 5, error: null },
          { id: 'M2', name: 'Irrigation', type: 'LSTM', up: false, modelLoaded: null, latencyMs: null, error: 'x' },
        ],
        checkedAt: '2026-10-17T10:00:00Z',
      },
    };
    backend.expectOne('/api/admin/stats').flush(stats);
    await fixture.whenStable();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toMatch(/1\s750/); // trees, French format (narrow no-break space)
    expect(el.textContent).toMatch(/90\s%/); // share of real-model predictions
    expect(el.querySelectorAll('.activity-bar')).toHaveLength(30);
    expect(el.querySelectorAll('.hbar-row').length).toBe(7 + 2);
    expect(el.querySelector('.pill-ok')?.textContent).toContain('Modèle réel');
    expect(el.querySelector('.pill-down')?.textContent).toContain('Hors ligne');
  });
});

describe('AdminUsers', () => {
  it('lists accounts, deletes a farmer, never offers to delete or change the single admin', async () => {
    session('ADMIN', 1);
    const backend = setup();
    const fixture = TestBed.createComponent(AdminUsers);
    fixture.detectChanges();
    const page: PageResponse<AdminUser> = {
      content: [
        { id: 1, fullName: 'Admin', email: 'admin@zitouna.tn', role: 'ADMIN', createdAt: '2026-10-01T00:00:00Z', parcels: 0, predictions: 0 },
        { id: 2, fullName: 'Salah', email: 'salah@ex.tn', role: 'FARMER', createdAt: '2026-10-02T00:00:00Z', parcels: 2, predictions: 9 },
      ],
      page: 0, size: 20, totalElements: 2, totalPages: 1,
    };
    backend.expectOne('/api/admin/users?q=&page=0').flush(page);
    await fixture.whenStable();

    const rows: HTMLTableRowElement[] = Array.from(fixture.nativeElement.querySelectorAll('tbody tr'));
    expect(rows).toHaveLength(2);
    expect(fixture.nativeElement.querySelector('tbody select')).toBeNull(); // no role change anywhere
    expect(rows[0].textContent).toContain('Administrateur');
    expect(rows[0].querySelector('button')).toBeNull(); // the admin cannot be deleted
    expect(rows[1].textContent).toContain('Agriculteur');

    vi.spyOn(window, 'confirm').mockReturnValue(true);
    (rows[1].querySelector('button') as HTMLButtonElement).click();
    const del = backend.expectOne('/api/admin/users/2');
    expect(del.request.method).toBe('DELETE');
    del.flush(null);
    backend.expectOne('/api/admin/users?q=&page=0').flush(page);
    backend.verify();
  });
});
