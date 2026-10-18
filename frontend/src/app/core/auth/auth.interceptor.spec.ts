import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  // AuthService restores the session from localStorage when it is created,
  // so the storage must be prepared before the TestBed is configured.
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    return { http: TestBed.inject(HttpClient), backend: TestBed.inject(HttpTestingController) };
  }

  beforeEach(() => localStorage.clear());

  it('sends no Authorization header when logged out', () => {
    const { http, backend } = setup();
    http.get('/api/parcels').subscribe();
    expect(backend.expectOne('/api/parcels').request.headers.has('Authorization')).toBe(false);
    backend.verify();
  });

  it('adds the JWT when a valid session exists', () => {
    localStorage.setItem(
      'zitouna.auth',
      JSON.stringify({ token: 'abc', expiresAt: '2999-01-01T00:00:00Z', user: {} }),
    );
    const { http, backend } = setup();
    http.get('/api/parcels').subscribe();
    expect(backend.expectOne('/api/parcels').request.headers.get('Authorization')).toBe('Bearer abc');
    backend.verify();
  });

  it('ignores an expired session', () => {
    localStorage.setItem(
      'zitouna.auth',
      JSON.stringify({ token: 'old', expiresAt: '2000-01-01T00:00:00Z', user: {} }),
    );
    const { http, backend } = setup();
    http.get('/api/parcels').subscribe();
    expect(backend.expectOne('/api/parcels').request.headers.has('Authorization')).toBe(false);
    backend.verify();
  });
});
