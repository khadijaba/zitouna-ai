import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { errorMessage } from '../../shared/errors';
import { AuthHero } from './auth-hero';

@Component({
  selector: 'app-register',
  imports: [ReactiveFormsModule, RouterLink, AuthHero],
  template: `
    <div class="auth-page">
      <app-auth-hero />
      <div class="auth-panel">
        <form [formGroup]="form" (ngSubmit)="submit()">
          <div>
            <p class="eyebrow">Nouveau</p>
            <h2>Créer un compte agriculteur</h2>
            <p class="muted">Gratuit. Ajoutez ensuite vos parcelles pour utiliser les outils d'IA.</p>
          </div>
          <label>Nom complet <input formControlName="fullName" autocomplete="name" placeholder="Salah Ben Ali" /></label>
          <label>E-mail <input type="email" formControlName="email" autocomplete="email" placeholder="vous@exemple.tn" /></label>
          <label>
            Mot de passe (8 caractères minimum)
            <input type="password" formControlName="password" autocomplete="new-password" />
          </label>
          @if (error()) {
            <p class="error">{{ error() }}</p>
          }
          <button class="btn" type="submit" [disabled]="form.invalid || loading()">
            {{ loading() ? 'Création…' : 'Créer mon compte' }}
          </button>
          <p class="muted">Déjà inscrit ? <a routerLink="/login">Se connecter</a></p>
        </form>
      </div>
    </div>
  `,
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(FormBuilder).nonNullable.group({
    fullName: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  submit(): void {
    this.loading.set(true);
    this.error.set(null);
    this.auth.register(this.form.getRawValue()).subscribe({
      next: () => this.router.navigate(['/home']),
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }
}
