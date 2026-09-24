"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  FileText, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  FolderCheck, 
  ShieldAlert, 
  UserCheck, 
  ArrowRight, 
  Shield, 
  Building2, 
  RefreshCw,
  ExternalLink,
  Lock,
  ChevronRight
} from "lucide-react";

interface EmployeeDashboardData {
  metrics: {
    total_submitted_applications: number;
    under_review: number;
    submitted: number;
    additional_info_required: number;
    approved: number;
    declined: number;
    my_assignments: number;
    pending_documents: number;
  };
  recent_applications: {
    id: string;
    user_id: string;
    loan_type: string;
    requested_amount: number;
    tenure: number;
    status: string;
    applicant_name: string;
    created_at: string | null;
    is_own_application: boolean;
  }[];
  employee_info: {
    id: string;
    full_name: string;
    email: string;
    role: string;
    organization: string;
    department: string;
    designation: string;
    employee_id: string | null;
  };
}

export default function EmployeeDashboardPage() {
  const { user } = useAuth();
  const { t, tStatus, tLoanType } = useLanguage();
  const [data, setData] = useState<EmployeeDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/dashboard/summary`, {
        credentials: "include"
      });
      if (res.status === 403) {
        setError("Access Restricted: This operational console requires authorized employee credentials.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Failed to load operations dashboard (HTTP ${res.status})`);
      }
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || "Failed to connect to institutional operations API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-950/70 text-emerald-300 border-emerald-500/40";
      case "DECLINED":
        return "bg-rose-950/70 text-rose-300 border-rose-500/40";
      case "UNDER_REVIEW":
        return "bg-blue-950/70 text-blue-300 border-blue-500/40";
      case "ADDITIONAL_INFO_REQUIRED":
        return "bg-amber-950/70 text-amber-300 border-amber-500/40";
      case "SUBMITTED":
      default:
        return "bg-slate-800 text-slate-300 border-slate-600/40";
    }
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase font-sans">
                Operations & Underwriting Dashboard
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                CONSOLE LIVE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Institutional credit verification, document compliance, and underwriting workflows
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Queues</span>
            </button>
            <Link
              href="/employee/applications"
              className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
            >
              <span>Application Queue</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-bold text-sm text-rose-100">Operational Notice</p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Officer Information Strip */}
        {data?.employee_info && (
          <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 font-bold flex items-center justify-center text-sm">
                <Building2 className="h-5 w-5 text-amber-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{data.employee_info.full_name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {data.employee_info.employee_id || "OFFICER"}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {data.employee_info.designation} • {data.employee_info.department} ({data.employee_info.organization})
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-6 text-xs">
              <div>
                <p className="text-[10px] uppercase font-mono tracking-wider text-slate-500">Operating Jurisdiction</p>
                <p className="font-semibold text-slate-300 mt-0.5">National Retail & SME</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-mono tracking-wider text-slate-500">Regulatory Framework</p>
                <p className="font-semibold text-amber-400/90 mt-0.5">RBI Master Directions 2024</p>
              </div>
            </div>
          </div>
        )}

        {/* Operational Metrics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Queue Total</span>
              <FileText className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">
              {loading ? "..." : data?.metrics.total_submitted_applications ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Submitted applications</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-blue-900/40 shadow-sm">
            <div className="flex items-center justify-between text-blue-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Under Review</span>
              <Clock className="h-4 w-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-blue-300 mt-2">
              {loading ? "..." : data?.metrics.under_review ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Active underwriter review</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-amber-900/40 shadow-sm">
            <div className="flex items-center justify-between text-amber-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Action Req.</span>
              <AlertCircle className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-300 mt-2">
              {loading ? "..." : data?.metrics.additional_info_required ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Customer clarification</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-emerald-900/40 shadow-sm">
            <div className="flex items-center justify-between text-emerald-400">
              <span className="text-xs font-semibold uppercase tracking-wider">Sanctioned</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-300 mt-2">
              {loading ? "..." : data?.metrics.approved ?? 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Approved applications</p>
          </div>
        </div>

        {/* Secondary Metric Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Pending Document Audits</p>
              <p className="text-xl font-bold text-slate-200 mt-1">
                {loading ? "..." : data?.metrics.pending_documents ?? 0}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">Customer KYC & proofs in queue</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
              <FolderCheck className="h-5 w-5" />
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Initial Review Intake</p>
              <p className="text-xl font-bold text-slate-200 mt-1">
                {loading ? "..." : data?.metrics.submitted ?? 0}
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">Fresh submissions pending triage</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
              <FileText className="h-5 w-5" />
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Institutional Queue Model</p>
              <p className="text-xs font-bold text-amber-400 mt-1 uppercase font-mono">
                Shared Pooled Queue
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">Direct individual assignments: 0</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 border border-amber-500/20">
              <UserCheck className="h-5 w-5" />
            </div>
          </div>
        </div>

        {/* Operational Applications Queue Preview */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-4 bg-[#070D1E] border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Recent Queue Activity
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Active customer loan applications submitted for institutional underwriting
              </p>
            </div>
            <Link
              href="/employee/applications"
              className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
            >
              <span>View Full Queue</span>
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0A1224] text-slate-400 uppercase font-mono text-[11px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Applicant / Case</th>
                  <th className="px-4 py-3">Product</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Tenure</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Submitted</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      Loading queue data...
                    </td>
                  </tr>
                ) : !data?.recent_applications || data.recent_applications.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No customer applications currently in the operational queue.
                    </td>
                  </tr>
                ) : (
                  data.recent_applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-200">
                          {app.applicant_name}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          ID: {app.id.slice(0, 8)}...
                        </div>
                        {app.is_own_application && (
                          <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-bold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.2 rounded">
                            <Lock className="h-3 w-3" /> Conflict: Self-owned
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-medium">
                        {tLoanType(app.loan_type)}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-200">
                        {formatINR(app.requested_amount)}
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {app.tenure} {t("common.months")}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString() : "N/A"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/employee/applications/${app.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded border border-slate-700 text-xs font-semibold transition-colors"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Internal Governance Notice Strip */}
        <div className="p-4 rounded-xl bg-[#0A1224] border border-slate-800 text-slate-400 text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>Governance Protocol:</strong> All underwriter actions and review decisions are recorded in the internal audit trail.
            </span>
          </div>
          <Link
            href="/employee/compliance"
            className="text-amber-400 hover:text-amber-300 font-medium text-xs flex items-center gap-1 shrink-0"
          >
            Review Policy Directives →
          </Link>
        </div>

      </div>
    </EmployeeLayout>
  );
}
