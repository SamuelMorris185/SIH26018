import { apiClient } from './client';
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
  review_status?: string[];
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
      params?.min_area !== undefined ||
      params?.max_area !== undefined ||
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
    const { blob, headers } = await apiClient.getBlob(`/api/v1/records/${recordId}/verification-report`);
    let filename = `verification_report_${recordId}.pdf`;
    const disposition = headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    return { blob, filename };
  },
};
