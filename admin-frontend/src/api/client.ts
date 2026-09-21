import { 
  AdminUser, 
  EmployeeRequestItem, 
  EmployeeItem, 
  CustomerItem, 
  CustomerDetail 
} from "@/types";

const API_BASE_URL = 
  process.env.NEXT_PUBLIC_API_BASE_URL || 
  process.env.NEXT_PUBLIC_API_URL || 
  "http://127.0.0.1:8000";

export async function apiClient<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});
  
  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: "include"
  });

  if (!res.ok) {
    let errorDetail = `Request failed (HTTP ${res.status})`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = errorJson.detail;
      }
    } catch {
      // Ignored
    }
    const err = new Error(errorDetail);
    (err as any).status = res.status;
    throw err;
  }

  // Handle empty bodies
  if (res.status === 204) {
    return {} as T;
  }

  return res.json();
}

export const adminApi = {
  // Auth endpoints (using existing /auth)
  getMe: () => apiClient<AdminUser>("/auth/me"),
  login: (credentials: { identifier: string; password?: string }) => 
    apiClient<{ redirect: string }>("/auth/local/login", {
      method: "POST",
      body: JSON.stringify(credentials)
    }),
  logout: () => 
    apiClient<{ message: string }>("/auth/logout", {
      method: "POST"
    }),

  // Admin Operational Endpoints - Employee Requests
  getEmployeeRequests: () => 
    apiClient<EmployeeRequestItem[]>("/admin/employee-requests"),
  
  getEmployeeRequest: (id: string) => 
    apiClient<EmployeeRequestItem>(`/admin/employee-requests/${id}`),
  
  approveEmployeeRequest: (id: string) => 
    apiClient<{ message: string }>(`/admin/employee-requests/${id}/approve`, {
      method: "POST"
    }),
  
  rejectEmployeeRequest: (id: string, reason: string) => 
    apiClient<{ message: string }>(`/admin/employee-requests/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason })
    }),
  
  requestInfo: (id: string, note: string) => 
    apiClient<{ message: string }>(`/admin/employee-requests/${id}/request-information`, {
      method: "POST",
      body: JSON.stringify({ note })
    }),

  // Employee Management
  getEmployees: (params?: { search?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.status && params.status !== "ALL") q.set("status", params.status);
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return apiClient<EmployeeItem[]>(`/admin/employees${queryStr}`);
  },

  getEmployee: (id: string) => 
    apiClient<EmployeeItem>(`/admin/employees/${id}`),

  // Customer Management
  getCustomers: (params?: { search?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.status && params.status !== "ALL") q.set("status", params.status);
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return apiClient<CustomerItem[]>(`/admin/customers${queryStr}`);
  },

  getCustomer: (id: string) => 
    apiClient<CustomerDetail>(`/admin/customers/${id}`)
};
