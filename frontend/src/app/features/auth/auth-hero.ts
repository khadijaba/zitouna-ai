import { Component } from '@angular/core';

import { Icon } from '../../shared/icon';

/** Left panel of the login / register pages: what Zitouna AI does, in one look. */
@Component({
  selector: 'app-auth-hero',
  imports: [Icon],
  template: `
    <section class="auth-hero">
      <div class="auth-brand">
        <svg viewBox="0 0 32 32" width="36" height="36" aria-hidden="true">
          <ellipse cx="16" cy="18" rx="9" ry="11" fill="#9aab4f" />
          <ellipse cx="13" cy="15" rx="2.6" ry="4" fill="#c4d27f" opacity=".7" />
          <path d="M16 7c3-4 8-5 11-4-2 4-6 6-11 4z" fill="#d9b43c" />
        </svg>
        Zitouna AI
      </div>
      <div>
        <h1>L'intelligence artificielle au service de vos oliviers.</h1>
        <p>Diagnostic des feuilles, irrigation, récolte, prix de l'huile et assistant en derja : tout votre verger au
          même endroit.</p>
        <ul>
          <li><app-icon name="leaf" /> Reconnaît l'œil de paon et l'Aculus sur une simple photo</li>
          <li><app-icon name="droplet" /> Litres d'eau par arbre selon la météo de votre parcelle</li>
          <li><app-icon name="coins" /> Vendre maintenant ou stocker : un conseil chiffré</li>
          <li><app-icon name="chat" /> Posez vos questions en derja, à l'écrit</li>
        </ul>
      </div>
      <p class="auth-foot">Projet Zitouna AI · 6 modules d'IA pour les oléiculteurs tunisiens</p>
    </section>
  `,
  host: { style: 'display: contents' },
})
export class AuthHero {}
