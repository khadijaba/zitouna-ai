import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Parcel } from '../../core/api/models';
import { ParcelService } from '../../core/api/parcel.service';
import { errorMessage } from '../../shared/errors';
import { IrrigationPanel } from './irrigation-panel';

/** M2 · Irrigation page: pick a parcel, see its plan and alerts. */
@Component({
  selector: 'app-irrigation',
  imports: [IrrigationPanel, RouterLink],
  template: `
    <h1>Irrigation & alertes météo</h1>
    <p class="muted">
      Besoin en eau de vos oliviers pour les prochains jours, calculé à partir de la météo de la parcelle.
    </p>
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    @if (parcels().length) {
      <label class="inline">
        Parcelle
        <select (change)="select($event)">
          @for (p of parcels(); track p.id) {
            <option [value]="p.id" [selected]="p.id === selected()">{{ p.name }} — {{ p.governorate }}</option>
          }
        </select>
      </label>
      @if (selected(); as id) {
        <app-irrigation-panel [parcelId]="id" />
      }
    } @else if (loaded()) {
      <p class="card">Aucune parcelle pour l'instant. <a routerLink="/parcels">Ajoutez une parcelle</a> pour avoir son plan d'irrigation.</p>
    }
  `,
})
export class Irrigation implements OnInit {
  private readonly parcelService = inject(ParcelService);

  protected readonly parcels = signal<Parcel[]>([]);
  protected readonly selected = signal<number | null>(null);
  protected readonly loaded = signal(false);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.parcelService.list().subscribe({
      next: (list) => {
        this.parcels.set(list);
        this.selected.set(list[0]?.id ?? null);
        this.loaded.set(true);
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected select(event: Event): void {
    this.selected.set(Number((event.target as HTMLSelectElement).value));
  }
}
