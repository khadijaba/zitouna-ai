import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import {
  ChatRequest,
  ChatResponse,
  DiseaseResult,
  HarvestPlan,
  IrrigationResult,
  PageResponse,
  PredictionRecord,
  PredictionType,
  PriceResult,
  TreeCountResult,
  YieldResult,
} from './models';

/** All AI features go through the Spring backend, never directly to the FastAPI services. */
@Injectable({ providedIn: 'root' })
export class AiService {
  private readonly http = inject(HttpClient);

  /** M1 */
  diagnose(image: File, parcelId?: number) {
    let params = new HttpParams();
    if (parcelId) params = params.set('parcelId', parcelId);
    return this.http.post<DiseaseResult>('/api/ai/disease', imageForm(image), { params });
  }

  /** M2 (days: 1..16) */
  irrigation(parcelId: number, days = 7) {
    return this.http.get<IrrigationResult>(`/api/parcels/${parcelId}/irrigation`, { params: { days } });
  }

  /** M3 */
  yieldForecast(parcelId: number) {
    return this.http.get<YieldResult>(`/api/parcels/${parcelId}/yield`);
  }

  /** M4 (horizonWeeks: 1..26; quantityKg: kg of oil, for the expected gain) */
  price(horizonWeeks = 8, quantityKg?: number | null) {
    let params = new HttpParams().set('horizonWeeks', horizonWeeks);
    if (quantityKg) params = params.set('quantityKg', quantityKg);
    return this.http.get<PriceResult>('/api/ai/price', { params });
  }

  /** M5 detects the intent, the backend routes the question to the right module. */
  chat(request: ChatRequest) {
    return this.http.post<ChatResponse>('/api/ai/chat', request);
  }

  /** M6 */
  countTrees(parcelId: number, image: File) {
    return this.http.post<TreeCountResult>(`/api/parcels/${parcelId}/count-trees`, imageForm(image));
  }

  /** M6 -> M3 -> M4. Without image, the parcel's saved tree count is used. */
  harvestPlan(parcelId: number, image?: File) {
    return this.http.post<HarvestPlan>(`/api/parcels/${parcelId}/harvest-plan`, image ? imageForm(image) : null);
  }

  history(type?: PredictionType, page = 0) {
    let params = new HttpParams().set('page', page);
    if (type) params = params.set('type', type);
    return this.http.get<PageResponse<PredictionRecord>>('/api/history', { params });
  }
}

function imageForm(image: File): FormData {
  const form = new FormData();
  form.append('image', image);
  return form;
}
