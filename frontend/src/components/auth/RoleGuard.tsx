"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { hasPermissions } from "@/lib/permissions";

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  requiredPermissions?: string[];
  fallbackUrl?: string;
  hideInsteadOfRedirect?: boolean;
}

export function RoleGuard({ 
  children, 
  allowedRoles, 
  requiredPermissions,
  fallbackUrl = "/dashboard",
  hideInsteadOfRedirect = false
}: RoleGuardProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    
    if (user && !hideInsteadOfRedirect) {
      let isAllowed = true;
      
      if (allowedRoles && !allowedRoles.includes(user.role)) {
        isAllowed = false;
      }
      
      if (requiredPermissions && !hasPermissions(user.role, requiredPermissions)) {
        isAllowed = false;
      }
      
      if (!isAllowed) {
        router.push(fallbackUrl);
      }
    }
  }, [user, isLoading, allowedRoles, requiredPermissions, fallbackUrl, router, hideInsteadOfRedirect]);

  if (isLoading) {
    return null; // Or a spinner
  }

  if (!user) {
    return null;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return null;
  }
  
  if (requiredPermissions && !hasPermissions(user.role, requiredPermissions)) {
    return null;
  }

  return <>{children}</>;
}
