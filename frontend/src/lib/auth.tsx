import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError, request } from './api';
import { ErrorState, Loading } from '../components/ui';

export type Role = 'admin' | 'power_user' | 'manager' | 'employee';
export const roleLabels: Record<Role, string> = {
  admin: 'Администратор',
  power_user: 'Пользователь с повышенными правами',
  manager: 'Руководитель',
  employee: 'Сотрудник',
};
export interface Account {
  id: number;
  username: string;
  role: Role;
  employee_id: number | null;
  is_active: boolean;
}
export interface AccountSummary extends Account {
  employee_name: string | null;
}
export interface Identity extends Account {
  display_name: string;
  department_id: number | null;
}
interface AuthContextValue {
  user: Identity | null;
  globalAccess: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Identity | null>(null);
  const identityRef = useRef<Identity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const cache = useQueryClient();
  useEffect(() => {
    let active = true;
    function expire() {
      cache.clear();
      identityRef.current = null;
      setUser(null);
    }
    async function load() {
      try {
        const identity = await request<Identity>('/auth/me');
        if (active) {
          if (
            identityRef.current &&
            JSON.stringify(identityRef.current) !== JSON.stringify(identity)
          )
            cache.clear();
          identityRef.current = identity;
          setUser(identity);
          setError(null);
        }
      } catch (cause) {
        if (!active) return;
        if (cause instanceof ApiError && cause.status === 401) expire();
        else setError(cause as Error);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    window.addEventListener('hrm-session-expired', expire);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener('hrm-session-expired', expire);
    };
  }, [cache]);
  async function login(username: string, password: string) {
    const identity = await request<Identity>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    await cache.cancelQueries();
    cache.clear();
    identityRef.current = identity;
    setUser(identity);
    setError(null);
  }
  async function logout() {
    await request('/auth/logout', { method: 'POST' });
    await cache.cancelQueries();
    cache.clear();
    identityRef.current = null;
    setUser(null);
  }
  if (loading) return <Loading />;
  if (error) return <ErrorState error={error} retry={() => window.location.reload()} />;
  return (
    <AuthContext.Provider
      value={{
        user,
        globalAccess: user?.role === 'admin' || user?.role === 'power_user',
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('AuthProvider is required');
  return context;
}
