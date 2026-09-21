export const ROLE_PERMISSIONS: Record<string, string[]> = {
  CUSTOMER: [
    "PROFILE_READ_SELF",
    "PROFILE_UPDATE_SELF",
    "APPLICATION_CREATE_SELF",
    "APPLICATION_READ_SELF",
    "APPLICATION_UPDATE_SELF",
    "DOCUMENT_READ_SELF",
    "DOCUMENT_UPLOAD_SELF",
    "NOTIFICATION_READ_SELF",
    "CUSTOMER_AI_USE",
  ],
  EMPLOYEE: [
    // Personal permissions
    "PROFILE_READ_SELF",
    "PROFILE_UPDATE_SELF",
    "APPLICATION_CREATE_SELF",
    "APPLICATION_READ_SELF",
    "APPLICATION_UPDATE_SELF",
    "DOCUMENT_READ_SELF",
    "DOCUMENT_UPLOAD_SELF",
    "NOTIFICATION_READ_SELF",
    "CUSTOMER_AI_USE",
    // Employee Workspace permissions
    "EMPLOYEE_WORKSPACE_ACCESS",
    "EMPLOYEE_APPLICATION_REVIEW",
    "EMPLOYEE_DOCUMENT_REVIEW",
    "EMPLOYEE_COMPLIANCE_ACCESS",
    "EMPLOYEE_REPORTS_ACCESS",
  ],
  ADMIN: [
    "ADMIN_USER_MANAGEMENT",
    "ADMIN_EMPLOYEE_VERIFICATION",
    "ADMIN_POLICY_MANAGEMENT",
    "ADMIN_AUDIT_ACCESS",
  ],
  UNASSIGNED: [],
};

export function hasPermissions(userRole: string, requiredPermissions: string[]): boolean {
  if (!userRole) return false;
  
  const userPermissions = ROLE_PERMISSIONS[userRole] || [];
  
  // Return true if the user has ALL required permissions
  return requiredPermissions.every(perm => userPermissions.includes(perm));
}
