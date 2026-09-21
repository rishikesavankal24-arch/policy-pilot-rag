"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { EmployeeRequestItem } from "@/types";
import { 
  UserCheck, 
  RefreshCw, 
  Filter, 
  ChevronRight, 
  Building2, 
  Mail, 
  Calendar 
} from "lucide-react";

export default function EmployeeVerificationListPage() {
  const [requests, setRequests] = useState<EmployeeRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await adminApi.getEmployeeRequests();
      setRequests(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load employee requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const filteredRequests = requests.filter((r) => {
    const matchesStatus = statusFilter === "ALL" || r.status === statusFilter;
    if (!matchesStatus) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (r.full_name && r.full_name.toLowerCase().includes(q)) ||
      (r.email && r.email.toLowerCase().includes(q)) ||
      (r.employee_id && r.employee_id.toLowerCase().includes(q)) ||
      (r.organization && r.organization.toLowerCase().includes(q)) ||
      (r.department && r.department.toLowerCase().includes(q))
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-100 text-emerald-800 border-emerald-300";
      case "REJECTED":
        return "bg-rose-100 text-rose-800 border-rose-300";
      case "PENDING":
      default:
        return "bg-amber-100 text-amber-800 border-amber-300";
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                Employee Verification Requests
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                ADMIN ACCESS
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Verify credentials and approve institutional employee access requests
            </p>
          </div>

          <button
            onClick={fetchRequests}
            disabled={loading}
            className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 flex items-center gap-1.5 shadow-xs transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
            {error}
          </div>
        )}

        {/* Filters & Search */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-xl shadow-xs text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-500 font-mono text-[11px] uppercase mr-1 flex items-center gap-1">
              <Filter className="h-3 w-3" /> Status:
            </span>
            {["ALL", "PENDING", "APPROVED", "REJECTED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                  statusFilter === st
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search applicant, ID, org..."
              className="px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-800 w-full sm:w-64"
            />
            <div className="text-slate-500 font-mono text-xs whitespace-nowrap">
              {filteredRequests.length} results
            </div>
          </div>
        </div>

        {/* Requests Table */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3.5">Applicant / Email</th>
                  <th className="px-4 py-3.5">Organization</th>
                  <th className="px-4 py-3.5">Department</th>
                  <th className="px-4 py-3.5">Designation</th>
                  <th className="px-4 py-3.5">Employee ID</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Submitted</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                      Loading employee verification requests...
                    </td>
                  </tr>
                ) : filteredRequests.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                      No verification requests found matching filter.
                    </td>
                  </tr>
                ) : (
                  filteredRequests.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-900">{req.full_name || "Applicant"}</div>
                        <div className="text-[11px] text-slate-500 font-mono mt-0.5">{req.email}</div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-700 font-medium">
                        {req.organization}
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">
                        {req.department || "N/A"}
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">
                        {req.designation || "N/A"}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-slate-700">
                        {req.employee_id || "N/A"}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusBadge(req.status)}`}>
                          {req.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 font-mono text-[11px]">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/employee-verification/${req.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors"
                        >
                          <span>Review</span>
                          <ChevronRight className="h-3.5 w-3.5" />
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
