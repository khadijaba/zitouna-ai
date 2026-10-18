import { Component, computed, effect, inject, input, signal } from '@angular/core';

import { AiService } from '../../core/api/ai.service';
import { IrrigationResult } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';
import { frDay, frNumber } from '../../shared/format';
import { AiExplain } from '../../shared/ai-explain';
import { MockBadge } from '../../shared/mock-badge';

/** M2 · Irrigation plan + frost / heatwave alerts for one parcel. Loads itself when the parcel or horizon changes. */
@Component({
  selector: 'app-irrigation-panel',
  imports: [MockBadge, AiExplain],
  template: `
    <section class="card">
      <div class="card-head">
        <h2>Irrigation & alertes <small>M2</small></h2>
        <div class="seg" role="group" aria-label="Horizon">
          @for (n of [7, 14]; track n) {
            <button type="button" [class.active]="days() === n" (click)="days.set(n)">{{ n }} jours</button>
          }
        </div>
      </div>

      @if (loading()) {
        <p class="muted">Calcul du plan d'irrigation…</p>
      }
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }

      @if (result(); as r) {
        <app-mock-badge [mock]="r.mock" />

        @for (a of r.alerts; track a.date + a.type) {
          <p class="alert" [class.alert-high]="a.severity === 'HIGH'">
            {{ a.type === 'FROST' ? '❄️' : '🔥' }} <strong>{{ day(a.date) }}</strong> — {{ a.message }}
          </p>
        } @empty {
          <p class="ok">✅ Aucune alerte de gel ni de canicule sur la période.</p>
        }

        <div class="kpis">
          <div class="kpi">
            <span class="kpi-label">Jours à irriguer</span>
            <strong>{{ summary().irrigateDays }} / {{ r.days.length }}</strong>
          </div>
          <div class="kpi">
            <span class="kpi-label">Besoin total</span>
            <strong>{{ num(summary().totalNeedMm, 1) }} mm</strong>
          </div>
          <div class="kpi">
            <span class="kpi-label">Par arbre</span>
            <strong>{{ summary().totalLiters === null ? '—' : num(summary().totalLiters!) + ' L' }}</strong>
          </div>
        </div>

        <table class="water">
          <thead>
            <tr><th>Jour</th><th>ET₀</th><th>Pluie</th><th>Besoin en eau</th><th>L / arbre</th></tr>
          </thead>
          <tbody>
            @for (d of r.days; track d.date) {
              <tr [class.highlight]="d.irrigate">
                <td>{{ day(d.date) }}</td>
                <td>{{ num(d.et0Mm, 1) }}</td>
                <td>{{ d.rainMm > 0 ? '🌧 ' + num(d.rainMm, 1) : '—' }}</td>
                <td>
                  <span class="water-bar" [style.width.%]="(d.waterNeedMm / summary().maxNeed) * 100"></span>
                  {{ num(d.waterNeedMm, 1) }} mm
                </td>
                <td>{{ d.litersPerTree === null ? '—' : num(d.litersPerTree) }}</td>
              </tr>
            }
          </tbody>
        </table>
        @if (summary().totalLiters === null) {
          <p class="muted">Renseignez la surface et le nombre d'arbres de la parcelle pour avoir les litres par arbre.</p>
        }
        <p class="footnote">
          Lignes vertes : irrigation conseillée (besoin ≥ 2 mm). Besoin = ET₀ × 0,65 − 0,8 × pluie (FAO-56).
          @if (!r.mock) {
            ET₀ prévue par le modèle {{ r.modelVersion }} (LSTM) · pluie et températures : prévisions Open-Meteo.
          }
        </p>
        <app-ai-explain module="M2" [result]="r" />
      }
    </section>
  `,
})
export class IrrigationPanel {
  private readonly ai = inject(AiService);

  readonly parcelId = input.required<number>();

  protected readonly days = signal(7);
  protected readonly result = signal<IrrigationResult | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly summary = computed(() => {
    const days = this.result()?.days ?? [];
    const liters = days.map((d) => d.litersPerTree);
    return {
      irrigateDays: days.filter((d) => d.irrigate).length,
      totalNeedMm: days.reduce((sum, d) => sum + d.waterNeedMm, 0),
      totalLiters: liters.some((l) => l === null) ? null : liters.reduce((sum, l) => sum! + l!, 0),
      maxNeed: Math.max(1, ...days.map((d) => d.waterNeedMm)),
    };
  });

  protected readonly day = frDay;
  protected readonly num = frNumber;

  constructor() {
    effect(() => this.load(this.parcelId(), this.days()));
  }

  private load(parcelId: number, days: number): void {
    this.loading.set(true);
    this.error.set(null);
    this.ai.irrigation(parcelId, days).subscribe({
      next: (r) => {
        this.result.set(r);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }
}
