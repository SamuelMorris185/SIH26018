import { apiClient, authStorage } from './client';
import {
  Document,
  DocumentPaginatedList,
  DigitizationPipelineResult,
  Job,
} from '../types';

export const documentsApi = {
  async uploadAndProcess(
    file: File,
    docType: string = 'JAMABANDI'
  ): Promise<DigitizationPipelineResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);

    return await apiClient.postFormData<DigitizationPipelineResult>(
      '/api/v1/digitization/upload-and-process',
      formData
    );
  },

  async uploadOnly(file: File, docType: string = 'JAMABANDI'): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);

    return await apiClient.postFormData<Document>('/api/v1/documents', formData);
  },

  async processExisting(documentId: string): Promise<DigitizationPipelineResult> {
    return await apiClient.post<DigitizationPipelineResult>(
      `/api/v1/digitization/process/${documentId}`
    );
  },

  async processExistingAsync(documentId: string): Promise<Job> {
    return await apiClient.post<Job>(
      `/api/v1/documents/${documentId}/process?background=true`
    );
  },


  async getDocument(documentId: string): Promise<Document> {
    return await apiClient.get<Document>(`/api/v1/documents/${documentId}`);
  },

  async listDocuments(params?: {
    status?: string;
    doc_type?: string;
    page?: number;
    limit?: number;
  }): Promise<DocumentPaginatedList> {
    return await apiClient.get<DocumentPaginatedList>('/api/v1/documents', params);
  },

  getDocumentContentUrl(documentId: string): string {
    return apiClient.getStreamUrl(`/api/v1/documents/${documentId}/content`);
  },

  async fetchDocumentBlob(documentId: string): Promise<{ blob: Blob; mimeType: string }> {
    const url = apiClient.getStreamUrl(`/api/v1/documents/${documentId}/content`);
    const token = authStorage.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`Failed to load document preview (HTTP ${response.status})`);
    }
    const blob = await response.blob();
    const mimeType = response.headers.get('content-type') || 'application/octet-stream';
    return { blob, mimeType };
  },
};
