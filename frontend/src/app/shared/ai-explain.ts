import { Component, effect, inject, input, signal } from '@angular/core';

import { AiService } from '../core/api/ai.service';
import { ExplainLanguage, ExplainModule, ExplainResult } from '../core/api/models';
import { errorMessage } from './errors';

/** Keys never sent to the LLM: images and coordinates are useless to it and can weigh megabytes. */
const HEAVY_KEYS = ['base64', 'image', 'heatmap', 'boxes'];

export function lighten(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(lighten);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => !HEAVY_KEYS.some((heavy) => key.toLowerCase().includes(heavy)))
        .map(([key, v]) => [key, lighten(v)]),
    );
  }
  return value;
}

/** « Expliquer avec l'IA » under a module's result: an LLM (Gemini, Groq in fallback) explains it in plain words. */
@Component({
  selector: 'app-ai-explain',
  template: `
    <div class="ai-explain">
      <div class="ai-explain-actions">
        <button type="button" class="btn btn-ai" [disabled]="loading()" (click)="ask('fr')">
          ✨ {{ loading() ? "L'IA rédige l'explication…" : "Expliquer avec l'IA" }}
        </button>
        <button type="button" class="btn btn-ghost" [disabled]="loading()" (click)="ask('derja')">بالدارجة</button>
      </div>
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }
      @if (explanation(); as e) {
        <div class="ai-explain-box" [attr.dir]="language() === 'derja' ? 'rtl' : null">
          <p>{{ e.explanation }}</p>
          <p class="ai-explain-by">
            {{ e.fallback ? 'Explication automatique (aucun LLM disponible)' : 'Rédigé par ' + e.provider + ' · ' + e.model }}
          </p>
        </div>
      }
    </div>
  `,
})
export class AiExplain {
  private readonly ai = inject(AiService);

  readonly module = input.required<ExplainModule>();
  readonly result = input.required<unknown>();

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly explanation = signal<ExplainResult | null>(null);
  protected readonly language = signal<ExplainLanguage>('fr');

  constructor() {
    // A new result makes the previous explanation obsolete.
    effect(() => {
      this.result();
      this.explanation.set(null);
      this.error.set(null);
    });
  }

  protected ask(language: ExplainLanguage) {
    this.loading.set(true);
    this.error.set(null);
    this.language.set(language);
    this.ai.explain(this.module(), lighten(this.result()), language).subscribe({
      next: (e) => {
        this.explanation.set(e);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }
}
