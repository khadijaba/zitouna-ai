import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { errorMessage } from '../../shared/errors';
import { AuthHero } from './auth-hero';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink, AuthHero],
  template: `
    <div class="auth-page">
      <app-auth-hero />
      <div class="auth-panel">
        <form [formGroup]="form" (ngSubmit)="submit()">
          <div>
            <p class="eyebrow">Bienvenue</p>
            <h2>Connexion</h2>
            <p class="muted">Agriculteur ou administrateur : le même écran, chacun arrive dans son espace.</p>
          </div>
          <label>E-mail <input type="email" formControlName="email" autocomplete="email" placeholder="vous@exemple.tn" /></label>
          <label>Mot de passe <input type="password" formControlName="password" autocomplete="current-password" /></label>
          @if (error()) {
            <p class="error">{{ error() }}</p>
          }
          <button class="btn" type="submit" [disabled]="form.invalid || loading()">
            {{ loading() ? 'Connexion…' : 'Se connecter' }}
          </button>
          <p class="muted">Pas encore de compte ? <a routerLink="/register">Créer un compte agriculteur</a></p>
        </form>
      </div>
    </div>
  `,
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(FormBuilder).nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  submit(): void {
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.form.getRawValue()).subscribe({
      next: () => this.router.navigate(['/']),
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }
}
