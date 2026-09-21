"use client";

import React from "react";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { ShieldCheck } from "lucide-react";

export default function AdminAuditPage() {
  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="pb-4 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
              System Audit Trail & Compliance Log
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-600 border border-slate-300">
              STRUCTURAL PLACEHOLDER
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Immutable cryptographic audit trail and supervisory access log
          </p>
        </div>

        <div className="p-12 bg-white border border-slate-200 rounded-xl shadow-xs text-center space-y-3">
          <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center mx-auto">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="text-sm font-bold text-slate-800 uppercase">
            Module not yet available.
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
            Immutable audit event streams, policy version hashes, and compliance verification logs will be integrated in Module M14.
          </p>
        </div>
      </div>
    </AdminLayout>
  );
}
