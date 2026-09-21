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
