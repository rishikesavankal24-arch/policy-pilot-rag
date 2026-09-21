"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { AdminUser } from "@/types";
import { adminApi } from "@/api/client";

interface AdminAuthContextType {
  user: AdminUser | null;
  isLoading: boolean;
  isAdmin: boolean;
  login: (email: string, password?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      setIsLoading(true);
      const userData = await adminApi.getMe();
      if (userData && userData.role === "ADMIN") {
        setUser(userData);
      } else {
        // Logged in as non-admin user (customer/employee)
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password?: string) => {
    await adminApi.login({ identifier: email, password });
    const userData = await adminApi.getMe();
    if (!userData || userData.role !== "ADMIN") {
      // Immediately terminate session if not an admin
      await adminApi.logout().catch(() => {});
      setUser(null);
      throw new Error("Access Denied: Administrative credentials are required to access this portal.");
    }
    setUser(userData);
  };

  const logout = async () => {
    try {
      await adminApi.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AdminAuthContext.Provider
      value={{
        user,
        isLoading,
        isAdmin: !!user && user.role === "ADMIN",
        login,
        logout,
        refreshUser
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error("useAdminAuth must be used within an AdminAuthProvider");
  }
  return context;
}
