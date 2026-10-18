import { DatePipe } from '@angular/common';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MODULE_LABELS } from '../../core/api/admin.service';
import { AiService } from '../../core/api/ai.service';
import { PageResponse, Parcel, PredictionRecord } from '../../core/api/models';
import { ParcelService } from '../../core/api/parcel.service';
import { AuthService } from '../../core/auth/auth.service';
import { errorMessage } from '../../shared/errors';
import { frNumber } from '../../shared/format';
import { Icon } from '../../shared/icon';

interface Tool {
  module: string;
  title: string;
  text: string;
  icon: string;
  link: string;
}

/** Farmer home: summary of the farm, the six AI tools, parcels and recent activity. */
@Component({
  selector: 'app-home',
  imports: [RouterLink, DatePipe, Icon],
  template: `
    <header class="page-head">
      <div>
        <p class="eyebrow">{{ today }}</p>
        <h1>Bonjour {{ firstName() }} 👋</h1>
        <p class="muted">Voici l'essentiel de votre exploitation et vos outils d'aide à la décision.</p>
      </div>
      <a class="btn btn-gold" routerLink="/parcels"><app-icon name="plus" [size]="18" /> Ajouter une parcelle</a>
    </header>

    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    <div class="kpis">
      <div class="kpi"><span class="kpi-label">Parcelles</span><strong>{{ parcels().length }}</strong></div>
      <div class="kpi"><span class="kpi-label">Oliviers</span><strong>{{ num(totals().trees) }}</strong></div>
      <div class="kpi"><span class="kpi-label">Surface</span><strong>{{ num(totals().area, 1) }} ha</strong></div>
      <div class="kpi"><span class="kpi-label">Analyses IA réalisées</span><strong>{{ history()?.totalElements ?? 0 }}</strong></div>
    </div>

    <h2 class="section-title">Vos outils d'intelligence artificielle</h2>
    <div class="tools">
      @for (t of tools(); track t.module) {
        <a class="tool card card-link" [routerLink]="t.link">
          <span class="tool-icon"><app-icon [name]="t.icon" [size]="22" /></span>
          <span class="tool-module">{{ t.module }}</span>
          <h3>{{ t.title }}</h3>
          <p class="muted">{{ t.text }}</p>
          <span class="tool-go">Ouvrir <app-icon name="arrow" [size]="16" /></span>
        </a>
      }
    </div>

    <div class="grid two">
      <section class="card">
        <div class="card-head">
          <h2>Mes parcelles</h2>
          <a routerLink="/parcels">Tout voir</a>
        </div>
        @for (p of parcels().slice(0, 4); track p.id) {
          <a class="row-link" [routerLink]="['/parcels', p.id]">
            <span class="row-icon"><app-icon name="map" [size]="18" /></span>
            <span class="row-main"><strong>{{ p.name }}</strong>
              <small class="muted">{{ p.governorate }} · {{ p.areaHa ?? '?' }} ha · {{ p.treeCount ?? '?' }} arbres</small></span>
            <app-icon name="arrow" [size]="16" />
          </a>
        } @empty {
          <p class="muted">Aucune parcelle pour l'instant. <a routerLink="/parcels">Ajoutez votre première parcelle</a>
            pour l'irrigation, la récolte et le comptage des arbres.</p>
        }
      </section>

      <section class="card">
        <div class="card-head">
          <h2>Activité récente</h2>
          <a routerLink="/history">Historique</a>
        </div>
        @for (r of history()?.content ?? []; track r.id) {
          <div class="row-link static">
            <span class="row-icon"><app-icon name="sparkles" [size]="18" /></span>
            <span class="row-main"><strong>{{ labels[r.type] }}</strong>
              <small class="muted">{{ r.parcelName ?? 'sans parcelle' }} · {{ r.createdAt | date: 'dd/MM/yyyy HH:mm' }}</small></span>
          </div>
        } @empty {
          <p class="muted">Vos diagnostics, plans d'irrigation et prévisions apparaîtront ici.</p>
        }
      </section>
    </div>
  `,
})
export class Home implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly parcelService = inject(ParcelService);
  private readonly ai = inject(AiService);

  protected readonly parcels = signal<Parcel[]>([]);
  protected readonly history = signal<PageResponse<PredictionRecord> | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly labels = MODULE_LABELS;
  protected readonly num = frNumber;
  protected readonly today = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
    .format(new Date());

  protected readonly firstName = computed(() => (this.auth.user()?.fullName ?? '').split(/\s+/)[0] ?? '');
  protected readonly totals = computed(() => ({
    trees: this.parcels().reduce((sum, p) => sum + (p.treeCount ?? 0), 0),
    area: this.parcels().reduce((sum, p) => sum + (p.areaHa ?? 0), 0),
  }));
  /** Tools that need a parcel open the first one (or the parcel list when there is none). */
  protected readonly tools = computed<Tool[]>(() => {
    const first = this.parcels()[0];
    const parcelLink = first ? `/parcels/${first.id}` : '/parcels';
    return [
      { module: 'M1', title: 'Diagnostic des feuilles', text: "Photo d'une feuille : maladie, conseil et zone malade.", icon: 'leaf', link: '/diagnosis' },
      { module: 'M2', title: 'Irrigation & météo', text: "Litres d'eau par arbre et alertes gel / canicule.", icon: 'droplet', link: '/irrigation' },
      { module: 'M3', title: 'Récolte estimée', text: "Kilos d'olives attendus pour votre parcelle.", icon: 'chart', link: parcelLink },
      { module: 'M4', title: "Prix de l'huile", text: 'Prévision du prix : vendre maintenant ou stocker.', icon: 'coins', link: '/price' },
      { module: 'M5', title: 'Assistant en derja', text: 'Posez vos questions comme vous parlez.', icon: 'chat', link: '/assistant' },
      { module: 'M6', title: 'Comptage des oliviers', text: 'Image satellite ou drone : nombre d’arbres.', icon: 'trees', link: parcelLink },
    ];
  });

  ngOnInit(): void {
    this.parcelService.list().subscribe({
      next: (p) => this.parcels.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
    this.ai.history(undefined, 0).subscribe({
      next: (h) => this.history.set({ ...h, content: h.content.slice(0, 5) }),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
