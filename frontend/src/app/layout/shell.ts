import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/auth/auth.service';
import { Icon } from '../shared/icon';

interface NavLink {
  path: string;
  label: string;
  icon: string;
  exact?: boolean;
}

interface NavSection {
  title: string;
  links: NavLink[];
}

/** Farmers use the AI tools; the single admin account only sees the back-office. */
const FARMER_NAV: NavSection[] = [
  {
    title: 'Mon exploitation',
    links: [
      { path: '/home', label: 'Accueil', icon: 'home' },
      { path: '/parcels', label: 'Parcelles', icon: 'map' },
    ],
  },
  {
    title: 'Outils IA',
    links: [
      { path: '/diagnosis', label: 'Diagnostic des feuilles', icon: 'leaf' },
      { path: '/irrigation', label: 'Irrigation & météo', icon: 'droplet' },
      { path: '/price', label: "Prix de l'huile", icon: 'coins' },
      { path: '/assistant', label: 'Assistant derja', icon: 'chat' },
    ],
  },
  { title: 'Suivi', links: [{ path: '/history', label: 'Historique', icon: 'history' }] },
];

const ADMIN_NAV: NavSection[] = [
  {
    title: 'Administration',
    links: [
      { path: '/admin', label: 'Tableau de bord', icon: 'gauge', exact: true },
      { path: '/admin/users', label: 'Utilisateurs', icon: 'users' },
      { path: '/admin/parcels', label: 'Parcelles', icon: 'map' },
      { path: '/admin/predictions', label: 'Prédictions IA', icon: 'list' },
    ],
  },
];

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  template: `
    <div class="app">
      <aside class="sidebar">
        <a routerLink="/" class="brand">
          <span class="brand-mark">
            <svg viewBox="0 0 32 32" width="34" height="34" aria-hidden="true">
              <ellipse cx="16" cy="18" rx="9" ry="11" fill="#9aab4f" />
              <ellipse cx="13" cy="15" rx="2.6" ry="4" fill="#c4d27f" opacity=".7" />
              <path d="M16 7c3-4 8-5 11-4-2 4-6 6-11 4z" fill="#d9b43c" />
            </svg>
          </span>
          <span>
            <strong>Zitouna AI</strong>
            <small>L'oléiculture intelligente</small>
          </span>
        </a>

        <nav class="side-nav">
          @for (section of nav(); track section.title) {
            <p class="side-title">{{ section.title }}</p>
            @for (link of section.links; track link.path) {
              <a [routerLink]="link.path" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: !!link.exact }">
                <app-icon [name]="link.icon" [size]="18" />
                <span>{{ link.label }}</span>
              </a>
            }
          }
        </nav>

        <div class="side-user">
          <span class="avatar">{{ initials() }}</span>
          <span class="side-user-text">
            <strong>{{ auth.user()?.fullName }}</strong>
            <small>{{ auth.isAdmin() ? 'Administrateur' : 'Agriculteur' }}</small>
          </span>
          <button class="icon-btn" type="button" title="Déconnexion" aria-label="Déconnexion" (click)="auth.logout()">
            <app-icon name="logout" [size]="18" />
          </button>
        </div>
      </aside>

      <main class="content">
        <div class="container">
          <router-outlet />
        </div>
      </main>
    </div>
  `,
})
export class Shell {
  protected readonly auth = inject(AuthService);
  protected readonly nav = computed(() => (this.auth.isAdmin() ? ADMIN_NAV : FARMER_NAV));
  protected readonly initials = computed(() =>
    (this.auth.user()?.fullName ?? '?')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]!.toUpperCase())
      .join(''),
  );
}
