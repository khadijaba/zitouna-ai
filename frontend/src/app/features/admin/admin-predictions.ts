import { DatePipe, JsonPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';

import { AdminService, MODULE_LABELS } from '../../core/api/admin.service';
import { AdminPrediction, PageResponse, PredictionType } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';

/** Back-office: every AI call of every user, filter by module, request / response details. */
@Component({
  selector: 'app-admin-predictions',
  imports: [DatePipe, JsonPipe],
  template: `
    <div class="toolbar">
      <select (change)="setType($any($event.target).value)">
        <option value="">Tous les modules</option>
        @for (t of types; track t) {
          <option [value]="t" [selected]="t === type()">{{ labels[t] }}</option>
        }
      </select>
    </div>
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }
    @if (page(); as p) {
      <div class="table-card">
        <table>
          <thead><tr><th>Date</th><th>Module</th><th>Utilisateur</th><th>Parcelle</th><th>Détail</th></tr></thead>
          <tbody>
            @for (r of p.content; track r.id) {
              <tr>
                <td>{{ r.createdAt | date: 'dd/MM/yyyy HH:mm' }}</td>
                <td>{{ labels[r.type] }} @if (r.mock) {<span class="badge badge-mock">démo</span>}</td>
                <td>{{ r.userEmail }}</td>
                <td>{{ r.parcelName ?? '—' }}</td>
                <td>
                  <details>
                    <summary>voir</summary>
                    <p class="muted">Requête</p><pre>{{ r.request | json }}</pre>
                    <p class="muted">Réponse</p><pre>{{ r.response | json }}</pre>
                  </details>
                </td>
              </tr>
            } @empty {
              <tr><td colspan="5" class="muted">Aucune prédiction.</td></tr>
            }
          </tbody>
        </table>
      </div>
      <div class="pager">
        <button class="btn btn-ghost" [disabled]="p.page === 0" (click)="load(p.page - 1)">‹ Précédent</button>
        <span class="muted">Page {{ p.page + 1 }} / {{ p.totalPages || 1 }} · {{ p.totalElements }} prédictions</span>
        <button class="btn btn-ghost" [disabled]="p.page + 1 >= p.totalPages" (click)="load(p.page + 1)">Suivant ›</button>
      </div>
    }
  `,
})
export class AdminPredictions implements OnInit {
  private readonly admin = inject(AdminService);

  protected readonly labels = MODULE_LABELS;
  protected readonly types = Object.keys(MODULE_LABELS) as PredictionType[];
  protected readonly type = signal<PredictionType | null>(null);
  protected readonly page = signal<PageResponse<AdminPrediction> | null>(null);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.load(0);
  }

  protected setType(value: string): void {
    this.type.set((value || null) as PredictionType | null);
    this.load(0);
  }

  protected load(page: number): void {
    this.error.set(null);
    this.admin.predictions(this.type(), page).subscribe({
      next: (p) => this.page.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
