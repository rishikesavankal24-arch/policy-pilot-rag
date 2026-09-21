"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { EmployeeItem } from "@/types";
import { 
  ArrowLeft, 
  Building2, 
  Mail, 
  Phone, 
  Briefcase, 
  ShieldCheck, 
  Calendar, 
  UserCheck, 
  AlertCircle,
  Clock
} from "lucide-react";

export default function EmployeeDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [employee, setEmployee] = useState<EmployeeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEmployee = async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getEmployee(id);
      setEmployee(data);
    } catch (err: any) {
      setError(err.message || "Failed to load employee details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployee();
  }, [id]);

  return (
    <AdminLayout>
      <div className="space-y-6 max-w-4xl">
        {/* Back Link */}
        <Link
          href="/employees"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors font-medium"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Employees Directory</span>
        </Link>

        {loading ? (
          <div className="p-12 bg-white border border-slate-200 rounded-xl text-center text-slate-400 text-xs">
            Loading employee record...
          </div>
        ) : error || !employee ? (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error || "Employee not found."}</span>
          </div>
        ) : (
          <>
            {/* Header Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-base font-mono">
                  {employee.full_name ? employee.full_name.slice(0, 2).toUpperCase() : "EM"}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-bold text-slate-900">
                      {employee.full_name || "Employee"}
                    </h1>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                      employee.onboarding_status === "COMPLETED"
                        ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                        : "bg-amber-100 text-amber-800 border-amber-300"
                    }`}>
                      {employee.onboarding_status === "COMPLETED" ? "ACTIVE" : "PENDING"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {employee.email} • ID: {employee.employee_id || "N/A"}
                  </p>
                </div>
              </div>

              <div className="text-right text-xs font-mono text-slate-400 sm:self-center">
                ROLE: {employee.role}
              </div>
            </div>

            {/* Grid Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Institutional Placement */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4 text-xs">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-bold uppercase tracking-wider font-mono text-[11px]">
                  <Building2 className="h-4 w-4 text-slate-500" />
                  <span>Institutional Assignment</span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">ORGANIZATION</span>
                    <span className="text-slate-900 font-semibold">{employee.organization || "PolicyPilot Demo Bank"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">DEPARTMENT</span>
                    <span className="text-slate-900 font-medium">{employee.department || "Credit Underwriting & Operations"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">DESIGNATION</span>
                    <span className="text-slate-900 font-medium">{employee.designation || "Credit Officer"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">EMPLOYEE / BADGE ID</span>
                    <span className="font-mono text-slate-900 font-bold">{employee.employee_id || "PP-DEMO-EMP-001"}</span>
                  </div>
                </div>
              </div>

              {/* Contact & Credentials */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4 text-xs">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900 font-bold uppercase tracking-wider font-mono text-[11px]">
                  <Briefcase className="h-4 w-4 text-slate-500" />
                  <span>Contact & Credentials</span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">PRIMARY EMAIL</span>
                    <span className="font-mono text-slate-900">{employee.email}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">WORK EMAIL</span>
                    <span className="font-mono text-slate-900">{employee.work_email || employee.email}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">REGISTERED PHONE</span>
                    <span className="font-mono text-slate-900">{employee.phone_number || "Not on file"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block font-mono">REGISTRATION DATE</span>
                    <span className="font-mono text-slate-900">{new Date(employee.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Governance Strip */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-900 font-mono text-[11px] uppercase block">
                ADMINISTRATIVE AUDIT & CONTROL
              </span>
              <p className="leading-relaxed">
                Employee profiles reflect verified credentials managed under internal institutional policy. Any credential modifications or revocations must adhere to administrative protocol.
              </p>
            </div>
          </>
        )}
      </div>
    </AdminLayout>
  );
}
