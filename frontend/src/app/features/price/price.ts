import { Component, computed, inject, OnInit, signal } from '@angular/core';

import { AiService } from '../../core/api/ai.service';
import { PriceResult } from '../../core/api/models';
import { errorMessage } from '../../shared/errors';
import { frMonth, frNumber, frShortDate } from '../../shared/format';
import { MockBadge } from '../../shared/mock-badge';
import { PriceChart } from '../../shared/price-chart';

/** M4 · Olive-oil price forecast and sell / store advice. */
@Component({
  selector: 'app-price',
  imports: [MockBadge, PriceChart],
  template: `
    <h1>Prix de l'huile d'olive</h1>
    <p class="muted">Prévision du prix et conseil : vendre maintenant ou stocker l'huile pour vendre plus tard.</p>

    <form class="card controls" (submit)="$event.preventDefault(); load()">
      <label>
        Horizon
        <select (change)="horizon.set(+$any($event.target).value)">
          @for (w of horizons; track w) {
            <option [value]="w" [selected]="w === horizon()">{{ w }} semaines</option>
          }
        </select>
      </label>
      <label>
        Quantité d'huile à vendre (kg)
        <input type="number" min="0" step="50" placeholder="ex. 1500" [value]="quantity() ?? ''"
               (input)="quantity.set(+$any($event.target).value || null)" />
      </label>
      <button class="btn" type="submit" [disabled]="loading()">{{ loading() ? 'Calcul…' : 'Mettre à jour' }}</button>
    </form>

    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    @if (result(); as r) {
      <section class="card rec" [class.rec-store]="r.recommendation === 'STORE'" [class.rec-sell]="r.recommendation === 'SELL_NOW'">
        <h2>
          {{ r.recommendation === 'STORE' ? '📦 Conseil : stocker et attendre' : '💰 Conseil : vendre maintenant' }}
          <app-mock-badge [mock]="r.mock" />
        </h2>
        <p>{{ r.reason }}</p>
        @if (r.expectedGainTnd) {
          <p>Gain estimé pour {{ num(quantity() ?? 0) }} kg : <strong>+{{ num(r.expectedGainTnd) }} {{ r.currency }}</strong></p>
        }
      </section>

      <div class="kpis">
        @if (stats(); as s) {
          <div class="kpi">
            <span class="kpi-label">Dernier prix publié ({{ month(s.last.date) }})</span>
            <strong>{{ num(s.last.price, 2) }} {{ r.currency }}/{{ r.unit }}</strong>
          </div>
          <div class="kpi">
            <span class="kpi-label">Prix prévu le {{ short(s.end.date) }}</span>
            <strong>{{ num(s.end.price, 2) }} {{ r.currency }}/{{ r.unit }}</strong>
            @if (s.end.low !== null && s.end.high !== null) {
              <span class="muted">entre {{ num(s.end.low, 2) }} et {{ num(s.end.high, 2) }}</span>
            }
          </div>
          <div class="kpi">
            <span class="kpi-label">Meilleur prix prévu</span>
            <strong>{{ num(s.best.price, 2) }} {{ r.currency }}/{{ r.unit }}</strong>
            <span class="muted">vers le {{ short(s.best.date) }}</span>
          </div>
        }
      </div>

      <section class="card">
        <h2>Évolution et prévision <small>{{ r.currency }}/{{ r.unit }} d'huile</small></h2>
        <app-price-chart [history]="r.history" [forecast]="r.forecast" [unit]="r.currency + '/' + r.unit" />
        <details>
          <summary>Détail de la prévision semaine par semaine</summary>
          <table>
            <thead><tr><th>Semaine du</th><th>Prix prévu</th><th>Intervalle à 80 %</th></tr></thead>
            <tbody>
              @for (p of r.forecast; track p.date) {
                <tr>
                  <td>{{ short(p.date) }}</td>
                  <td>{{ num(p.price, 2) }}</td>
                  <td>{{ p.low === null ? '—' : num(p.low, 2) + ' – ' + num(p.high!, 2) }}</td>
                </tr>
              }
            </tbody>
          </table>
        </details>
        <p class="footnote">
          @if (r.source) {
            Source : {{ r.source }}. Modèle {{ r.modelVersion }}, réajusté sur toute la série au démarrage.
          } @else {
            Données de démonstration (aucun modèle chargé).
          }
          Coût de stockage pris en compte : 0,15 TND/kg/mois.
        </p>
      </section>
    }
  `,
})
export class Price implements OnInit {
  private readonly ai = inject(AiService);

  protected readonly horizons = [4, 8, 12, 26];
  protected readonly horizon = signal(12);
  protected readonly quantity = signal<number | null>(null);
  protected readonly result = signal<PriceResult | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly stats = computed(() => {
    const r = this.result();
    const last = r?.history.at(-1);
    const end = r?.forecast.at(-1);
    if (!r || !last || !end) return null;
    const best = r.forecast.reduce((a, b) => (b.price > a.price ? b : a));
    return { last, end, best };
  });

  protected readonly num = frNumber;
  protected readonly short = frShortDate;
  protected readonly month = frMonth;

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.ai.price(this.horizon(), this.quantity()).subscribe({
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
