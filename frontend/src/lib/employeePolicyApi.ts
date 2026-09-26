/**
 * Employee Policy Catalog API client for M08.7.
 * Read-only interface for verified employees to discover and inspect active policies.
 */

export interface EmployeeRegulatoryAuthoritySummary {
  id: string;
  name: string;
  code: string;
  jurisdiction: string;
  description?: string | null;
  website_url?: string | null;
}

export interface EmployeePolicyListItem {
  id: string;
  policy_code: string;
  title: string;
  description?: string | null;
  category: string;
  policy_type: string;
  status: string;
  institution?: string | null;
  jurisdiction: string;
  current_version_number?: number | null;
  effective_from?: string | null;
  effective_to?: string | null;
  updated_at: string;
  regulatory_authority?: EmployeeRegulatoryAuthoritySummary | null;
}

export interface EmployeePolicyListResponse {
  items: EmployeePolicyListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmployeeApplicabilitySummary {
  id: string;
  institution?: string | null;
  jurisdiction?: string | null;
  loan_type?: string | null;
  department?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
}

export interface EmployeePolicyVersionSummary {
  id: string;
  version_number: number;
  status: string;
  effective_from?: string | null;
  effective_to?: string | null;
  changelog?: string | null;
  has_file: boolean;
  file_size?: number | null;
  mime_type?: string | null;
  created_at: string;
  published_at?: string | null;
}

export interface EmployeePolicyDetail {
  id: string;
  policy_code: string;
  title: string;
  description?: string | null;
  category: string;
  policy_type: string;
  status: string;
  institution?: string | null;
  jurisdiction: string;
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
  updated_at: string;
  regulatory_authority?: EmployeeRegulatoryAuthoritySummary | null;
  current_version?: EmployeePolicyVersionSummary | null;
  applicabilities: EmployeeApplicabilitySummary[];
}

export interface EmployeePolicyHistoryItem {
  id: string;
  version_number: number;
  status: string;
  effective_from?: string | null;
  effective_to?: string | null;
  changelog?: string | null;
  has_file: boolean;
  file_size?: number | null;
  mime_type?: string | null;
  created_at: string;
  published_at?: string | null;
}

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface PolicyFilterParams {
  search?: string;
  category?: string;
  policy_type?: string;
  jurisdiction?: string;
  institution?: string;
  regulatory_authority_id?: string;
  loan_type?: string;
  department?: string;
  page?: number;
  page_size?: number;
}

export async function fetchEmployeePolicies(params: PolicyFilterParams = {}): Promise<EmployeePolicyListResponse> {
  const query = new URLSearchParams();
  if (params.search?.trim()) query.append("search", params.search.trim());
  if (params.category && params.category !== "ALL") query.append("category", params.category);
  if (params.policy_type && params.policy_type !== "ALL") query.append("policy_type", params.policy_type);
  if (params.jurisdiction && params.jurisdiction !== "ALL") query.append("jurisdiction", params.jurisdiction);
  if (params.institution?.trim()) query.append("institution", params.institution.trim());
  if (params.regulatory_authority_id && params.regulatory_authority_id !== "ALL") {
    query.append("regulatory_authority_id", params.regulatory_authority_id);
  }
  if (params.loan_type && params.loan_type !== "ALL") query.append("loan_type", params.loan_type);
  if (params.department && params.department !== "ALL") query.append("department", params.department);
  if (params.page) query.append("page", String(params.page));
  if (params.page_size) query.append("page_size", String(params.page_size));

  const url = `${getApiUrl()}/api/employee/policies${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      "Accept": "application/json"
    }
  });

  if (res.status === 401) {
    throw new Error("UNAUTHORIZED: Session expired or unauthenticated.");
  }
  if (res.status === 403) {
    throw new Error("FORBIDDEN: Verified employee credentials required to access policy catalog.");
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch policies (HTTP ${res.status})`);
  }

  return res.json();
}

export async function fetchEmployeePolicyDetail(policyId: string): Promise<EmployeePolicyDetail> {
  const url = `${getApiUrl()}/api/employee/policies/${policyId}`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      "Accept": "application/json"
    }
  });

  if (res.status === 401) {
    throw new Error("UNAUTHORIZED: Session expired or unauthenticated.");
  }
  if (res.status === 403) {
    throw new Error("FORBIDDEN: Verified employee credentials required.");
  }
  if (res.status === 404) {
    throw new Error("NOT_FOUND: The requested policy was not found or is not active.");
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to retrieve policy details (HTTP ${res.status})`);
  }

  return res.json();
}

export async function fetchEmployeePolicyHistory(policyId: string): Promise<EmployeePolicyHistoryItem[]> {
  const url = `${getApiUrl()}/api/employee/policies/${policyId}/history`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      "Accept": "application/json"
    }
  });

  if (res.status === 401) {
    throw new Error("UNAUTHORIZED: Session expired or unauthenticated.");
  }
  if (res.status === 403) {
    throw new Error("FORBIDDEN: Verified employee credentials required.");
  }
  if (res.status === 404) {
    throw new Error("NOT_FOUND: Policy not found or not active.");
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to retrieve version history (HTTP ${res.status})`);
  }

  return res.json();
}

export async function downloadPolicyDocumentBlob(
  policyId: string, 
  versionId: string, 
  filename: string
): Promise<void> {
  const url = `${getApiUrl()}/api/employee/policies/${policyId}/versions/${versionId}/file`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include"
  });

  if (res.status === 401) {
    throw new Error("UNAUTHORIZED: Please sign in as a verified employee.");
  }
  if (res.status === 403) {
    throw new Error("FORBIDDEN: You do not have permission to download this document.");
  }
  if (res.status === 404) {
    throw new Error("NOT_FOUND: Document file not found on server.");
  }
  if (!res.ok) {
    throw new Error(`Download failed with status ${res.status}`);
  }

  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = filename || `policy_${policyId}_v${versionId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}

export async function viewPolicyDocumentBlob(
  policyId: string, 
  versionId: string
): Promise<void> {
  const url = `${getApiUrl()}/api/employee/policies/${policyId}/versions/${versionId}/file`;
  const res = await fetch(url, {
    method: "GET",
    credentials: "include"
  });

  if (res.status === 401) {
    throw new Error("UNAUTHORIZED: Please sign in as a verified employee.");
  }
  if (res.status === 403) {
    throw new Error("FORBIDDEN: You do not have permission to view this document.");
  }
  if (res.status === 404) {
    throw new Error("NOT_FOUND: Document file not found on server.");
  }
  if (!res.ok) {
    throw new Error(`View failed with status ${res.status}`);
  }

  const blob = await res.blob();
  const pdfBlob = new Blob([blob], { type: "application/pdf" });
  const viewUrl = window.URL.createObjectURL(pdfBlob);
  window.open(viewUrl, "_blank");
}
