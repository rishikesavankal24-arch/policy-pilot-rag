"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { EmployeeRequestItem, EmployeeItem, CustomerItem } from "@/types";
import { 
  ShieldCheck, 
  UserCheck, 
  Users, 
  FileText, 
  Activity, 
  ArrowRight, 
  Building2,
  RefreshCw
} from "lucide-react";

export default function AdminDashboardPage() {
  const [requests, setRequests] = useState<EmployeeRequestItem[]>([]);
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const [reqData, empData, custData] = await Promise.all([
        adminApi.getEmployeeRequests().catch(() => []),
        adminApi.getEmployees().catch(() => []),
        adminApi.getCustomers().catch(() => [])
      ]);
      setRequests(reqData || []);
      setEmployees(empData || []);
      setCustomers(custData || []);
    } catch (err: any) {
      setError(err.message || "Failed to load administrative overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const pendingRequests = requests.filter((r) => r.status === "PENDING");

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                Administrative Governance Dashboard
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                ACTIVE CONSOLE
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Central supervisory oversight, personnel verification, and platform management
            </p>
          </div>

          <button
            onClick={fetchOverview}
            disabled={loading}
            className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 flex items-center gap-1.5 shadow-xs transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Overview</span>
          </button>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
            {error}
          </div>
        )}

        {/* Real Operational Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Card 1: Employee Verification */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Employee Requests
              </span>
              <UserCheck className="h-4 w-4 text-amber-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {loading ? "..." : pendingRequests.length}
              </span>
              <span className="text-xs text-amber-700 font-semibold font-mono">Pending Review</span>
            </div>
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Total requests on record:</span>
              <span className="font-bold text-slate-700 font-mono">{requests.length}</span>
            </div>
            <Link
              href="/employee-verification"
              className="mt-1 w-full py-2 px-3 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>Review Requests</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {/* Card 2: Active Employees */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Active Employees
              </span>
              <Users className="h-4 w-4 text-slate-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {loading ? "..." : employees.length}
              </span>
              <span className="text-xs text-slate-600 font-semibold font-mono">Officers Registered</span>
            </div>
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Institutional personnel:</span>
              <span className="font-bold text-slate-700 font-mono">PolicyPilot Demo Bank</span>
            </div>
            <Link
              href="/employees"
              className="mt-1 w-full py-2 px-3 bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>View Employee Directory</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {/* Card 3: Customers */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Customer Accounts
              </span>
              <Users className="h-4 w-4 text-blue-600" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {loading ? "..." : customers.length}
              </span>
              <span className="text-xs text-blue-700 font-semibold font-mono">Borrowers Registered</span>
            </div>
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Registry status:</span>
              <span className="font-bold text-emerald-600 font-mono">Live Sync</span>
            </div>
            <Link
              href="/customers"
              className="mt-1 w-full py-2 px-3 bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>View Customer Registry</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Future Modules Truthful Section */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Global Applications
              </span>
              <FileText className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-xs font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
              Loan application governance will be established in Module M06.
            </p>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Institutions
              </span>
              <Building2 className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-xs font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
              Multi-tenant bank configuration will be enabled in a future release.
            </p>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 font-mono">
                System Audit
              </span>
              <ShieldCheck className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-xs font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-100">
              Immutable audit trail and compliance verification will appear in M14.
            </p>
          </div>
        </div>

        {/* Architecture Notice */}
        <div className="p-5 bg-[#0F172A] border border-slate-800 rounded-xl text-slate-200 space-y-2 shadow-xs">
          <div className="flex items-center gap-2 text-amber-400">
            <ShieldCheck className="h-5 w-5" />
            <h2 className="text-sm font-bold uppercase tracking-wider">
              Administrative Console Architecture Notice
            </h2>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
            Administrative overview data will appear here once operational modules are enabled. This administrative console operates on a separate frontend on port 3001, strictly segregated from the user-facing Customer and Employee portals on port 3000, while sharing the central FastAPI backend and PostgreSQL database.
          </p>
        </div>

        {/* Recent Pending Employee Verification Table Preview */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase">
                Pending Employee Verification Requests
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Onboarding requests awaiting administrative approval
              </p>
            </div>
            <Link
              href="/employee-verification"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>View All ({pendingRequests.length})</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Applicant Name</th>
                  <th className="px-4 py-3">Organization</th>
                  <th className="px-4 py-3">Department</th>
                  <th className="px-4 py-3">Designation</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      Loading verification requests...
                    </td>
                  </tr>
                ) : pendingRequests.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      No pending employee requests at this time.
                    </td>
                  </tr>
                ) : (
                  pendingRequests.slice(0, 5).map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-semibold text-slate-800">
                        {req.full_name || req.email}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{req.organization}</td>
                      <td className="px-4 py-3 text-slate-600">{req.department || "N/A"}</td>
                      <td className="px-4 py-3 text-slate-600">{req.designation || "N/A"}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          {req.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/employee-verification/${req.id}`}
                          className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </AdminLayout>
  );
}
