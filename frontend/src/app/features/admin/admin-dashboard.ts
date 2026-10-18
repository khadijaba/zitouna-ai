import { Component, computed, inject, OnInit, signal } from '@angular/core';

import { AdminService, MODULE_LABELS } from '../../core/api/admin.service';
import { AdminStats, PredictionType } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';
import { frNumber, frShortDate } from '../../shared/format';

/** Back-office home: totals, activity of the last 30 days, usage per module, live state of the AI services. */
@Component({
  selector: 'app-admin-dashboard',
  template: `
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }
    @if (stats(); as s) {
      <div class="kpis">
        <div class="kpi"><span class="kpi-label">Utilisateurs</span><strong>{{ num(s.users) }}</strong>
          <span class="muted">dont {{ s.admins }} admin{{ s.admins > 1 ? 's' : '' }}</span></div>
        <div class="kpi"><span class="kpi-label">Parcelles</span><strong>{{ num(s.parcels) }}</strong>
          <span class="muted">{{ num(s.areaHa, 1) }} ha au total</span></div>
        <div class="kpi"><span class="kpi-label">Oliviers suivis</span><strong>{{ num(s.trees) }}</strong></div>
        <div class="kpi"><span class="kpi-label">Prédictions IA</span><strong>{{ num(s.predictions) }}</strong>
          <span class="muted">{{ realShare() }} % avec un vrai modèle</span></div>
      </div>

      <div class="grid">
        <section class="card span-2">
          <h2>Activité des 30 derniers jours <small>prédictions par jour</small></h2>
          <div class="activity" role="img" aria-label="Prédictions par jour">
            @for (d of s.last30Days; track d.date) {
              <div class="activity-col" [title]="short(d.date) + ' : ' + d.count">
                <div class="activity-bar" [style.height.%]="(d.count / maxDay()) * 100"></div>
              </div>
            }
          </div>
          <div class="activity-axis muted">
            <span>{{ short(s.last30Days[0].date) }}</span><span>aujourd'hui</span>
          </div>
        </section>

        <section class="card">
          <h2>Utilisation par module</h2>
          @for (row of byType(); track row.type) {
            <div class="hbar-row">
              <span class="hbar-label">{{ row.label }}</span>
              <span class="hbar"><span [style.width.%]="(row.count / maxType()) * 100"></span></span>
              <span class="hbar-value">{{ row.count }}</span>
            </div>
          }
        </section>

        <section class="card">
          <h2>Parcelles par gouvernorat</h2>
          @for (g of s.parcelsByGovernorate; track g.governorate) {
            <div class="hbar-row">
              <span class="hbar-label">{{ g.governorate }}</span>
              <span class="hbar"><span [style.width.%]="(g.parcels / s.parcelsByGovernorate[0].parcels) * 100"></span></span>
              <span class="hbar-value">{{ g.parcels }}</span>
            </div>
          } @empty {
            <p class="muted">Aucune parcelle.</p>
          }
        </section>

        <section class="card span-2">
          <h2>Modules IA <small>état en direct</small></h2>
          <table>
            <thead><tr><th>Module</th><th>Méthode</th><th>État</th><th>Réponse</th></tr></thead>
            <tbody>
              @for (m of s.status.modules; track m.id) {
                <tr>
                  <td><strong>{{ m.id }}</strong> · {{ m.name }}</td>
                  <td class="muted">{{ m.type }}</td>
                  <td>
                    @if (!m.up) {
                      <span class="pill pill-down">Hors ligne</span>
                    } @else if (m.modelLoaded) {
                      <span class="pill pill-ok">Modèle réel</span>
                    } @else {
                      <span class="pill pill-warn">Mode démo</span>
                    }
                  </td>
                  <td class="muted">{{ m.latencyMs === null ? '—' : m.latencyMs + ' ms' }}</td>
                </tr>
              }
            </tbody>
          </table>
          <p class="footnote">
            Backend Spring Boot {{ s.status.application.springBootVersion }} · Java {{ s.status.application.javaVersion }} ·
            base {{ s.status.database.product }} {{ s.status.database.version }}
            ({{ s.status.database.up ? 'en ligne' : 'hors ligne' }})
          </p>
        </section>
      </div>
    }
  `,
})
export class AdminDashboard implements OnInit {
  private readonly admin = inject(AdminService);

  protected readonly stats = signal<AdminStats | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly maxDay = computed(() => Math.max(1, ...(this.stats()?.last30Days ?? []).map((d) => d.count)));
  protected readonly byType = computed(() => {
    const counts = this.stats()?.predictionsByType;
    if (!counts) return [];
    return (Object.keys(MODULE_LABELS) as PredictionType[]).map((type) => ({
      type,
      label: MODULE_LABELS[type],
      count: counts[type] ?? 0,
    }));
  });
  protected readonly maxType = computed(() => Math.max(1, ...this.byType().map((r) => r.count)));
  protected readonly realShare = computed(() => {
    const s = this.stats();
    return !s || s.predictions === 0 ? 100 : Math.round((100 * (s.predictions - s.mockPredictions)) / s.predictions);
  });

  protected readonly num = frNumber;
  protected readonly short = frShortDate;

  ngOnInit(): void {
    this.admin.stats().subscribe({
      next: (s) => this.stats.set(s),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
