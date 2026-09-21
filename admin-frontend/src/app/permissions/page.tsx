"use client";

import React from "react";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { KeyRound } from "lucide-react";

export default function AdminPermissionsPage() {
  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="pb-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
              Role & Permission Governance
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-300">
              STRUCTURAL PLACEHOLDER
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            RBAC matrix definitions, scope assignments, and privilege delegation
          </p>
        </div>

        <div className="p-12 bg-white border border-slate-200 rounded-xl shadow-xs text-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center mx-auto">
            <KeyRound className="h-6 w-6" />
          </div>
          <h2 className="text-sm font-bold text-slate-800 uppercase">
            Module not yet available.
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            Administrative role and granular permission management is governed by the underlying FastAPI RBAC matrix. Dynamic privilege assignment will appear here once module interfaces are enabled.
          </p>
        </div>
      </div>
    </AdminLayout>
  );
}
