import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { AdminParcel, AdminPrediction, AdminStats, AdminUser, PageResponse, PredictionType } from './models';

/** Back-office API (/api/admin/**). The backend answers 403 to non-admins. */
@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  stats() {
    return this.http.get<AdminStats>('/api/admin/stats');
  }

  users(q = '', page = 0) {
    return this.http.get<PageResponse<AdminUser>>('/api/admin/users', { params: { q, page } });
  }

  deleteUser(userId: number) {
    return this.http.delete<void>(`/api/admin/users/${userId}`);
  }

  parcels(q = '', page = 0) {
    return this.http.get<PageResponse<AdminParcel>>('/api/admin/parcels', { params: { q, page } });
  }

  deleteParcel(parcelId: number) {
    return this.http.delete<void>(`/api/admin/parcels/${parcelId}`);
  }

  predictions(type?: PredictionType | null, page = 0) {
    let params = new HttpParams().set('page', page);
    if (type) params = params.set('type', type);
    return this.http.get<PageResponse<AdminPrediction>>('/api/admin/predictions', { params });
  }
}

/** French labels of the AI modules, shared by the back-office pages. */
export const MODULE_LABELS: Record<PredictionType, string> = {
  DISEASE: 'M1 · Maladies',
  IRRIGATION: 'M2 · Irrigation',
  YIELD: 'M3 · Récolte',
  PRICE: 'M4 · Prix',
  CHAT: 'M5 · Assistant',
  TREE_COUNT: 'M6 · Comptage',
  HARVEST_PLAN: 'Plan de récolte',
  EXPLAIN: 'Explications IA (LLM)',
};
