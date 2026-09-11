import { apiClient } from './client';
import {
  Discrepancy,
  DiscrepancyPaginatedList,
  DiscrepancyStatus,
  ComparisonSummary,
  RecordComparison,
} from '../types';

export interface DiscrepancyFilterParams {
  status?: string;
  severity?: string;
  discrepancy_type?: string;
  record_id?: string;
  page?: number;
  limit?: number;
}

export const discrepanciesApi = {
  async listDiscrepancies(params?: DiscrepancyFilterParams): Promise<DiscrepancyPaginatedList> {
    return await apiClient.get<DiscrepancyPaginatedList>('/api/v1/discrepancies', params);
  },

  async getRecordDiscrepancies(recordId: string): Promise<Discrepancy[]> {
    return await apiClient.get<Discrepancy[]>(`/api/v1/records/${recordId}/discrepancies`);
  },

  async compareRecord(recordId: string): Promise<ComparisonSummary> {
    return await apiClient.post<ComparisonSummary>(`/api/v1/records/${recordId}/compare`);
  },

  async getRecordComparisons(recordId: string): Promise<RecordComparison[]> {
    return await apiClient.get<RecordComparison[]>(`/api/v1/records/${recordId}/comparisons`);
  },

  async updateDiscrepancyStatus(
    discrepancyId: string,
    status: DiscrepancyStatus | string,
    resolutionNotes?: string
  ): Promise<Discrepancy> {
    return await apiClient.patch<Discrepancy>(`/api/v1/discrepancies/${discrepancyId}`, {
      status,
      resolution_notes: resolutionNotes,
    });
  },
};
