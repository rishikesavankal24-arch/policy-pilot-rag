"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { Plus, Search, FileText, ArrowRight, ArrowUpDown, Filter, FolderOpen, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageContext";

export default function ApplicationsPage() {
  const { t, tStatus, tLoanType } = useLanguage();
  const [applications, setApplications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sortField, setSortField] = useState<"created_at" | "requested_amount">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const inFlightRef = useRef(false);

  const fetchApplications = useCallback(async (isBackground = false) => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    if (!isBackground) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/applications`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setApplications(data);
        setError(null);
      } else if (res.status === 401) {
        setError(t("applications.sessionExpired"));
      } else if (res.status === 403) {
        setError(t("applications.accessDenied"));
      } else if (res.status >= 500) {
        setError(t("applications.serverError"));
      } else {
        setError(t("applications.failedToLoad"));
      }
    } catch {
      setError(t("applications.networkError"));
    } finally {
      inFlightRef.current = false;
      if (!isBackground) {
        setIsLoading(false);
      }
    }
  }, [t]);

  useEffect(() => {
    fetchApplications(false);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchApplications(true);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchApplications]);

  const statusOptions = [
    { key: "ALL", label: t("applications.filterAll") },
    { key: "DRAFT", label: t("applications.filterDraft") },
    { key: "SUBMITTED", label: t("applications.filterSubmitted") },
    { key: "UNDER_REVIEW", label: t("applications.filterUnderReview") },
    { key: "ADDITIONAL_INFO_REQUIRED", label: t("applications.filterActionRequired") },
    { key: "APPROVED", label: t("applications.filterApproved") },
    { key: "DECLINED", label: t("applications.filterDeclined") },
  ];

  const filteredApplications = useMemo(() => {
    return applications
      .filter((app) => {
        const matchesStatus = statusFilter === "ALL" || app.status === statusFilter;
        const matchesQuery = 
          !searchQuery.trim() ||
          app.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (app.loan_type && app.loan_type.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (app.purpose && app.purpose.toLowerCase().includes(searchQuery.toLowerCase()));
        return matchesStatus && matchesQuery;
      })
      .sort((a, b) => {
        if (sortField === "requested_amount") {
          const amtA = Number(a.requested_amount) || 0;
          const amtB = Number(b.requested_amount) || 0;
          return sortOrder === "asc" ? amtA - amtB : amtB - amtA;
        } else {
          const dateA = new Date(a.created_at || 0).getTime();
          const dateB = new Date(b.created_at || 0).getTime();
          return sortOrder === "asc" ? dateA - dateB : dateB - dateA;
        }
      });
  }, [applications, statusFilter, searchQuery, sortField, sortOrder]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-50 text-emerald-800 border-emerald-300";
      case "DECLINED":
        return "bg-red-50 text-red-800 border-red-300";
      case "ADDITIONAL_INFO_REQUIRED":
        return "bg-amber-50 text-amber-800 border-amber-300";
      case "UNDER_REVIEW":
        return "bg-blue-50 text-blue-800 border-blue-300";
      case "SUBMITTED":
        return "bg-slate-100 text-slate-800 border-slate-300";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  const toggleSort = (field: "created_at" | "requested_amount") => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 text-slate-900">
        
        {/* Header Strip */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold uppercase tracking-tight text-slate-950">
                {t("applications.title")}
              </h1>
              <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                {filteredApplications.length} of {applications.length}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{t("applications.subtitle")}</p>
          </div>

          <Link 
            href="/dashboard/applications/new" 
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors shadow-xs"
          >
            <Plus className="h-4 w-4" />
            <span>{t("applications.newApplication")}</span>
          </Link>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 text-xs text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Filter and Search Bar */}
        <div className="bg-white border border-slate-200 rounded p-4 shadow-xs space-y-3">
          <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input 
                type="text" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("applications.searchPlaceholder")} 
                className="w-full pl-9 pr-4 py-2 text-xs border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white font-sans"
              />
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Filter className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <span className="font-semibold uppercase tracking-wider text-[11px] text-slate-500">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B192C]"
              >
                {statusOptions.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pt-1 pb-1 scrollbar-none">
            {statusOptions.map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setStatusFilter(opt.key)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors shrink-0 ${
                  statusFilter === opt.key
                    ? "bg-[#0B192C] text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Applications Ledger Table */}
        <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
          {isLoading ? (
            <div className="flex flex-col h-48 items-center justify-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{t("common.loading")}</p>
            </div>
          ) : filteredApplications.length === 0 ? (
            <div className="text-center py-12 px-4">
              <FolderOpen className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">{t("applications.noApplicationsTitle")}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">{t("applications.noApplicationsSubtitle")}</p>
              <Link 
                href="/dashboard/applications/new" 
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>{t("applications.startFirstApp")}</span>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="text-[11px] text-slate-600 uppercase tracking-wider bg-slate-100/70 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("applications.tableId")}</th>
                    <th className="px-4 py-3 font-semibold">{t("applications.tableType")}</th>
                    <th 
                      className="px-4 py-3 font-semibold cursor-pointer hover:bg-slate-200/60 transition-colors select-none"
                      onClick={() => toggleSort("requested_amount")}
                    >
                      <div className="flex items-center gap-1">
                        <span>{t("applications.tableAmount")}</span>
                        <ArrowUpDown className="h-3 w-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-4 py-3 font-semibold">{t("applications.tableStatus")}</th>
                    <th 
                      className="px-4 py-3 font-semibold cursor-pointer hover:bg-slate-200/60 transition-colors select-none"
                      onClick={() => toggleSort("created_at")}
                    >
                      <div className="flex items-center gap-1">
                        <span>{t("dashboard.tableDate")}</span>
                        <ArrowUpDown className="h-3 w-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-4 py-3 font-semibold">{t("applications.tableUpdated")}</th>
                    <th className="px-4 py-3 font-semibold text-right">{t("applications.tableAction")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-sans">
                  {filteredApplications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                        {app.id}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800">
                        {tLoanType(app.loan_type)}
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-900">
                        {app.requested_amount ? `₹${Number(app.requested_amount).toLocaleString('en-IN')}` : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        }) : "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                        {app.updated_at ? new Date(app.updated_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        }) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link 
                          href={`/dashboard/applications/${app.id}`}
                          className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:text-blue-900 hover:underline"
                        >
                          <span>{app.status === 'DRAFT' ? t("applicationDetails.editDraft") : t("dashboard.viewDossier")}</span>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </AuthenticatedLayout>
  );
}
