"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  FolderCheck, 
  Search, 
  Filter, 
  RefreshCw, 
  ExternalLink, 
  ShieldAlert, 
  FileText, 
  Building2,
  CheckCircle2,
  Clock,
  AlertTriangle
} from "lucide-react";
import { 
  formatFileSize, 
  getMimeBadge, 
  formatPageCount, 
  sanitizeErrorMessage 
} from "@/lib/documentUtils";

interface DocumentQueueItem {
  id: string;
  application_id: string;
  document_type: string;
  file_url: string;
  status: string;
  created_at: string | null;
  applicant_name: string;
  applicant_email: string;
  loan_type: string;
  application_status: string;
  original_filename?: string | null;
  file_size_bytes?: number | null;
  mime_type?: string | null;
  file_hash?: string | null;
  page_count?: number | null;
}

export default function EmployeeDocumentsPage() {
  const { t, tStatus, tLoanType } = useLanguage();
  const [documents, setDocuments] = useState<DocumentQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const params = new URLSearchParams();
      if (statusFilter !== "ALL") params.append("status", statusFilter);

      const res = await fetch(`${apiUrl}/api/employee/documents?${params.toString()}`, {
        credentials: "include"
      });

      if (res.status === 403) {
        setError("Access Forbidden: Authorized employee verification required.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Failed to fetch documents repository (HTTP ${res.status})`);
      }
      const data = await res.json();
      setDocuments(data || []);
    } catch (err: any) {
      setError(sanitizeErrorMessage(err.message || "Failed to load document records."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter]);

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Customer Document Repository
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                AUDIT EVIDENCE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              KYC proofs and financial documentation submitted across active customer applications
            </p>
          </div>

          <button
            onClick={fetchDocuments}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Records</span>
          </button>
        </div>

        {/* OCR / M07 Boundary Strip */}
        <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <FolderCheck className="h-5 w-5 text-amber-400 shrink-0" />
            <span className="text-slate-300">
              <strong>Module M07 Boundary:</strong> Automated OCR extraction, document tampering detection, and verification scoring integrate under Module M07.
            </span>
          </div>
          <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-400 border border-slate-700 shrink-0">
            OCR PIPELINE ACTIVE
          </span>
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

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 p-3 bg-[#0F172A] border border-slate-800 rounded-xl text-xs">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" /> Filter by Verification State:
          </span>
          {["ALL", "UPLOADED", "PROCESSING", "VERIFIED", "REQUIRES_REUPLOAD", "REJECTED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                statusFilter === st
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold"
                  : "bg-slate-900/60 text-slate-400 border border-slate-800 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {st === "ALL" ? "All Documents" : st.replace(/_/g, " ")}
            </button>
          ))}
          <div className="ml-auto text-[11px] text-slate-400 font-mono">
            {documents.length} records found
          </div>
        </div>

        {/* Documents Table */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0A1224] text-slate-400 uppercase font-mono text-[11px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3.5">Document Type</th>
                  <th className="px-4 py-3.5">Applicant / Case</th>
                  <th className="px-4 py-3.5">Product Facility</th>
                  <th className="px-4 py-3.5">Verification Status</th>
                  <th className="px-4 py-3.5">Upload Date</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                      Loading document repository records...
                    </td>
                  </tr>
                ) : documents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                      No documents found for selected status filter.
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => {
                    const mimeBadge = getMimeBadge(doc.mime_type, doc.original_filename);
                    const pageText = formatPageCount(doc.page_count, doc.mime_type, doc.original_filename);
                    const displayName = doc.original_filename || doc.file_url.split('/').pop() || "Document";

                    return (
                    <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-semibold text-slate-200">
                            {doc.document_type.replace(/_/g, " ")}
                          </span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-700/80 text-slate-200">
                            {mimeBadge}
                          </span>
                          {doc.file_size_bytes != null && (
                            <span className="text-[10px] font-mono text-slate-400">
                              ({formatFileSize(doc.file_size_bytes)})
                            </span>
                          )}
                          {pageText && (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-950/80 text-blue-300 border border-blue-800/60">
                              {pageText}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 truncate max-w-[200px]" title={displayName}>
                          {displayName}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">
                          ID: {doc.id.slice(0, 8)}...
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-medium text-slate-300">{doc.applicant_name}</div>
                        <div className="text-[11px] text-slate-500 truncate max-w-[160px]">{doc.applicant_email}</div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-300">
                        {tLoanType(doc.loan_type)}
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                          {doc.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-slate-400 font-mono text-[11px]">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "N/A"}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${doc.id}/content`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-400 hover:text-amber-300 rounded border border-slate-700 text-xs font-semibold transition-colors"
                          >
                            <span>Inspect File</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                          <Link
                            href={`/employee/applications/${doc.application_id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded border border-slate-700 text-xs font-semibold transition-colors"
                          >
                            <span>Case</span>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
