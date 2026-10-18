import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';

import { AdminService } from '../../core/api/admin.service';
import { AdminUser, PageResponse } from '../../core/api/models';
import { AuthService } from '../../core/auth/auth.service';
import { errorMessage } from '../../shared/errors';

/**
 * Back-office: every account, search, deletion of farmer accounts. The single admin account is defined in .env:
 * no role change here, and it cannot be deleted.
 */
@Component({
  selector: 'app-admin-users',
  imports: [DatePipe],
  template: `
    <form class="toolbar" (submit)="$event.preventDefault(); load(0)">
      <input type="search" placeholder="Rechercher un nom ou un email" [value]="query()"
             (input)="query.set($any($event.target).value)" />
      <button class="btn" type="submit">Rechercher</button>
    </form>
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }
    @if (page(); as p) {
      <div class="table-card">
        <table>
          <thead>
            <tr><th>Nom</th><th>Email</th><th>Rôle</th><th>Parcelles</th><th>Prédictions</th><th>Inscrit le</th><th></th></tr>
          </thead>
          <tbody>
            @for (u of p.content; track u.id) {
              <tr>
                <td>{{ u.fullName }} @if (u.id === me()) {<span class="muted">(vous)</span>}</td>
                <td>{{ u.email }}</td>
                <td>
                  @if (u.role === 'ADMIN') {
                    <span class="pill pill-ok">Administrateur</span>
                  } @else {
                    <span class="pill">Agriculteur</span>
                  }
                </td>
                <td>{{ u.parcels }}</td>
                <td>{{ u.predictions }}</td>
                <td>{{ u.createdAt | date: 'dd/MM/yyyy' }}</td>
                <td>
                  @if (u.role !== 'ADMIN') {
                    <button class="btn btn-danger btn-small" (click)="remove(u)">Supprimer</button>
                  }
                </td>
              </tr>
            } @empty {
              <tr><td colspan="7" class="muted">Aucun utilisateur trouvé.</td></tr>
            }
          </tbody>
        </table>
      </div>
      <div class="pager">
        <button class="btn btn-ghost" [disabled]="p.page === 0" (click)="load(p.page - 1)">‹ Précédent</button>
        <span class="muted">Page {{ p.page + 1 }} / {{ p.totalPages || 1 }} · {{ p.totalElements }} comptes</span>
        <button class="btn btn-ghost" [disabled]="p.page + 1 >= p.totalPages" (click)="load(p.page + 1)">Suivant ›</button>
      </div>
    }
  `,
})
export class AdminUsers implements OnInit {
  private readonly admin = inject(AdminService);
  private readonly auth = inject(AuthService);

  protected readonly page = signal<PageResponse<AdminUser> | null>(null);
  protected readonly query = signal('');
  protected readonly error = signal<string | null>(null);
  protected readonly me = () => this.auth.user()?.id;

  ngOnInit(): void {
    this.load(0);
  }

  protected load(page: number): void {
    this.error.set(null);
    this.admin.users(this.query().trim(), page).subscribe({
      next: (p) => this.page.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected remove(user: AdminUser): void {
    if (!confirm(`Supprimer le compte de ${user.fullName} (${user.email}) ? Ses parcelles et son historique seront aussi supprimés.`)) {
      return;
    }
    this.admin.deleteUser(user.id).subscribe({
      next: () => this.load(this.page()?.page ?? 0),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
