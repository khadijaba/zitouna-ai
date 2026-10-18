import { PercentPipe } from '@angular/common';
import { Component, inject, OnDestroy, signal } from '@angular/core';

import { AiService } from '../../core/api/ai.service';
import { DiseaseResult } from '../../core/api/models';
import { errorMessage, fileFrom } from '../../shared/errors';
import { AiExplain } from '../../shared/ai-explain';
import { MockBadge } from '../../shared/mock-badge';

/** M1 · Leaf diseases */
@Component({
  selector: 'app-diagnosis',
  imports: [PercentPipe, MockBadge, AiExplain],
  template: `
    <h1>Diagnostic d'une feuille</h1>
    <p class="muted">Photographiez une feuille d'olivier, de près et bien éclairée.</p>

    <div class="grid">
      <section class="card">
        <input type="file" accept="image/*" capture="environment" (change)="onFile($event)" />
        @if (previewUrl()) {
          <img class="preview" [src]="previewUrl()" alt="Feuille envoyée" />
        }
        @if (loading()) {
          <p class="muted">Analyse en cours…</p>
        }
        @if (error()) {
          <p class="error">{{ error() }}</p>
        }
      </section>

      @if (result(); as r) {
        <section class="card">
          @if (r.lowConfidence) {
            <h2>📷 Photo peu claire <app-mock-badge [mock]="r.mock" /></h2>
            <p class="alert">{{ r.advice }}</p>
            <p class="muted">Le modèle n'est pas assez sûr ({{ r.confidence | percent: '1.0-0' }}) pour donner un diagnostic.</p>
          } @else {
            <h2>{{ r.labelFr }} <app-mock-badge [mock]="r.mock" /></h2>
            <p>Confiance : <strong>{{ r.confidence | percent: '1.0-0' }}</strong></p>
            <p>{{ r.advice }}</p>
          }
          @if (r.heatmapBase64 && !r.lowConfidence) {
            <p class="muted">Zone utilisée par le modèle pour décider (Grad-CAM, rouge = important) :</p>
            <img class="preview" [src]="'data:image/png;base64,' + r.heatmapBase64" alt="Zone malade (Grad-CAM)" />
          }
          <app-ai-explain module="M1" [result]="r" />
        </section>
      }
    </div>
  `,
})
export class Diagnosis implements OnDestroy {
  private readonly ai = inject(AiService);

  protected readonly previewUrl = signal<string | null>(null);
  protected readonly result = signal<DiseaseResult | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  onFile(event: Event): void {
    const file = fileFrom(event);
    if (!file) return;
    this.revokePreview();
    this.previewUrl.set(URL.createObjectURL(file));
    this.result.set(null);
    this.error.set(null);
    this.loading.set(true);
    this.ai.diagnose(file).subscribe({
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

  ngOnDestroy(): void {
    this.revokePreview();
  }

  private revokePreview(): void {
    const url = this.previewUrl();
    if (url) URL.revokeObjectURL(url);
  }
}
