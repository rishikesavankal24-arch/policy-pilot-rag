"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  FileText, 
  Search, 
  Filter, 
  RefreshCw, 
  ExternalLink, 
  ShieldAlert, 
  Lock, 
  FolderCheck,
  Building2,
  Clock,
  CheckCircle2,
  AlertCircle,
  X
} from "lucide-react";

interface ApplicationQueueItem {
  id: string;
  user_id: string;
  loan_type: string;
  requested_amount: number;
  tenure: number;
  purpose: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  applicant_name: string;
  applicant_email: string;
  is_own_application: boolean;
  document_count: number;
}

export default function EmployeeApplicationsQueuePage() {
  const { user } = useAuth();
  const { t, tStatus, tLoanType } = useLanguage();
  
  const [applications, setApplications] = useState<ApplicationQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [loanTypeFilter, setLoanTypeFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const fetchApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const params = new URLSearchParams();
      if (statusFilter !== "ALL") params.append("status", statusFilter);
      if (loanTypeFilter !== "ALL") params.append("loan_type", loanTypeFilter);
      if (searchTerm.trim()) params.append("search", searchTerm.trim());

      const res = await fetch(`${apiUrl}/api/employee/applications?${params.toString()}`, {
        credentials: "include"
      });

      if (res.status === 403) {
        setError("Access Forbidden: Authorized employee verification required.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Failed to fetch application queue (HTTP ${res.status})`);
      }
      const data = await res.json();
      setApplications(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load applications queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter, loanTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchApplications();
  };

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
        
        {/* Header Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Institutional Application Queue
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                ACTIVE QUEUE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Centralized underwriting intake. Private customer drafts are strictly excluded.
            </p>
          </div>

          <button
            onClick={fetchApplications}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Queue</span>
          </button>
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

        {/* Search & Filter Controls */}
        <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl space-y-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search applicant name, email, loan product, or application ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-8 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-400/60"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm("");
                    // Refetch without search
                    setTimeout(() => fetchApplications(), 50);
                  }}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <button
              type="submit"
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold transition-colors"
            >
              Search
            </button>
          </form>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800 text-xs">
            <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mr-1 flex items-center gap-1">
              <Filter className="h-3 w-3" /> Status:
            </span>
            {["ALL", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFO_REQUIRED", "APPROVED", "DECLINED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  statusFilter === st
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold"
                    : "bg-slate-900/60 text-slate-400 border border-slate-800 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                {st === "ALL" ? "All Cases" : tStatus(st)}
              </button>
            ))}

            <div className="ml-auto hidden md:flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-400">Total in view:</span>
              <span className="text-[11px] font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                {applications.length}
              </span>
            </div>
          </div>
        </div>

        {/* Application Queue Table */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0A1224] text-slate-400 uppercase font-mono text-[11px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3.5">Case Reference</th>
                  <th className="px-4 py-3.5">Applicant Details</th>
                  <th className="px-4 py-3.5">Product & Purpose</th>
                  <th className="px-4 py-3.5">Amount / Tenure</th>
                  <th className="px-4 py-3.5">Docs</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Timeline</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      <div className="flex flex-col items-center gap-2">
                        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
                        <span>Loading institutional queue records...</span>
                      </div>
                    </td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      <FileText className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                      <p className="text-xs font-semibold text-slate-300">No applications match current filters</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">Try resetting search filters or check back later</p>
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3.5 font-mono">
                        <span className="text-amber-400/90 font-semibold">{app.id.slice(0, 8)}</span>
                        <span className="text-slate-500 block text-[10px]">VER-{app.id.slice(9, 13)}</span>
                        {app.is_own_application && (
                          <span className="inline-flex items-center gap-1 mt-1 text-[9px] font-bold text-amber-300 bg-amber-500/20 border border-amber-500/40 px-1.5 py-0.2 rounded uppercase">
                            <Lock className="h-2.5 w-2.5" /> Self-Owned
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-200">{app.applicant_name}</div>
                        <div className="text-[11px] text-slate-400 truncate max-w-[160px]">{app.applicant_email}</div>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="font-medium text-slate-300 block">{tLoanType(app.loan_type)}</span>
                        <span className="text-[11px] text-slate-500 truncate max-w-[180px] block mt-0.5">
                          {app.purpose}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="font-bold text-slate-100">{formatINR(app.requested_amount)}</span>
                        <span className="text-slate-400 block text-[11px]">{app.tenure} {t("common.months")}</span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px]">
                          <FolderCheck className="h-3 w-3 text-slate-400" />
                          {app.document_count}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-[11px] text-slate-400 font-mono">
                        <div>Sub: {app.created_at ? new Date(app.created_at).toLocaleDateString() : "N/A"}</div>
                        {app.updated_at && app.updated_at !== app.created_at && (
                          <div className="text-[10px] text-slate-500">Upd: {new Date(app.updated_at).toLocaleDateString()}</div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/employee/applications/${app.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg border border-slate-700 text-xs font-semibold transition-colors"
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

      </div>
    </EmployeeLayout>
  );
}
