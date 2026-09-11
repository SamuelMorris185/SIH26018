import { apiClient } from './client';
import { ReviewDetail } from '../types';

export const reviewApi = {
  async getReviewStatus(recordId: string): Promise<ReviewDetail> {
    return await apiClient.get<ReviewDetail>(`/api/v1/records/${recordId}/review`);
  },

  async submitForReview(recordId: string, notes?: string): Promise<ReviewDetail> {
    return await apiClient.post<ReviewDetail>(`/api/v1/records/${recordId}/submit-review`, {
      notes,
    });
  },

  async approveRecord(recordId: string, notes?: string): Promise<ReviewDetail> {
    return await apiClient.post<ReviewDetail>(`/api/v1/records/${recordId}/approve`, {
      notes,
    });
  },

  async rejectRecord(
    recordId: string,
    rejectionReason: string,
    notes?: string
  ): Promise<ReviewDetail> {
    return await apiClient.post<ReviewDetail>(`/api/v1/records/${recordId}/reject`, {
      rejection_reason: rejectionReason,
      notes,
    });
  },
};
