import { Component, effect, inject, input, numberAttribute, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';

import { AiService } from '../../core/api/ai.service';
import { HarvestPlan, Parcel, TreeCountResult, YieldResult } from '../../core/api/models';
import { ParcelService } from '../../core/api/parcel.service';
import { errorMessage, fileFrom } from '../../shared/errors';
import { frNumber } from '../../shared/format';
import { AiExplain } from '../../shared/ai-explain';
import { MockBadge } from '../../shared/mock-badge';
import { IrrigationPanel } from '../irrigation/irrigation-panel';

@Component({
  selector: 'app-parcel-detail',
  imports: [MockBadge, IrrigationPanel, AiExplain],
  template: `
    @if (parcel(); as p) {
      <div class="page-header">
        <h1>{{ p.name }}</h1>
        <button class="btn btn-danger" (click)="remove(p)">Supprimer</button>
      </div>
      <p class="muted">
        {{ p.governorate }} · {{ p.latitude }}, {{ p.longitude }} · {{ p.areaHa ?? '?' }} ha ·
        {{ p.treeCount ?? '?' }} arbres · {{ p.variety ?? 'variété inconnue' }}
      </p>
    }
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    <div class="grid">
      <!-- M2 -->
      <app-irrigation-panel class="span-2" [parcelId]="id()" />

      <!-- M3 -->
      <section class="card">
        <h2>Récolte estimée <small>M3</small></h2>
        <button class="btn" (click)="run(ai.yieldForecast(id()), yieldResult)">Estimer la récolte</button>
        @if (yieldResult(); as y) {
          <app-mock-badge [mock]="y.mock" />
          <p>
            {{ y.scope === 'NATIONAL' ? 'Tunisie (production nationale)' : 'Région ' + y.governorate }},
            saison {{ y.season }}/{{ y.season + 1 }} :
            <strong>{{ num(y.regionalProductionTonnes) }} t d'olives</strong>
            @if (y.scope === 'NATIONAL') {
              <span class="muted">&nbsp;({{ y.observed ? 'chiffre publié par la FAO' : 'prévision du modèle' }})</span>
            }
          </p>
          @if (y.parcelEstimateKg !== null) {
            <p>Votre parcelle : <strong>{{ num(y.parcelEstimateKg) }} kg d'olives</strong>
              ({{ num(y.parcelLowKg ?? 0) }} – {{ num(y.parcelHighKg ?? 0) }})
              @if (y.kgPerTree !== null) {
                · {{ num(y.kgPerTree, 1) }} kg / arbre
              }
            </p>
          } @else {
            <p class="muted">Renseignez la surface ou le nombre d'arbres pour une estimation de la parcelle.</p>
          }
          @if (y.scope === 'NATIONAL') {
            <p class="footnote">Rendement national (FAOSTAT + météo ERA5) appliqué à la surface de la parcelle.</p>
          }
          <app-ai-explain module="M3" [result]="y" />
        }
      </section>

      <!-- M6 -->
      <section class="card">
        <h2>Compter les oliviers <small>M6</small></h2>
        <p class="muted">Image drone ou capture satellite de la parcelle.</p>
        <input type="file" accept="image/*" (change)="countTrees($event)" />
        @if (trees(); as t) {
          <app-mock-badge [mock]="t.mock" />
          <p><strong>{{ t.treeCount }}</strong> arbres détectés</p>
          @if (t.annotatedImageBase64) {
            <img class="preview" [src]="'data:image/png;base64,' + t.annotatedImageBase64" alt="Arbres détectés" />
          }
          <app-ai-explain module="M6" [result]="t" />
        }
      </section>

      <!-- M6 -> M3 -> M4 -->
      <section class="card">
        <h2>Plan de récolte <small>M6 → M3 → M4</small></h2>
        <p class="muted">Image optionnelle : sans image, le nombre d'arbres enregistré est utilisé.</p>
        <input type="file" accept="image/*" (change)="planImage = fileFrom($event)" />
        <button class="btn" (click)="run(ai.harvestPlan(id(), planImage), plan)">Calculer le plan</button>
        @if (plan(); as h) {
          <app-mock-badge [mock]="h.mock" />
          <p>{{ h.summary }}</p>
          <p class="muted">{{ h.price.reason }}</p>
        }
      </section>
    </div>
  `,
})
export class ParcelDetail {
  protected readonly ai = inject(AiService);
  private readonly parcelService = inject(ParcelService);
  private readonly router = inject(Router);

  /** Bound from the route parameter :id (withComponentInputBinding). */
  readonly id = input.required({ transform: numberAttribute });

  protected readonly parcel = signal<Parcel | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly yieldResult = signal<YieldResult | null>(null);
  protected readonly trees = signal<TreeCountResult | null>(null);
  protected readonly plan = signal<HarvestPlan | null>(null);
  protected planImage?: File;
  protected readonly fileFrom = fileFrom;
  protected readonly num = frNumber;

  constructor() {
    effect(() => this.loadParcel(this.id()));
  }

  private loadParcel(id: number): void {
    this.parcelService.get(id).subscribe({
      next: (p) => this.parcel.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  run<T>(call: Observable<T>, target: { set(value: T): void }): void {
    this.error.set(null);
    call.subscribe({
      next: (result) => target.set(result),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  countTrees(event: Event): void {
    const file = fileFrom(event);
    if (!file) return;
    this.error.set(null);
    this.ai.countTrees(this.id(), file).subscribe({
      next: (result) => {
        this.trees.set(result);
        this.loadParcel(this.id());
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  remove(p: Parcel): void {
    if (!confirm(`Supprimer la parcelle « ${p.name} » ?`)) return;
    this.parcelService.delete(p.id).subscribe(() => this.router.navigate(['/parcels']));
  }
}
