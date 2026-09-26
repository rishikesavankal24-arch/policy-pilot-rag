import { 
  AdminUser, 
  EmployeeRequestItem, 
  EmployeeItem, 
  CustomerItem, 
  CustomerDetail,
  RegulatoryAuthority,
  Policy,
  PolicyListResponse,
  PolicyApplicability,
  PolicyVersionHistoryItem,
  PolicyLifecycleResponse
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
    apiClient<CustomerDetail>(`/admin/customers/${id}`),

  // ===========================================================================
  // M08.5 Regulatory Authority Endpoints
  // ===========================================================================
  getRegulatoryAuthorities: (params?: { is_active?: boolean; authority_type?: string; jurisdiction?: string }) => {
    const q = new URLSearchParams();
    if (params?.is_active !== undefined) q.set("is_active", String(params.is_active));
    if (params?.authority_type && params.authority_type !== "ALL") q.set("authority_type", params.authority_type);
    if (params?.jurisdiction) q.set("jurisdiction", params.jurisdiction);
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return apiClient<RegulatoryAuthority[]>(`/api/admin/regulatory-authorities${queryStr}`);
  },

  getRegulatoryAuthority: (id: string) => 
    apiClient<RegulatoryAuthority>(`/api/admin/regulatory-authorities/${id}`),

  createRegulatoryAuthority: (data: {
    name: string;
    short_name: string;
    authority_type?: string;
    jurisdiction?: string;
    website_url?: string;
    description?: string;
    is_active?: boolean;
  }) => 
    apiClient<RegulatoryAuthority>("/api/admin/regulatory-authorities", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  updateRegulatoryAuthority: (id: string, data: Partial<{
    name: string;
    short_name: string;
    authority_type: string;
    jurisdiction: string;
    website_url: string;
    description: string;
    is_active: boolean;
  }>) => 
    apiClient<RegulatoryAuthority>(`/api/admin/regulatory-authorities/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data)
    }),

  deactivateRegulatoryAuthority: (id: string) => 
    apiClient<RegulatoryAuthority>(`/api/admin/regulatory-authorities/${id}/deactivate`, {
      method: "POST"
    }),

  // ===========================================================================
  // M08.5 Policy Metadata Endpoints
  // ===========================================================================
  getPolicies: (params?: {
    status?: string;
    policy_code?: string;
    title?: string;
    category?: string;
    policy_type?: string;
    institution?: string;
    jurisdiction?: string;
    regulatory_authority_id?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.status && params.status !== "ALL") q.set("status", params.status);
    if (params?.policy_code) q.set("policy_code", params.policy_code);
    if (params?.title) q.set("title", params.title);
    if (params?.category && params.category !== "ALL") q.set("category", params.category);
    if (params?.policy_type && params.policy_type !== "ALL") q.set("policy_type", params.policy_type);
    if (params?.institution) q.set("institution", params.institution);
    if (params?.jurisdiction) q.set("jurisdiction", params.jurisdiction);
    if (params?.regulatory_authority_id && params.regulatory_authority_id !== "ALL") q.set("regulatory_authority_id", params.regulatory_authority_id);
    if (params?.search) q.set("search", params.search);
    if (params?.page) q.set("page", String(params.page));
    if (params?.page_size) q.set("page_size", String(params.page_size));
    const queryStr = q.toString() ? `?${q.toString()}` : "";
    return apiClient<PolicyListResponse>(`/api/admin/policies${queryStr}`);
  },

  getPolicy: (id: string) => 
    apiClient<Policy>(`/api/admin/policies/${id}`),

  createPolicy: (data: {
    policy_code: string;
    title: string;
    description?: string;
    category?: string;
    policy_type?: string;
    institution?: string;
    jurisdiction?: string;
    regulatory_authority_id?: string;
  }) => 
    apiClient<Policy>("/api/admin/policies", {
      method: "POST",
      body: JSON.stringify(data)
    }),

  updatePolicy: (id: string, data: Partial<{
    title: string;
    description: string;
    category: string;
    policy_type: string;
    institution: string;
    jurisdiction: string;
    regulatory_authority_id: string;
  }>) => 
    apiClient<Policy>(`/api/admin/policies/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data)
    }),

  // ===========================================================================
  // M08.5 Policy Applicability Endpoints
  // ===========================================================================
  getPolicyApplicability: (policyId: string) => 
    apiClient<PolicyApplicability[]>(`/api/admin/policies/${policyId}/applicability`),

  addPolicyApplicability: (policyId: string, data: {
    institution?: string;
    jurisdiction?: string;
    loan_type?: string;
    department?: string;
  }) => 
    apiClient<PolicyApplicability>(`/api/admin/policies/${policyId}/applicability`, {
      method: "POST",
      body: JSON.stringify(data)
    }),

  deletePolicyApplicability: (policyId: string, applicabilityId: string) => 
    apiClient<{ status: string; applicability_id: string }>(`/api/admin/policies/${policyId}/applicability/${applicabilityId}`, {
      method: "DELETE"
    }),

  // ===========================================================================
  // M08.5 Policy Version & Document Management
  // ===========================================================================
  getPolicyHistory: (policyId: string) => 
    apiClient<PolicyVersionHistoryItem[]>(`/api/admin/policies/${policyId}/history`),

  uploadPolicyVersion: async (policyId: string, formData: FormData) => {
    const url = `${API_BASE_URL}/api/admin/policies/${policyId}/versions/upload`;
    const res = await fetch(url, {
      method: "POST",
      body: formData,
      credentials: "include"
    });
    if (!res.ok) {
      let errorDetail = `Upload failed (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errorDetail = errJson.detail;
      } catch {}
      const err = new Error(errorDetail);
      (err as any).status = res.status;
      throw err;
    }
    return res.json();
  },

  updatePolicyVersionMetadata: (
    policyId: string,
    versionId: string,
    data: {
      changelog?: string;
      effective_from?: string;
      effective_to?: string;
    }
  ) => 
    apiClient<PolicyVersionHistoryItem>(`/api/admin/policies/${policyId}/versions/${versionId}`, {
      method: "PATCH",
      body: JSON.stringify(data)
    }),

  downloadPolicyVersionFile: async (policyId: string, versionId: string, filename?: string) => {
    const url = `${API_BASE_URL}/api/admin/policies/${policyId}/versions/${versionId}/file`;
    const res = await fetch(url, {
      credentials: "include"
    });
    if (!res.ok) {
      let errorDetail = `Failed to download file (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errorDetail = errJson.detail;
      } catch {}
      const err = new Error(errorDetail);
      (err as any).status = res.status;
      throw err;
    }
    const blob = await res.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename || `policy_version_${versionId}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(objectUrl);
    document.body.removeChild(a);
  },

  viewPolicyVersionFileInTab: async (policyId: string, versionId: string) => {
    const url = `${API_BASE_URL}/api/admin/policies/${policyId}/versions/${versionId}/file`;
    const res = await fetch(url, {
      credentials: "include"
    });
    if (!res.ok) {
      let errorDetail = `Failed to open document (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errorDetail = errJson.detail;
      } catch {}
      const err = new Error(errorDetail);
      (err as any).status = res.status;
      throw err;
    }
    const blob = await res.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    window.open(objectUrl, "_blank");
  },

  // ===========================================================================
  // M08.5 Policy Lifecycle Transitions
  // ===========================================================================
  publishPolicy: (policyId: string, versionId?: string) => {
    const queryStr = versionId ? `?version_id=${encodeURIComponent(versionId)}` : "";
    return apiClient<PolicyLifecycleResponse>(`/api/admin/policies/${policyId}/publish${queryStr}`, {
      method: "POST"
    });
  },

  activatePolicy: (policyId: string, versionId?: string) => {
    const queryStr = versionId ? `?version_id=${encodeURIComponent(versionId)}` : "";
    return apiClient<PolicyLifecycleResponse>(`/api/admin/policies/${policyId}/activate${queryStr}`, {
      method: "POST"
    });
  },

  supersedePolicy: (policyId: string, newVersionId: string) => 
    apiClient<PolicyLifecycleResponse>(`/api/admin/policies/${policyId}/supersede?new_version_id=${encodeURIComponent(newVersionId)}`, {
      method: "POST"
    }),

  archivePolicy: (policyId: string) => 
    apiClient<PolicyLifecycleResponse>(`/api/admin/policies/${policyId}/archive`, {
      method: "POST"
    })
};

