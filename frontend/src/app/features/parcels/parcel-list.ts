import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { Parcel } from '../../core/api/models';
import { ParcelService } from '../../core/api/parcel.service';
import { errorMessage } from '../../shared/errors';

export const GOVERNORATES = [
  'Ariana', 'Béja', 'Ben Arous', 'Bizerte', 'Gabès', 'Gafsa', 'Jendouba', 'Kairouan', 'Kasserine',
  'Kébili', 'Le Kef', 'Mahdia', 'La Manouba', 'Médenine', 'Monastir', 'Nabeul', 'Sfax',
  'Sidi Bouzid', 'Siliana', 'Sousse', 'Tataouine', 'Tozeur', 'Tunis', 'Zaghouan',
];

@Component({
  selector: 'app-parcel-list',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <h1>Mes parcelles</h1>
    @if (error()) {
      <p class="error">{{ error() }}</p>
    }

    <div class="grid">
      @for (p of parcels(); track p.id) {
        <a class="card card-link" [routerLink]="['/parcels', p.id]">
          <h3>{{ p.name }}</h3>
          <p class="muted">{{ p.governorate }} · {{ p.areaHa ?? '?' }} ha · {{ p.treeCount ?? '?' }} arbres</p>
          <p class="muted">{{ p.variety ?? 'Variété inconnue' }} · {{ p.irrigated ? 'irriguée' : 'en sec' }}</p>
        </a>
      } @empty {
        <p class="muted">Aucune parcelle. Ajoutez-en une ci-dessous.</p>
      }
    </div>

    <form class="card" [formGroup]="form" (ngSubmit)="create()">
      <h2>Ajouter une parcelle</h2>
      <div class="form-row">
        <label>Nom <input formControlName="name" /></label>
        <label>
          Gouvernorat
          <select formControlName="governorate">
            @for (g of governorates; track g) {
              <option [value]="g">{{ g }}</option>
            }
          </select>
        </label>
        <label>Variété <input formControlName="variety" placeholder="Chemlali, Chetoui…" /></label>
      </div>
      <div class="form-row">
        <label>Latitude <input type="number" step="any" formControlName="latitude" /></label>
        <label>Longitude <input type="number" step="any" formControlName="longitude" /></label>
        <label>Surface (ha) <input type="number" step="any" formControlName="areaHa" /></label>
        <label>Nombre d'arbres <input type="number" formControlName="treeCount" /></label>
      </div>
      <label class="checkbox"><input type="checkbox" formControlName="irrigated" /> Parcelle irriguée</label>
      <button class="btn" type="submit" [disabled]="form.invalid">Ajouter</button>
    </form>
  `,
})
export class ParcelList implements OnInit {
  private readonly parcelService = inject(ParcelService);

  protected readonly governorates = GOVERNORATES;
  protected readonly parcels = signal<Parcel[]>([]);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(FormBuilder).group({
    name: ['', Validators.required],
    governorate: ['Sfax', Validators.required],
    latitude: [34.74, Validators.required],
    longitude: [10.76, Validators.required],
    areaHa: [null as number | null],
    treeCount: [null as number | null],
    variety: [null as string | null],
    irrigated: [false],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.parcelService.list().subscribe({
      next: (p) => this.parcels.set(p),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  create(): void {
    const v = this.form.getRawValue();
    this.parcelService
      .create({
        name: v.name!,
        governorate: v.governorate!,
        latitude: v.latitude!,
        longitude: v.longitude!,
        areaHa: v.areaHa,
        treeCount: v.treeCount,
        variety: v.variety,
        irrigated: !!v.irrigated,
      })
      .subscribe({
        next: () => {
          this.form.reset({ governorate: 'Sfax', latitude: 34.74, longitude: 10.76, irrigated: false });
          this.load();
        },
        error: (err) => this.error.set(errorMessage(err)),
      });
  }
}
