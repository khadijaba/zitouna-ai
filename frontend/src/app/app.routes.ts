import { inject } from '@angular/core';
import { Routes } from '@angular/router';

import { adminGuard, authGuard } from './core/auth/auth.guard';
import { AuthService } from './core/auth/auth.service';
import { Shell } from './layout/shell';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login').then((m) => m.Login) },
  { path: 'register', loadComponent: () => import('./features/auth/register').then((m) => m.Register) },
  {
    path: '',
    component: Shell,
    canActivate: [authGuard],
    children: [
      // Home after login: the admin goes to the back-office, a farmer to their dashboard.
      { path: '', pathMatch: 'full', redirectTo: () => (inject(AuthService).isAdmin() ? 'admin' : 'home') },
      { path: 'home', loadComponent: () => import('./features/home/home').then((m) => m.Home) },
      {
        path: 'parcels',
        loadComponent: () => import('./features/parcels/parcel-list').then((m) => m.ParcelList),
      },
      {
        path: 'parcels/:id',
        loadComponent: () => import('./features/parcels/parcel-detail').then((m) => m.ParcelDetail),
      },
      {
        path: 'diagnosis',
        loadComponent: () => import('./features/diagnosis/diagnosis').then((m) => m.Diagnosis),
      },
      {
        path: 'irrigation',
        loadComponent: () => import('./features/irrigation/irrigation').then((m) => m.Irrigation),
      },
      { path: 'price', loadComponent: () => import('./features/price/price').then((m) => m.Price) },
      {
        path: 'assistant',
        loadComponent: () => import('./features/assistant/assistant').then((m) => m.Assistant),
      },
      { path: 'history', loadComponent: () => import('./features/history/history').then((m) => m.History) },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadComponent: () => import('./features/admin/admin-layout').then((m) => m.AdminLayout),
        children: [
          {
            path: '',
            pathMatch: 'full',
            loadComponent: () => import('./features/admin/admin-dashboard').then((m) => m.AdminDashboard),
          },
          { path: 'users', loadComponent: () => import('./features/admin/admin-users').then((m) => m.AdminUsers) },
          {
            path: 'parcels',
            loadComponent: () => import('./features/admin/admin-parcels').then((m) => m.AdminParcels),
          },
          {
            path: 'predictions',
            loadComponent: () => import('./features/admin/admin-predictions').then((m) => m.AdminPredictions),
          },
        ],
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
