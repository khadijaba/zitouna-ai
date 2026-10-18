import { Component, input } from '@angular/core';

/** Shown next to any AI result computed without a trained model. */
@Component({
  selector: 'app-mock-badge',
  template: `@if (mock()) {
    <span class="badge badge-mock" title="Ce module n'a pas encore de modèle entraîné">données de démo</span>
  }`,
})
export class MockBadge {
  readonly mock = input.required<boolean>();
}
