"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  BookOpen, 
  FileText, 
  Download, 
  ExternalLink, 
  Building2, 
  Globe2, 
  Calendar, 
  History, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Layers, 
  Briefcase, 
  FileCheck2,
  Clock,
  Tag,
  Eye
} from "lucide-react";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  fetchEmployeePolicyDetail, 
  fetchEmployeePolicyHistory, 
  downloadPolicyDocumentBlob, 
  viewPolicyDocumentBlob,
  EmployeePolicyDetail, 
  EmployeePolicyHistoryItem 
} from "@/lib/employeePolicyApi";
import { formatFileSize } from "@/lib/documentUtils";

export default function EmployeePolicyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const policyId = (params?.id as string) || "";

  const [policy, setPolicy] = useState<EmployeePolicyDetail | null>(null);
  const [history, setHistory] = useState<EmployeePolicyHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Download / View action states
  const [isDownloading, setIsDownloading] = useState(false);
  const [isViewing, setIsViewing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadPolicyData = useCallback(async () => {
    if (!policyId) return;
    try {
      setIsLoading(true);
      setError(null);

      const [detailRes, historyRes] = await Promise.all([
        fetchEmployeePolicyDetail(policyId),
        fetchEmployeePolicyHistory(policyId).catch(() => [])
      ]);

      setPolicy(detailRes);
      setHistory(historyRes);
    } catch (err: any) {
      setError(err.message || "Failed to load policy details.");
    } finally {
      setIsLoading(false);
    }
  }, [policyId]);

  useEffect(() => {
    loadPolicyData();
  }, [loadPolicyData]);

  // Document download handler
  const handleDownloadDocument = async (versionId?: string, versionNum?: number) => {
    const vId = versionId || policy?.current_version?.id;
    if (!policy || !vId) return;

    try {
      setIsDownloading(true);
      setActionError(null);
      const filename = `${policy.policy_code}_v${versionNum ?? policy.current_version?.version_number ?? 1}.pdf`;
      await downloadPolicyDocumentBlob(policy.id, vId, filename);
    } catch (err: any) {
      setActionError(err.message || "Failed to download document.");
    } finally {
      setIsDownloading(false);
    }
  };

  // Document view handler
  const handleViewDocument = async (versionId?: string) => {
    const vId = versionId || policy?.current_version?.id;
    if (!policy || !vId) return;

    try {
      setIsViewing(true);
      setActionError(null);
      await viewPolicyDocumentBlob(policy.id, vId);
    } catch (err: any) {
      setActionError(err.message || "Failed to view document.");
    } finally {
      setIsViewing(false);
    }
  };

  // Date formatter
  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "—";
    try {
      return new Date(dateStr).toLocaleDateString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toUpperCase()) {
      case "ACTIVE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            ACTIVE
          </span>
        );
      case "SUPERSEDED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            SUPERSEDED
          </span>
        );
      case "ARCHIVED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30">
            ARCHIVED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            {status}
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <EmployeeLayout>
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="h-6 w-32 bg-slate-800 rounded animate-pulse"></div>
          <div className="h-40 bg-slate-900 border border-slate-800 rounded-xl animate-pulse"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl animate-pulse"></div>
            <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl animate-pulse"></div>
          </div>
        </div>
      </EmployeeLayout>
    );
  }

  if (error || !policy) {
    return (
      <EmployeeLayout>
        <div className="max-w-xl mx-auto py-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Policy Not Accessible</h2>
            <p className="text-xs text-slate-400 mt-1">
              {error || "The requested policy could not be found or is not currently active."}
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/employee/policies"
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Policy Catalog</span>
            </Link>
          </div>
        </div>
      </EmployeeLayout>
    );
  }

  const currentVersion = policy.current_version;

  return (
    <EmployeeLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <Link
            href="/employee/policies"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-amber-300 font-medium transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Policy Catalog</span>
          </Link>

          <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
            EMPLOYEE WORKSPACE • READ-ONLY
          </span>
        </div>

        {/* Action Error Banner */}
        {actionError && (
          <div className="p-3.5 bg-rose-950/80 border border-rose-600/40 rounded-xl flex items-center justify-between text-xs text-rose-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{actionError}</span>
            </div>
            <button
              onClick={() => setActionError(null)}
              className="text-rose-400 hover:text-rose-200 text-xs font-semibold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Policy Header Banner */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="px-2.5 py-1 rounded-lg bg-amber-400/10 text-amber-400 border border-amber-400/30 font-mono text-xs font-bold">
                  {policy.policy_code}
                </span>
                {getStatusBadge(policy.status)}
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px] font-mono">
                  {policy.category}
                </span>
              </div>
              
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                {policy.title}
              </h1>

              {policy.description && (
                <p className="text-xs sm:text-sm text-slate-300 max-w-4xl leading-relaxed">
                  {policy.description}
                </p>
              )}
            </div>

            {/* Quick Document Download / View button in header */}
            {currentVersion?.has_file && (
              <div className="flex flex-wrap sm:flex-col gap-2 shrink-0">
                <button
                  onClick={() => handleViewDocument()}
                  disabled={isViewing}
                  className="px-3.5 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-sm"
                >
                  <Eye className="h-4 w-4" />
                  <span>{isViewing ? "Opening..." : "View Document"}</span>
                </button>
                <button
                  onClick={() => handleDownloadDocument()}
                  disabled={isDownloading}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center justify-center gap-2 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  <span>{isDownloading ? "Downloading..." : "Download PDF"}</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Two Column Grid: Overview & Current Version */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Policy Overview Card */}
          <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
              <BookOpen className="h-4 w-4 text-amber-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider">
                Policy Overview
              </h2>
            </div>

            <dl className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Regulatory Authority
                </dt>
                <dd className="mt-1 text-slate-200 font-medium">
                  {policy.regulatory_authority ? (
                    <div className="flex items-center gap-1.5">
                      <Building2 className="h-3.5 w-3.5 text-slate-400" />
                      <span>{policy.regulatory_authority.name}</span>
                      <span className="text-[10px] font-mono text-amber-400 bg-amber-400/10 px-1 rounded">
                        {policy.regulatory_authority.code}
                      </span>
                    </div>
                  ) : (
                    <span className="text-slate-400 font-mono">Internal Directive</span>
                  )}
                </dd>
              </div>

              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Jurisdiction
                </dt>
                <dd className="mt-1 text-slate-200 font-medium flex items-center gap-1.5">
                  <Globe2 className="h-3.5 w-3.5 text-slate-400" />
                  <span>{policy.jurisdiction}</span>
                </dd>
              </div>

              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Policy Type
                </dt>
                <dd className="mt-1 text-slate-200 font-mono">
                  {policy.policy_type?.replace(/_/g, " ")}
                </dd>
              </div>

              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Institution
                </dt>
                <dd className="mt-1 text-slate-200 font-medium">
                  {policy.institution || "Institutional Master"}
                </dd>
              </div>

              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Effective From
                </dt>
                <dd className="mt-1 text-slate-200 font-mono">
                  {formatDate(policy.effective_from)}
                </dd>
              </div>

              <div>
                <dt className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
                  Effective To
                </dt>
                <dd className="mt-1 text-slate-200 font-mono">
                  {policy.effective_to ? formatDate(policy.effective_to) : "Open-ended (No expiry)"}
                </dd>
              </div>

              <div className="col-span-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Created: {formatDate(policy.created_at)}</span>
                <span>Last Updated: {formatDate(policy.updated_at)}</span>
              </div>
            </dl>
          </div>

          {/* Current Active Version & Document Access */}
          <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-200">
              <div className="flex items-center gap-2">
                <FileCheck2 className="h-4 w-4 text-emerald-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider">
                  Current Active Version
                </h2>
              </div>
              {currentVersion && (
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-mono font-bold">
                  v{currentVersion.version_number}
                </span>
              )}
            </div>

            {currentVersion ? (
              <div className="space-y-4 text-xs">
                <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                      <FileText className="h-4 w-4 text-amber-400" />
                      Official Policy Document
                    </span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                      {formatFileSize(currentVersion.file_size)}
                    </span>
                  </div>
                  
                  {currentVersion.changelog && (
                    <div className="pt-2 border-t border-slate-800">
                      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block">
                        Changelog / Release Summary:
                      </span>
                      <p className="text-slate-300 mt-1 text-[11px] leading-relaxed italic">
                        &quot;{currentVersion.changelog}&quot;
                      </p>
                    </div>
                  )}

                  <div className="pt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                    <span>Published: {formatDate(currentVersion.published_at)}</span>
                    <span className="text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Verified Active
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-1">
                  <button
                    onClick={() => handleViewDocument()}
                    disabled={isViewing || !currentVersion.has_file}
                    className="flex-1 py-2 px-3 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors"
                  >
                    <Eye className="h-4 w-4" />
                    <span>{isViewing ? "Opening..." : "View Document"}</span>
                  </button>

                  <button
                    onClick={() => handleDownloadDocument()}
                    disabled={isDownloading || !currentVersion.has_file}
                    className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 rounded-lg font-medium border border-slate-700 flex items-center justify-center gap-2 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    <span>{isDownloading ? "Downloading..." : "Download Document"}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-400">
                No active version file currently associated with this policy.
              </div>
            )}
          </div>

        </div>

        {/* Applicability Dimensions Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-200">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-amber-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider">
                Policy Applicability Dimensions
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              {policy.applicabilities?.length || 0} Scope Rule(s) Defined
            </span>
          </div>

          {policy.applicabilities && policy.applicabilities.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              {policy.applicabilities.map((app) => (
                <div 
                  key={app.id} 
                  className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold text-amber-400 uppercase">
                      Scope Rule
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {formatDate(app.created_at)}
                    </span>
                  </div>

                  <div className="space-y-1 text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-500 text-[11px]">Institution:</span>
                      <span className="font-medium text-slate-200">{app.institution || "All Institutions"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500 text-[11px]">Jurisdiction:</span>
                      <span className="font-medium text-slate-200">{app.jurisdiction || "All"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500 text-[11px]">Loan Product:</span>
                      <span className="font-medium text-slate-200">{app.loan_type || "All Products"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500 text-[11px]">Department:</span>
                      <span className="font-medium text-slate-200">{app.department || "All Departments"}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg flex items-center gap-3 text-xs text-slate-300">
              <ShieldCheck className="h-4 w-4 text-blue-400 shrink-0" />
              <span>
                <strong>General applicability:</strong> This active policy has institutional-wide scope and applies to all loan products, departments, and underwriting operations without restrictive overrides.
              </span>
            </div>
          )}
        </div>

        {/* Version History Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 bg-[#070D1E] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-200">
              <History className="h-4 w-4 text-amber-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider">
                Policy Version History & Lineage
              </h2>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              {history.length} Version(s) Recorded
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-900/60 border-b border-slate-800 text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-4 font-semibold">Version</th>
                  <th className="py-2.5 px-4 font-semibold">Status</th>
                  <th className="py-2.5 px-4 font-semibold">Effective Period</th>
                  <th className="py-2.5 px-4 font-semibold">Changelog</th>
                  <th className="py-2.5 px-4 font-semibold">Published</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Document Access</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 px-4 text-center text-slate-500">
                      No historical versions recorded for this policy.
                    </td>
                  </tr>
                ) : (
                  history.map((v) => (
                    <tr key={v.id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Version number */}
                      <td className="py-3 px-4 font-mono font-bold text-slate-200 whitespace-nowrap">
                        v{v.version_number}
                        {v.version_number === currentVersion?.version_number && (
                          <span className="ml-2 text-[10px] font-sans font-normal text-amber-400 bg-amber-400/10 px-1.5 py-0.2 rounded border border-amber-400/20">
                            Current
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getStatusBadge(v.status)}
                      </td>

                      {/* Effective Period */}
                      <td className="py-3 px-4 whitespace-nowrap text-slate-300 font-mono text-[11px]">
                        <span>{formatDate(v.effective_from)}</span>
                        {v.effective_to && (
                          <span className="text-slate-500 block">to {formatDate(v.effective_to)}</span>
                        )}
                      </td>

                      {/* Changelog */}
                      <td className="py-3 px-4 text-slate-300 max-w-sm">
                        <span className="line-clamp-2">
                          {v.changelog || "Initial baseline release"}
                        </span>
                      </td>

                      {/* Published Date */}
                      <td className="py-3 px-4 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                        {formatDate(v.published_at || v.created_at)}
                      </td>

                      {/* Document Actions */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        {v.has_file ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleViewDocument(v.id)}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded text-[11px] font-medium border border-slate-700 transition-colors"
                              title="View Document in browser"
                            >
                              <Eye className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => handleDownloadDocument(v.id, v.version_number)}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded text-[11px] font-medium border border-slate-700 transition-colors"
                              title="Download PDF"
                            >
                              <Download className="h-3 w-3" />
                            </button>
                          </div>
                        ) : (
                          <span className="text-slate-500 font-mono text-[11px]">No file</span>
                        )}
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
