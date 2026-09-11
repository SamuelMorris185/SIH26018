import { apiClient } from './client';
import { CadastralMapResponse, CadastralMapRecord, GeometryValidationResponse } from '../types';

export const mapApi = {
  async getMapParcels(params?: {
    status?: string;
    district?: string;
    village?: string;
    has_discrepancies?: boolean;
    limit?: number;
  }): Promise<CadastralMapResponse> {
    return await apiClient.get<CadastralMapResponse>('/api/v1/map/parcels', params);
  },

  async getParcelDetail(recordId: string): Promise<CadastralMapRecord> {
    return await apiClient.get<CadastralMapRecord>(`/api/v1/map/parcels/${recordId}`);
  },

  async validateGeometry(payload: {
    latitude?: number;
    longitude?: number;
    boundary_geojson?: Record<string, any>;
  }): Promise<GeometryValidationResponse> {
    return await apiClient.post<GeometryValidationResponse>('/api/v1/map/geometry/validate', payload);
  },

  async attachParcelLocation(
    recordId: string,
    payload: {
      latitude?: number;
      longitude?: number;
      boundary_geojson?: Record<string, any>;
      map_source?: string;
    }
  ): Promise<any> {
    return await apiClient.post(`/api/v1/map/parcels/${recordId}`, payload);
  },
};
