import { apiClient, authStorage } from './client';
import {
  LandRecordDetail,
  LandRecordPaginatedList,
  ExtractionResult,
  ValidationCheck,
} from '../types';

export interface RecordFilterParams {
  state?: string;
  district?: string;
  tehsil?: string;
  village?: string;
  khasra_number?: string;
  khata_number?: string;
  status?: string;
  min_area?: number;
  max_area?: number;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  limit?: number;
}

export const recordsApi = {
  async listRecords(params?: RecordFilterParams): Promise<LandRecordPaginatedList> {
    // If complex filters are present, use /search endpoint; otherwise use /records
    const hasSearchFilters =
      params?.tehsil ||
      params?.village ||
      params?.khasra_number ||
      params?.khata_number ||
      params?.min_area ||
      params?.max_area ||
      params?.sort_by;

    const endpoint = hasSearchFilters ? '/api/v1/search' : '/api/v1/records';
    return await apiClient.get<LandRecordPaginatedList>(endpoint, params);
  },

  async getRecord(recordId: string): Promise<LandRecordDetail> {
    return await apiClient.get<LandRecordDetail>(`/api/v1/records/${recordId}`);
  },

  async getRecordExtraction(recordId: string): Promise<ExtractionResult> {
    return await apiClient.get<ExtractionResult>(`/api/v1/records/${recordId}/extraction`);
  },

  async getRecordValidation(recordId: string): Promise<ValidationCheck> {
    return await apiClient.get<ValidationCheck>(`/api/v1/records/${recordId}/validation`);
  },

  async triggerValidation(recordId: string): Promise<ValidationCheck> {
    return await apiClient.post<ValidationCheck>(`/api/v1/records/${recordId}/validate`);
  },

  async downloadVerificationReport(recordId: string): Promise<{ blob: Blob; filename: string }> {
    const url = apiClient.getStreamUrl(`/api/v1/records/${recordId}/verification-report`);
    const token = authStorage.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      let errMsg = `Failed to generate verification report (HTTP ${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson?.detail || errJson?.message) {
          errMsg = errJson.detail || errJson.message;
        }
      } catch {
        // use default message
      }
      throw new Error(errMsg);
    }

    const blob = await response.blob();
    let filename = `verification_report_${recordId}.pdf`;
    const disposition = response.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    return { blob, filename };
  },
};
