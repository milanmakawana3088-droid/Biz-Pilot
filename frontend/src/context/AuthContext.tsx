import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { User, Warehouse } from '@/types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  activeWarehouse: Warehouse | null;
  warehouses: Warehouse[];
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setActiveWarehouse: (warehouse: Warehouse) => void;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('bizpilot_token'));
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [activeWarehouse, setActiveWarehouseState] = useState<Warehouse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const setActiveWarehouse = (warehouse: Warehouse) => {
    setActiveWarehouseState(warehouse);
    localStorage.setItem('bizpilot_active_warehouse_id', warehouse.id);
  };

  const loadUserData = async () => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await api.auth.me();
      setUser(currentUser);

      const whList = await api.warehouses.list();
      setWarehouses(whList);

      const savedWhId = localStorage.getItem('bizpilot_active_warehouse_id');
      if (savedWhId) {
        const found = whList.find((w) => w.id === savedWhId);
        if (found) {
          setActiveWarehouseState(found);
        } else if (whList.length > 0) {
          setActiveWarehouse(whList[0]);
        }
      } else if (whList.length > 0) {
        setActiveWarehouse(whList[0]);
      }
    } catch (err) {
      console.error('Failed to load authenticated user session', err);
      localStorage.removeItem('bizpilot_token');
      localStorage.removeItem('bizpilot_active_warehouse_id');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUserData();
  }, [token]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.auth.login({ email, password });
      localStorage.setItem('bizpilot_token', res.access_token);
      setToken(res.access_token);
      setUser(res.user);

      const whList = await api.warehouses.list();
      setWarehouses(whList);
      if (whList.length > 0) {
        setActiveWarehouse(whList[0]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch (err) {
      // Ignore network errors on logout
    } finally {
      localStorage.removeItem('bizpilot_token');
      localStorage.removeItem('bizpilot_active_warehouse_id');
      setToken(null);
      setUser(null);
      setActiveWarehouseState(null);
    }
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    // Map roles to basic permissions if not explicitly stored
    if (user.role === 'MANAGER') return true;
    if (user.role === 'STAFF') {
      return !permission.includes('delete') && !permission.includes('users');
    }
    if (user.role === 'AUDITOR') {
      return permission.includes('read') || permission.includes('report') || permission.includes('audit');
    }
    return false;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        activeWarehouse,
        warehouses,
        isLoading,
        login,
        logout,
        setActiveWarehouse,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
