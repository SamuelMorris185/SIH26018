import { apiClient, authStorage } from './client';
import { TokenResponse, User } from '../types';

export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await apiClient.post<TokenResponse>('/api/v1/auth/login', {
      email,
      password,
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
    }
    return data;
  },

  async getMe(): Promise<User> {
    return await apiClient.get<User>('/api/v1/auth/me');
  },

  logout(): void {
    authStorage.clearToken();
  },
};
