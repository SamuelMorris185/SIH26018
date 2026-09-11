import { apiClient } from './client';
import { AuditLogList } from '../types';

export interface AuditLogFilterParams {
  actor_user_id?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  page?: number;
  limit?: number;
}

export const auditApi = {
  async getAuditLogs(params?: AuditLogFilterParams): Promise<AuditLogList> {
    return await apiClient.get<AuditLogList>('/api/v1/audit-logs', params);
  },
};
