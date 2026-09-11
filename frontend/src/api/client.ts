import { env } from '../config/env';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const TOKEN_STORAGE_KEY = 'sih_auth_token';

export const authStorage = {
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  },
  setToken: (token: string): void => {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  },
  clearToken: (): void => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  },
};

const getBaseUrl = (): string => {
  return env.API_BASE_URL || '';
};

const buildUrl = (endpoint: string, params?: Record<string, any>): string => {
  const base = getBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  let url = `${base}${cleanEndpoint}`;

  if (params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, String(value));
      }
    });
    const queryString = query.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  return url;
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (response.ok) {
    if (response.status === 204) {
      return {} as T;
    }
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    return (await response.text()) as unknown as T;
  }

  let errorMessage = `HTTP Error ${response.status}`;
  let errorData: any = null;

  try {
    errorData = await response.json();
    if (typeof errorData?.detail === 'string') {
      errorMessage = errorData.detail;
    } else if (Array.isArray(errorData?.detail)) {
      errorMessage = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
    } else if (errorData?.message) {
      errorMessage = errorData.message;
    }
  } catch {
    try {
      const text = await response.text();
      if (text) errorMessage = text;
    } catch {
      // Keep default message
    }
  }

  if (response.status === 401) {
    // Session expired or invalid
    authStorage.clearToken();
  }

  throw new ApiError(response.status, errorMessage, errorData);
};

const getHeaders = (customHeaders: Record<string, string> = {}): Record<string, string> => {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...customHeaders,
  };

  const token = authStorage.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

export const apiClient = {
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = buildUrl(endpoint, params);
    const response = await fetch(url, {
      method: 'GET',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
    });
    return handleResponse<T>(response);
  },

  async post<T>(endpoint: string, body?: any): Promise<T> {
    const url = buildUrl(endpoint);
    const response = await fetch(url, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async patch<T>(endpoint: string, body?: any): Promise<T> {
    const url = buildUrl(endpoint);
    const response = await fetch(url, {
      method: 'PATCH',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(endpoint: string): Promise<T> {
    const url = buildUrl(endpoint);
    const response = await fetch(url, {
      method: 'DELETE',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
    });
    return handleResponse<T>(response);
  },

  async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = buildUrl(endpoint);
    // Don't set Content-Type header when using FormData; fetch handles boundary automatically
    const headers = getHeaders();
    delete headers['Content-Type'];

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });
    return handleResponse<T>(response);
  },

  getStreamUrl(endpoint: string): string {
    return buildUrl(endpoint);
  },
};
