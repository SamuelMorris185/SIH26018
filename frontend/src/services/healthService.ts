import { apiClient } from './apiClient';
import { HealthStatus } from '../types';

export const healthService = {
  getHealth: async (): Promise<HealthStatus> => {
    return apiClient.get<HealthStatus>('/health');
  },
};
