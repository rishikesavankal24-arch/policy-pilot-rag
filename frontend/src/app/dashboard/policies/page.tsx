"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function DashboardPoliciesRedirect() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (user?.role === "EMPLOYEE") {
      router.replace("/employee/policies");
    } else {
      router.replace("/dashboard/guidelines");
    }
  }, [user, isLoading, router]);

  return (
    <div className="min-h-screen bg-[#0B132B] flex items-center justify-center text-slate-300">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs uppercase tracking-wider font-mono">Routing to Policy Catalog...</span>
      </div>
    </div>
  );
}
