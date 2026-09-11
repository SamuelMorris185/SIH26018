import { apiClient } from './client';
import { Job, JobPaginatedList } from '../types';

export const jobsApi = {
  async getJob(jobId: string): Promise<Job> {
    return await apiClient.get<Job>(`/api/v1/jobs/${jobId}`);
  },

  async retryJob(jobId: string): Promise<Job> {
    return await apiClient.post<Job>(`/api/v1/jobs/${jobId}/retry`);
  },

  async listJobs(params?: {
    document_id?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<JobPaginatedList> {
    return await apiClient.get<JobPaginatedList>('/api/v1/jobs', params);
  },

  async getDocumentJobs(documentId: string): Promise<Job[]> {
    return await apiClient.get<Job[]>(`/api/v1/documents/${documentId}/jobs`);
  },
};
