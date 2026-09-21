"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/contexts/AdminAuthContext";

export default function AdminHomePage() {
  const router = useRouter();
  const { isAdmin, isLoading } = useAdminAuth();

  useEffect(() => {
    if (!isLoading) {
      if (isAdmin) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [isAdmin, isLoading, router]);

  return (
    <div className="min-h-screen bg-[#070D1E] flex items-center justify-center text-slate-300">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs uppercase tracking-wider font-mono">Routing to Admin Console...</span>
      </div>
    </div>
  );
}
