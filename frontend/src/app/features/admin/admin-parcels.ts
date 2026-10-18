import { DatePipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';

import { AdminService } from '../../core/api/admin.service';
import { AdminParcel, PageResponse } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';
import { frNumber } from '../../shared/format';

/** Back-office: every parcel of every farmer, search, deletion. */
@Component({
  selector: 'app-admin-parcels',
  imports: [DatePipe],
  template: `
    <form class="toolbar" (submit)="$event.preventDefault(); load(0)">
      <input type="search" placeholder="Nom, gouvernorat ou email du propriétaire" [value]="query()"
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
            <tr><th>Parcelle</th><th>Gouvernorat</th><th>Surface</th><th>Arbres</th><th>Propriétaire</th><th>Créée le</th><th></th></tr>
          </thead>
          <tbody>
            @for (x of p.content; track x.id) {
              <tr>
                <td><strong>{{ x.name }}</strong><br /><span class="muted">{{ x.variety ?? 'variété inconnue' }} ·
                  {{ x.irrigated ? 'irriguée' : 'en sec' }}</span></td>
                <td>{{ x.governorate }}</td>
                <td>{{ x.areaHa === null ? '—' : num(x.areaHa, 1) + ' ha' }}</td>
                <td>{{ x.treeCount === null ? '—' : num(x.treeCount) }}</td>
                <td>{{ x.ownerName }}<br /><span class="muted">{{ x.ownerEmail }}</span></td>
                <td>{{ x.createdAt | date: 'dd/MM/yyyy' }}</td>
                <td><button class="btn btn-danger btn-small" (click)="remove(x)">Supprimer</button></td>
              </tr>
            } @empty {
              <tr><td colspan="7" class="muted">Aucune parcelle trouvée.</td></tr>
            }
          </tbody>
        </table>
      </div>
      <div class="pager">
        <button class="btn btn-ghost" [disabled]="p.page === 0" (click)="load(p.page - 1)">‹ Précédent</button>
        <span class="muted">Page {{ p.page + 1 }} / {{ p.totalPages || 1 }} · {{ p.totalElements }} parcelles</span>
        <button class="btn btn-ghost" [disabled]="p.page + 1 >= p.totalPages" (click)="load(p.page + 1)">Suivant ›</button>
      </div>
    }
  `,
})
export class AdminParcels implements OnInit {
  private readonly admin = inject(AdminService);

  protected readonly page = signal<PageResponse<AdminParcel> | null>(null);
  protected readonly query = signal('');
  protected readonly error = signal<string | null>(null);
  protected readonly num = frNumber;

  ngOnInit(): void {
    this.load(0);
  }

  protected load(page: number): void {
    this.error.set(null);
    this.admin.parcels(this.query().trim(), page).subscribe({
      next: (p) => this.page.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected remove(parcel: AdminParcel): void {
    if (!confirm(`Supprimer la parcelle « ${parcel.name} » de ${parcel.ownerName} ?`)) return;
    this.admin.deleteParcel(parcel.id).subscribe({
      next: () => this.load(this.page()?.page ?? 0),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
