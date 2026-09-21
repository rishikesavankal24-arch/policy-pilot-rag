from fastapi import Depends, HTTPException, status
from app.db.models import User, Role, OnboardingStatus
from app.core.security import get_current_user

# Permission Matrix Definition
ROLE_PERMISSIONS = {
    Role.CUSTOMER.value: {
        "PROFILE_READ_SELF",
        "PROFILE_UPDATE_SELF",
        "APPLICATION_CREATE_SELF",
        "APPLICATION_READ_SELF",
        "APPLICATION_UPDATE_SELF",
        "DOCUMENT_READ_SELF",
        "DOCUMENT_UPLOAD_SELF",
        "NOTIFICATION_READ_SELF",
        "CUSTOMER_AI_USE"
    },
    Role.EMPLOYEE.value: {
        # Personal permissions
        "PROFILE_READ_SELF",
        "PROFILE_UPDATE_SELF",
        "APPLICATION_CREATE_SELF",
        "APPLICATION_READ_SELF",
        "APPLICATION_UPDATE_SELF",
        "DOCUMENT_READ_SELF",
        "DOCUMENT_UPLOAD_SELF",
        "NOTIFICATION_READ_SELF",
        "CUSTOMER_AI_USE",
        # Employee Workspace permissions
        "EMPLOYEE_WORKSPACE_ACCESS",
        "EMPLOYEE_APPLICATION_REVIEW",
        "EMPLOYEE_DOCUMENT_REVIEW",
        "EMPLOYEE_COMPLIANCE_ACCESS",
        "EMPLOYEE_REPORTS_ACCESS"
    },
    Role.ADMIN.value: {
        "ADMIN_USER_MANAGEMENT",
        "ADMIN_EMPLOYEE_VERIFICATION",
        "ADMIN_POLICY_MANAGEMENT",
        "ADMIN_AUDIT_ACCESS"
    },
    Role.UNASSIGNED.value: set()
}

def require_permissions(required_permissions: list[str]):
    """
    Dependency that checks if the current user's role has ALL the required permissions.
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        user_role = current_user.role
        user_permissions = ROLE_PERMISSIONS.get(user_role, set())
        
        missing = [perm for perm in required_permissions if perm not in user_permissions]
        
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker

def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Ensures the user is fully onboarded and active before allowing generic access.
    """
    if current_user.role == Role.UNASSIGNED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not fully configured")
    return current_user

def check_resource_ownership_or_employee(current_user: User, resource_user_id: str):
    """
    Checks if the user owns the resource, OR if they are an employee.
    Used for generic GET routes where owners can view, and employees can view.
    Returns True if allowed, otherwise raises HTTPException.
    """
    is_owner = str(current_user.id) == str(resource_user_id)
    is_employee = "EMPLOYEE_WORKSPACE_ACCESS" in ROLE_PERMISSIONS.get(current_user.role, set())
    
    if is_owner or is_employee:
        return True
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this resource"
    )

def check_employee_review_not_owner(current_user: User, resource_user_id: str):
    """
    Strictly for employee review actions (approve/reject).
    Ensures they have review permissions AND are not the owner.
    """
    is_owner = str(current_user.id) == str(resource_user_id)
    is_employee = "EMPLOYEE_APPLICATION_REVIEW" in ROLE_PERMISSIONS.get(current_user.role, set())
    
    if is_employee:
        if is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conflict of interest: Employees cannot review their own applications"
            )
        return True
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to review this resource"
    )

def require_verified_employee(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensures the user is an authorized, verified employee:
    - User role must be EMPLOYEE
    - Onboarding status must be COMPLETED
    """
    if current_user.role != Role.EMPLOYEE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Employee access required."
        )
    if current_user.onboarding_status != OnboardingStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee verification pending approval. Access to operational queues is restricted."
        )
    return current_user
