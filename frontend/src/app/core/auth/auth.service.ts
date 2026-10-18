import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { AuthResponse } from '../api/models';

const STORAGE_KEY = 'zitouna.auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly session = signal<AuthResponse | null>(restoreSession());

  readonly user = computed(() => this.session()?.user ?? null);
  readonly isLoggedIn = computed(() => this.session() !== null);
  /** Back-office access. The backend checks the role again on every /api/admin call. */
  readonly isAdmin = computed(() => this.session()?.user.role === 'ADMIN');

  token(): string | null {
    return this.session()?.token ?? null;
  }

  login(body: { email: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/api/auth/login', body).pipe(tap((r) => this.save(r)));
  }

  register(body: { fullName: string; email: string; password: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/api/auth/register', body).pipe(tap((r) => this.save(r)));
  }

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    this.session.set(null);
    this.router.navigate(['/login']);
  }

  private save(response: AuthResponse): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(response));
    this.session.set(response);
  }
}

function restoreSession(): AuthResponse | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as AuthResponse;
    return new Date(session.expiresAt) > new Date() ? session : null;
  } catch {
    return null;
  }
}
