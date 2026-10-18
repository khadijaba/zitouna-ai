import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AiExplain, lighten } from './ai-explain';

describe('lighten', () => {
  it('removes images and coordinates at every level, keeps the figures', () => {
    expect(
      lighten({ treeCount: 86, annotatedImageBase64: 'AAAA', boxes: [{ x: 1 }], days: [{ et0Mm: 3.6, heatmap: 'x' }] }),
    ).toEqual({ treeCount: 86, days: [{ et0Mm: 3.6 }] });
  });
});

describe('AiExplain', () => {
  function setup() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(AiExplain);
    fixture.componentRef.setInput('module', 'M6');
    fixture.componentRef.setInput('result', { treeCount: 86, annotatedImageBase64: 'AAAA' });
    fixture.detectChanges();
    return { fixture, http: TestBed.inject(HttpTestingController) };
  }

  it('asks the backend for an LLM explanation without the image, then shows it with the model name', () => {
    const { fixture, http } = setup();
    (fixture.nativeElement.querySelector('.btn-ai') as HTMLButtonElement).click();

    const req = http.expectOne('/api/ai/explain');
    expect(req.request.body).toEqual({ module: 'M6', result: { treeCount: 86 }, language: 'fr' });
    req.flush({ explanation: '86 oliviers détectés.', provider: 'gemini', model: 'gemini-3.5-flash', latencyMs: 700, fallback: false });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('86 oliviers détectés.');
    expect(text).toContain('gemini-3.5-flash');
    http.verify();
  });

  it('asks in derja, shows it right to left, and says when no LLM was available', () => {
    const { fixture, http } = setup();
    (fixture.nativeElement.querySelector('.btn-ghost') as HTMLButtonElement).click();

    const req = http.expectOne('/api/ai/explain');
    expect(req.request.body.language).toBe('derja');
    req.flush({ explanation: 'لقينا 86 زيتونة.', provider: 'template', model: 'template', latencyMs: 0, fallback: true });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.ai-explain-box').getAttribute('dir')).toBe('rtl');
    expect(fixture.nativeElement.textContent).toContain('aucun LLM disponible');
    http.verify();
  });

  it('forgets the old explanation when a new result arrives', () => {
    const { fixture, http } = setup();
    (fixture.nativeElement.querySelector('.btn-ai') as HTMLButtonElement).click();
    http.expectOne('/api/ai/explain').flush({ explanation: 'Ancienne.', provider: 'p', model: 'm', latencyMs: 1, fallback: false });
    fixture.detectChanges();

    fixture.componentRef.setInput('result', { treeCount: 90 });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Ancienne.');
  });
});
