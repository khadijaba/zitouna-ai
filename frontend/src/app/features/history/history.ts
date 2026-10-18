import { DatePipe, JsonPipe } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AiService } from '../../core/api/ai.service';
import { PageResponse, PredictionRecord, PredictionType } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';

@Component({
  selector: 'app-history',
  imports: [DatePipe, JsonPipe, FormsModule],
  template: `
    <div class="page-header">
      <h1>Historique</h1>
      <select [(ngModel)]="type" (ngModelChange)="load(0)">
        <option [ngValue]="undefined">Tous les modules</option>
        @for (t of types; track t) {
          <option [ngValue]="t">{{ t }}</option>
        }
      </select>
    </div>
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    @if (page(); as p) {
      <table class="card">
        <tr><th>Date</th><th>Module</th><th>Parcelle</th><th>Résultat</th></tr>
        @for (r of p.content; track r.id) {
          <tr>
            <td>{{ r.createdAt | date: 'short' }}</td>
            <td>{{ r.type }} @if (r.mock) {<span class="badge badge-mock">démo</span>}</td>
            <td>{{ r.parcelName ?? '—' }}</td>
            <td><details><summary>voir</summary><pre>{{ r.response | json }}</pre></details></td>
          </tr>
        } @empty {
          <tr><td colspan="4" class="muted">Aucune prédiction pour le moment.</td></tr>
        }
      </table>
      <div class="pager">
        <button class="btn btn-ghost" [disabled]="p.page === 0" (click)="load(p.page - 1)">‹ Précédent</button>
        <span class="muted">Page {{ p.page + 1 }} / {{ p.totalPages || 1 }}</span>
        <button class="btn btn-ghost" [disabled]="p.page + 1 >= p.totalPages" (click)="load(p.page + 1)">Suivant ›</button>
      </div>
    }
  `,
})
export class History implements OnInit {
  private readonly ai = inject(AiService);

  protected readonly types: PredictionType[] = [
    'DISEASE', 'IRRIGATION', 'YIELD', 'PRICE', 'CHAT', 'TREE_COUNT', 'HARVEST_PLAN',
  ];
  protected readonly page = signal<PageResponse<PredictionRecord> | null>(null);
  protected readonly error = signal<string | null>(null);
  protected type?: PredictionType;

  ngOnInit(): void {
    this.load(0);
  }

  load(page: number): void {
    this.ai.history(this.type, page).subscribe({
      next: (p) => this.page.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
