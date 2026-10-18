import { Component, computed, input } from '@angular/core';

/** Stroke icons (24×24 grid, 2 px), drawn inline: no icon font, no extra request. */
const PATHS: Record<string, string[]> = {
  home: ['M3 10.5 12 3l9 7.5', 'M5 9.5V21h14V9.5', 'M9.5 21v-6h5v6'],
  map: ['M9 4 3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5L9 4z', 'M9 4v13.5', 'M15 6.5V20'],
  leaf: ['M5 19c0-8 5-13 15-14-1 10-6 15-14 15', 'M5 19c3-4 6-6.5 9-8'],
  droplet: ['M12 3s-6 6.6-6 11a6 6 0 0 0 12 0c0-4.4-6-11-6-11z'],
  chart: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  coins: ['M8 7a5 2.5 0 1 0 10 0 5 2.5 0 1 0-10 0', 'M8 7v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V7', 'M3 12a5 2.5 0 0 0 5 2.5', 'M3 12v5c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5'],
  chat: ['M4 5h16v11H9l-5 4V5z', 'M8 9h8', 'M8 12h5'],
  trees: ['M7 3 3 10h8L7 3z', 'M7 10v8', 'M17 6l-4 7h8l-4-7z', 'M17 13v5', 'M2 21h20'],
  history: ['M3 12a9 9 0 1 0 3-6.7L3 8', 'M3 3v5h5', 'M12 7v5l3 3'],
  gauge: ['M4 15a8 8 0 1 1 16 0', 'M12 15l4-4', 'M4 19h16'],
  users: ['M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M2 21c0-3.9 3.1-7 7-7s7 3.1 7 7', 'M16 3.5a4 4 0 0 1 0 7.5', 'M22 21c0-3.2-2.1-5.9-5-6.7'],
  list: ['M8 6h13', 'M8 12h13', 'M8 18h13', 'M3 6h.01', 'M3 12h.01', 'M3 18h.01'],
  logout: ['M15 4h4v16h-4', 'M10 16l-4-4 4-4', 'M6 12h11'],
  arrow: ['M5 12h14', 'M13 6l6 6-6 6'],
  plus: ['M12 5v14', 'M5 12h14'],
  sparkles: ['M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8L12 3z', 'M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z'],
};

@Component({
  selector: 'app-icon',
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      @for (d of paths(); track $index) {
        <path [attr.d]="d" />
      }
    </svg>
  `,
  host: { class: 'icon' },
})
export class Icon {
  readonly name = input.required<string>();
  readonly size = input(20);
  protected readonly paths = computed(() => PATHS[this.name()] ?? []);
}
