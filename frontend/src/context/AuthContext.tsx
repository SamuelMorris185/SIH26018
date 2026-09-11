import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, UserRole } from '../types';
import { authApi } from '../api/auth';
import { authStorage } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  isAuthenticated: boolean;
  role: UserRole | null;
  isAdmin: boolean;
  isOperator: boolean;
  isReviewer: boolean;
  isViewer: boolean;
  hasRole: (...roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(authStorage.getToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const rehydrate = useCallback(async () => {
    const existingToken = authStorage.getToken();
    if (!existingToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const me = await authApi.getMe();
      setUser(me);
      setToken(existingToken);
    } catch {
      authStorage.clearToken();
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    rehydrate();
  }, [rehydrate]);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authApi.login(email, password);
      setUser(response.user);
      setToken(response.access_token);
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify your credentials.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    authApi.logout();
    setUser(null);
    setToken(null);
    setError(null);
  };

  const clearError = (): void => {
    setError(null);
  };

  const role = user?.role || null;
  const isAuthenticated = !!user && !!token;
  const isAdmin = role === 'ADMIN';
  const isOperator = role === 'OPERATOR';
  const isReviewer = role === 'REVIEWER';
  const isViewer = role === 'VIEWER';

  const hasRole = (...roles: UserRole[]): boolean => {
    if (!role) return false;
    return roles.includes(role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        error,
        login,
        logout,
        clearError,
        isAuthenticated,
        role,
        isAdmin,
        isOperator,
        isReviewer,
        isViewer,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
