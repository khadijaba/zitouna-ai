import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { Parcel, ParcelRequest } from './models';

@Injectable({ providedIn: 'root' })
export class ParcelService {
  private readonly http = inject(HttpClient);

  list() {
    return this.http.get<Parcel[]>('/api/parcels');
  }

  get(id: number) {
    return this.http.get<Parcel>(`/api/parcels/${id}`);
  }

  create(body: ParcelRequest) {
    return this.http.post<Parcel>('/api/parcels', body);
  }

  update(id: number, body: ParcelRequest) {
    return this.http.put<Parcel>(`/api/parcels/${id}`, body);
  }

  delete(id: number) {
    return this.http.delete<void>(`/api/parcels/${id}`);
  }
}
