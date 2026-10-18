import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

/**
 * Back-office frame (sections are in the sidebar, see layout/shell.ts). Reachable only by the admin account
 * (adminGuard + backend role check).
 */
@Component({
  selector: 'app-admin-layout',
  imports: [RouterOutlet],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">Back-office</p>
        <h1>Administration</h1>
        <p class="muted">Utilisateurs, parcelles, prédictions et état des modèles IA de la plateforme.</p>
      </div>
      <span class="badge admin-badge">ADMIN</span>
    </header>
    <router-outlet />
  `,
})
export class AdminLayout {}
