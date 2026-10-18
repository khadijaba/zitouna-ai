import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ChatResponse } from '../../core/api/models';
import { Assistant } from './assistant';

describe('Assistant', () => {
  let backend: HttpTestingController;

  function render() {
    TestBed.configureTestingModule({
      imports: [Assistant],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    backend = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(Assistant);
    fixture.detectChanges();
    backend.expectOne('/api/parcels').flush([]);
    return fixture;
  }

  async function ask(fixture: ReturnType<typeof render>, text: string) {
    await fixture.whenStable(); // ngModel registers its control asynchronously
    const input: HTMLInputElement = fixture.nativeElement.querySelector('input[name="message"]');
    input.value = text;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    fixture.nativeElement.querySelector('form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('shows suggestion buttons on clarify and resends the question with the chosen intent', async () => {
    const fixture = render();
    await ask(fixture, '9adech 3andi?');

    const first = backend.expectOne('/api/ai/chat');
    expect(first.request.body).toEqual({ text: '9adech 3andi?', parcelId: null, forcedIntent: null });
    first.flush({
      reply: 'تحب تعرف قداش من شجرة عندك؟',
      intent: 'recolte',
      clarify: true,
      suggestions: ['recolte', 'comptage'],
      data: null,
      mock: false,
      generatedBy: 'template',
    } satisfies ChatResponse);
    await fixture.whenStable();

    const bubbles: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.bubble'));
    expect(bubbles.every((b) => b.getAttribute('dir') === 'auto')).toBe(true);
    const buttons: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('.suggestions button'));
    expect(buttons.map((b) => b.textContent?.trim())).toEqual(['الصابة', 'عدد الزيتون']);

    buttons[1].click();
    await fixture.whenStable();
    const second = backend.expectOne('/api/ai/chat');
    expect(second.request.body).toEqual({ text: '9adech 3andi?', parcelId: null, forcedIntent: 'comptage' });
    backend.verify();
  });
});
