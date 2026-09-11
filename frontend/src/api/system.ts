import { apiClient } from './client';
import { OCRStatus, HealthStatus, DashboardStats } from '../types';

export const systemApi = {
  async getHealth(): Promise<HealthStatus> {
    return await apiClient.get<HealthStatus>('/health');
  },

  async getOCRStatus(): Promise<OCRStatus> {
    return await apiClient.get<OCRStatus>('/api/v1/system/ocr-status');
  },

  async getDashboardStats(): Promise<DashboardStats> {
    return await apiClient.get<DashboardStats>('/api/v1/system/dashboard-stats');
  },
};
