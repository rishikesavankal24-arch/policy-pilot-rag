"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { setActiveSessionToken, clearActiveSessionToken, setupFetchInterceptor, getPortalScope } from "@/lib/session";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  profile_image_url: string | null;
  onboarding_status: string;
  role: string;
  requested_role: string;
  language: string;
  phone_number: string | null;
  authentication_provider: string;
  session_token?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const checkAuth = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/auth/me`, {
        credentials: "include"
      });
      
      if (response.ok) {
        const userData = await response.json();
        const hasTabToken = typeof window !== "undefined" && !!sessionStorage.getItem("session_token");
        const hasEmpToken = typeof window !== "undefined" && !!localStorage.getItem("employee_session_token");
        const hasCustToken = typeof window !== "undefined" && !!localStorage.getItem("customer_session_token");

        // Safe non-secret debug logging for Step 4
        console.log("[DEBUG AUTH_ME]", {
          currentPathname: pathname,
          selectedPortalScope: getPortalScope(pathname),
          authMeRole: userData.role,
          hasEmployeeToken: hasEmpToken,
          hasCustomerToken: hasCustToken,
        });

        // On /login without a prior tab session, if a background cookie exists, do not auto-inject it into this tab
        if (pathname === "/login" && !hasTabToken) {
          setUser(null);
          return;
        }

        setUser(userData);
        if (userData.session_token) {
          setActiveSessionToken(userData.session_token, userData.role, pathname);
        }
      } else if (response.status === 401) {
        // Explicitly handle 401 as unauthenticated, not an error
        clearActiveSessionToken(pathname);
        setUser(null);
      } else {
        console.warn(`Auth check returned status: ${response.status}`);
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed (network/CORS error):", error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setupFetchInterceptor();
    checkAuth();
  }, []);

  useEffect(() => {
    // Route protection logic
    if (isLoading) return;

    const publicPaths = ["/login", "/", "/register", "/forgot-password", "/reset-password"];
    const isPublicPath = publicPaths.includes(pathname);

    if (!user && !isPublicPath) {
      if (pathname.startsWith("/employee")) {
        router.push("/login?portal=employee");
      } else {
        router.push("/login?portal=customer");
      }
    } else if (user) {
      const isNew = ["NEW", "ONBOARDING_REQUIRED"].includes(user.onboarding_status);
      const isPending = user.onboarding_status === "PENDING_VERIFICATION";
      const isCompleted = user.onboarding_status === "COMPLETED";

      if (isNew) {
        if (user.authentication_provider === "mobile" && pathname !== "/register") {
          router.push("/register");
        } else if (user.authentication_provider === "google" && pathname !== "/onboarding") {
          router.push("/onboarding");
        } else if (pathname !== "/onboarding" && pathname !== "/register") {
          router.push("/onboarding");
        }
      } else if (isPending && pathname !== "/pending") {
        router.push("/pending");
      } else if (isCompleted) {
        if (pathname === "/login" || pathname === "/onboarding" || pathname === "/register" || pathname === "/pending" || pathname === "/") {
          const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
          const targetPortal = params?.get("portal");

          // If on /login?portal=employee but session is not employee, stay on login to allow employee sign-in
          if (pathname === "/login" && targetPortal === "employee" && user.role !== "EMPLOYEE") {
            return;
          }

          // If on /login without an active tab session token, stay on login to allow clean authentication
          if (pathname === "/login" && typeof window !== "undefined" && !sessionStorage.getItem("session_token")) {
            return;
          }

          let targetRedirect = "/dashboard";
          if (user.role === "ADMIN") {
            targetRedirect = "/admin";
          } else if (user.role === "EMPLOYEE") {
            targetRedirect = "/employee/dashboard";
          }

          console.log("[DEBUG ROUTE REDIRECT]", {
            currentPathname: pathname,
            requestedPortal: targetPortal,
            returnedRole: user.role,
            finalRedirectPath: targetRedirect,
          });

          router.push(targetRedirect);
        } else if (user.role === "CUSTOMER" && pathname.startsWith("/employee")) {
          clearActiveSessionToken(pathname);
          setUser(null);
          router.push("/login?portal=employee");
        } else if (user.role === "EMPLOYEE" && pathname.startsWith("/dashboard")) {
          router.push("/employee/dashboard");
        }
      }
    }
  }, [user, isLoading, pathname, router]);

  const logout = async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      const isEmp = pathname.startsWith("/employee");
      clearActiveSessionToken(pathname);
      setUser(null);
      router.push(isEmp ? "/login?portal=employee" : "/login?portal=customer");
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
