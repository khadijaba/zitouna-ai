import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AiService } from '../../core/api/ai.service';
import { ChatResponse, Intent, Parcel } from '../../core/api/models';
import { ParcelService } from '../../core/api/parcel.service';
import { errorMessage } from '../../shared/errors';
import { MockBadge } from '../../shared/mock-badge';

/** Shown on the suggestion buttons and under the replies: derja in Arabic script, like the replies. */
export const INTENT_LABELS: Record<Intent, string> = {
  maladie: 'مرض الزيتون',
  irrigation: 'السقي',
  meteo_alerte: 'الطقس',
  recolte: 'الصابة',
  prix_vente: 'السوم',
  comptage: 'عدد الزيتون',
  conseil_general: 'نصيحة عامة',
  salutation: 'سلام',
  hors_sujet: 'خارج الموضوع',
};

interface Message {
  from: 'user' | 'bot';
  text: string;
  intent?: Intent;
  mock?: boolean;
  /** LLM model that wrote the reply, undefined for template replies. */
  llm?: string;
  /** Clarification: buttons to pick the intent, and the question they apply to. */
  suggestions?: Intent[];
  originalText?: string;
  answered?: boolean;
}

/** M5 · Derja assistant (the backend routes questions to M1-M4, M6 or the RAG) */
@Component({
  selector: 'app-assistant',
  imports: [FormsModule, MockBadge],
  template: `
    <h1>Assistant</h1>
    <p class="muted">Posez votre question en derja (arabe ou arabizi) ou en français : Zitouna répond en derja, en lettres arabes.</p>

    <section class="card chat">
      @for (m of messages(); track $index) {
        <div class="bubble" [class.user]="m.from === 'user'" dir="auto">
          {{ m.text }}
          @if (m.intent && !m.suggestions) {
            <small class="muted"> · {{ labels[m.intent] }}@if (m.llm) { · ✨ {{ m.llm }}}</small>
          }
          @if (m.mock) {
            <app-mock-badge [mock]="true" />
          }
          @if (m.suggestions?.length) {
            <div class="suggestions">
              @for (s of m.suggestions; track s) {
                <button class="btn btn-ghost" type="button" [disabled]="m.answered || loading()" (click)="choose(m, s)">
                  {{ labels[s] }}
                </button>
              }
            </div>
          }
        </div>
      } @empty {
        <p class="muted" dir="auto">Exemples : « 9adech nesgi zitouni had el jem3a? » · « قداش يشريو الزيت اليوم؟ »</p>
      }
      @if (loading()) {
        <p class="muted" dir="rtl">زيتونة تكتب…</p>
      }
    </section>

    <form class="chat-input" (ngSubmit)="send()">
      <select [(ngModel)]="parcelId" name="parcel">
        <option [ngValue]="undefined">Sans parcelle</option>
        @for (p of parcels(); track p.id) {
          <option [ngValue]="p.id">{{ p.name }}</option>
        }
      </select>
      <input [(ngModel)]="draft" name="message" placeholder="Votre question…" maxlength="500" dir="auto" autocomplete="off" />
      <button class="btn" type="submit" [disabled]="!draft.trim() || loading()">Envoyer</button>
    </form>
  `,
})
export class Assistant implements OnInit {
  private readonly ai = inject(AiService);
  private readonly parcelService = inject(ParcelService);

  protected readonly labels = INTENT_LABELS;
  protected readonly messages = signal<Message[]>([]);
  protected readonly parcels = signal<Parcel[]>([]);
  protected readonly loading = signal(false);
  protected draft = '';
  protected parcelId?: number;

  ngOnInit(): void {
    this.parcelService.list().subscribe((p) => this.parcels.set(p));
  }

  send(): void {
    const text = this.draft.trim();
    if (!text) return;
    this.draft = '';
    this.push({ from: 'user', text });
    this.ask(text);
  }

  /** The farmer picked an intent: resend the original question, without classification. */
  choose(message: Message, intent: Intent): void {
    this.messages.update((list) => list.map((m) => (m === message ? { ...m, answered: true } : m)));
    this.push({ from: 'user', text: this.labels[intent] });
    this.ask(message.originalText!, intent);
  }

  private ask(text: string, forcedIntent?: Intent): void {
    this.loading.set(true);
    this.ai.chat({ text, parcelId: this.parcelId ?? null, forcedIntent: forcedIntent ?? null }).subscribe({
      next: (r) => {
        this.push(toMessage(r, text));
        this.loading.set(false);
      },
      error: (err) => {
        this.push({ from: 'bot', text: errorMessage(err) });
        this.loading.set(false);
      },
    });
  }

  private push(message: Message): void {
    this.messages.update((list) => [...list, message]);
  }
}

function toMessage(r: ChatResponse, originalText: string): Message {
  return r.clarify
    ? { from: 'bot', text: r.reply, intent: r.intent, mock: r.mock, suggestions: r.suggestions, originalText }
    : { from: 'bot', text: r.reply, intent: r.intent, mock: r.mock, llm: llmName(r.generatedBy) };
}

/** "gemini/gemini-3.5-flash" -> "gemini-3.5-flash"; template replies show nothing. */
function llmName(generatedBy: string | undefined): string | undefined {
  return generatedBy && generatedBy !== 'template' ? generatedBy.split('/').pop() : undefined;
}
