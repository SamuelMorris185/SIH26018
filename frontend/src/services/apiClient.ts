import { env } from '../config/env';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${env.API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new ApiError(response.status, `HTTP error! Status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new Error(`Failed to fetch from ${endpoint}: ${error instanceof Error ? error.message : String(error)}`);
    }
  },
};
