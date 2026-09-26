export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  onboarding_status: string;
}

export interface EmployeeRequestItem {
  id: string;
  user_id: string;
  organization: string;
  department: string | null;
  employee_id: string | null;
  designation: string | null;
  work_email: string | null;
  reason: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED";
  created_at: string;
  updated_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  admin_note: string | null;
  full_name: string | null;
  email: string | null;
  phone_number: string | null;
}

export interface EmployeeItem {
  id: string;
  full_name: string | null;
  email: string;
  phone_number: string | null;
  role: string;
  onboarding_status: string;
  employee_id: string | null;
  organization: string | null;
  department: string | null;
  designation: string | null;
  work_email: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface CustomerApplicationSummary {
  id: string;
  loan_type: string;
  requested_amount: number;
  tenure: number;
  status: string;
  created_at: string;
}

export interface CustomerItem {
  id: string;
  full_name: string | null;
  email: string;
  phone_number: string | null;
  role: string;
  onboarding_status: string;
  city: string | null;
  state: string | null;
  application_count: number;
  created_at: string;
  last_login_at: string | null;
}

export interface CustomerDetail extends CustomerItem {
  date_of_birth: string | null;
  address: string | null;
  pincode: string | null;
  language: string | null;
  applications: CustomerApplicationSummary[];
}

// =============================================================================
// M08 Policy & Regulatory Management Types
// =============================================================================

export type PolicyStatus = "DRAFT" | "PUBLISHED" | "ACTIVE" | "SUPERSEDED" | "ARCHIVED";

export interface RegulatoryAuthority {
  id: string;
  name: string;
  short_name: string;
  authority_type: string;
  jurisdiction: string | null;
  website_url: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface Policy {
  id: string;
  policy_code: string;
  title: string;
  description: string | null;
  category: string | null;
  policy_type: string | null;
  status: PolicyStatus;
  institution: string | null;
  jurisdiction: string | null;
  current_version_id: string | null;
  regulatory_authority_id: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PolicyListResponse {
  items: Policy[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PolicyApplicability {
  id: string;
  policy_id: string;
  institution: string | null;
  jurisdiction: string | null;
  loan_type: string | null;
  department: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PolicyVersionHistoryItem {
  id: string;
  policy_id: string;
  version_number: string;
  status_context: string;
  changelog: string | null;
  file_url: string | null;
  file_hash: string | null;
  file_size_bytes: number | null;
  page_count: number | null;
  effective_from: string | null;
  effective_to: string | null;
  created_by: string | null;
  published_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface PolicyLifecycleResponse {
  id: string;
  policy_code: string;
  title: string;
  status: PolicyStatus;
  current_version_id: string | null;
  updated_at: string | null;
}

