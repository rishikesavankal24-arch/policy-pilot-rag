"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useLanguage } from "@/i18n/LanguageContext";
import { getActiveSessionToken } from "@/lib/session";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Lock,
  CheckCircle2,
  FileText,
  User,
  Calendar,
  CreditCard,
  Clock,
  ExternalLink,
  AlertTriangle,
  Info,
  Layers,
  Check,
  XCircle,
  HelpCircle,
  Send,
  MessageSquare,
  Sparkles,
  ClipboardList,
  Save,
  CheckSquare,
  AlertCircle
} from "lucide-react";

interface DocumentItem {
  id: string;
  document_type: string;
  file_url: string;
  status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface InformationRequestItem {
  id: string;
  application_id: string;
  requested_by: string;
  title: string;
  description: string;
  requested_document_type: string | null;
  status: string;
  response_document_id: string | null;
  response_document_url: string | null;
  response_notes: string | null;
  created_at: string | null;
  responded_at: string | null;
}

interface ComplianceChecklistItem {
  id: string;
  application_id: string;
  item_key: string;
  category: string;
  title: string;
  description: string | null;
  status: "PENDING" | "REVIEWED" | "REQUIRES_INFORMATION" | "NOT_APPLICABLE";
  notes: string | null;
  display_order: number;
  updated_by: string | null;
  updated_by_name: string | null;
  updated_at: string | null;
  created_at: string | null;
}

interface ComplianceReviewNote {
  id: string;
  application_id: string;
  author_id: string;
  author_name: string;
  author_email: string;
  note: string;
  created_at: string;
}

interface ComplianceAuditEventItem {
  id: string;
  event_type: string;
  title: string;
  description: string;
  user_id: string | null;
  created_at: string | null;
}

interface ComplianceWorkspaceData {
  application: {
    id: string;
    user_id: string;
    loan_type: string;
    requested_amount: number;
    tenure: number;
    purpose: string;
    employment_info: string | null;
    income_info: string | null;
    existing_liabilities: string | null;
    status: string;
    created_at: string | null;
    updated_at: string | null;
  };
  applicant: {
    id: string | null;
    full_name: string;
    email: string;
    phone_number: string | null;
    date_of_birth: string | null;
    address: string | null;
    city: string | null;
    state: string | null;
    pincode: string | null;
    created_at: string | null;
  };
  documents: DocumentItem[];
  checklist_items: ComplianceChecklistItem[];
  review_notes: ComplianceReviewNote[];
  information_requests: InformationRequestItem[];
  audit_events: ComplianceAuditEventItem[];
  ai_rag_boundary: {
    status: string;
    feature: string;
    message: string;
  };
}

export default function EmployeeComplianceWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const { tStatus, tLoanType } = useLanguage();

  const id = params?.id as string;

  const [data, setData] = useState<ComplianceWorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Local draft state for checklist items { [itemId]: { status, notes } }
  const [checklistDrafts, setChecklistDrafts] = useState<
    Record<string, { status: string; notes: string }>
  >({});
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [itemSaveError, setItemSaveError] = useState<string | null>(null);

  // New Compliance Note state
  const [newNote, setNewNote] = useState("");
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  const formatINR = (val?: number) => {
    if (val === undefined || val === null) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val);
  };

  const getHeaders = useCallback(() => {
    const token = getActiveSessionToken("/employee");
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }, []);

  const fetchWorkspace = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setConflictError(null);
      setGeneralError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}/compliance`, {
        headers: getHeaders(),
        credentials: "include"
      });

      if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        if (errData.detail && errData.detail.toLowerCase().includes("conflict of interest")) {
          setConflictError(errData.detail);
        } else {
          setGeneralError(errData.detail || "Forbidden: You do not have permission to view this compliance workspace.");
        }
        return;
      }

      if (res.status === 404) {
        setGeneralError("Application not found in the operations queue.");
        return;
      }

      if (res.status === 400) {
        const errData = await res.json().catch(() => ({}));
        setGeneralError(errData.detail || "Draft applications cannot be evaluated in the compliance workspace.");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to load compliance workspace (HTTP ${res.status})`);
      }

      const json: ComplianceWorkspaceData = await res.json();
      setData(json);

      // Initialize draft edits for checklist
      const initialDrafts: Record<string, { status: string; notes: string }> = {};
      json.checklist_items.forEach((item) => {
        initialDrafts[item.id] = {
          status: item.status,
          notes: item.notes || ""
        };
      });
      setChecklistDrafts(initialDrafts);
    } catch (err: any) {
      setGeneralError(err.message || "Failed to load compliance workspace.");
    } finally {
      setLoading(false);
    }
  }, [id, getHeaders]);

  useEffect(() => {
    fetchWorkspace();
  }, [fetchWorkspace]);

  // Handle Checklist Draft updates
  const handleChecklistFieldChange = (itemId: string, field: "status" | "notes", value: string) => {
    setChecklistDrafts((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value
      }
    }));
  };

  // Save single checklist item
  const handleSaveChecklistItem = async (itemId: string) => {
    if (!id) return;
    const draft = checklistDrafts[itemId];
    if (!draft) return;

    try {
      setSavingItemId(itemId);
      setItemSaveError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}/compliance/checklist/${itemId}`, {
        method: "PATCH",
        headers: getHeaders(),
        credentials: "include",
        body: JSON.stringify({
          status: draft.status,
          notes: draft.notes
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to update checklist item (HTTP ${res.status})`);
      }

      const updatedItem: ComplianceChecklistItem = await res.json();

      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          checklist_items: prev.checklist_items.map((it) => (it.id === itemId ? updatedItem : it))
        };
      });

      setSuccessMessage("Compliance checklist item updated successfully.");
      setTimeout(() => setSuccessMessage(null), 3500);
      // Re-fetch to refresh audit events
      fetchWorkspace();
    } catch (err: any) {
      setItemSaveError(err.message || "Error updating checklist item.");
    } finally {
      setSavingItemId(null);
    }
  };

  // Submit new compliance note
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim() || !id) return;

    try {
      setIsSubmittingNote(true);
      setNoteError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}/compliance/notes`, {
        method: "POST",
        headers: getHeaders(),
        credentials: "include",
        body: JSON.stringify({
          note: newNote.trim()
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to record note (HTTP ${res.status})`);
      }

      const recordedNote: ComplianceReviewNote = await res.json();
      setNewNote("");
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          review_notes: [recordedNote, ...prev.review_notes]
        };
      });

      setSuccessMessage("Compliance review note recorded.");
      setTimeout(() => setSuccessMessage(null), 3500);
      // Re-fetch to refresh audit events
      fetchWorkspace();
    } catch (err: any) {
      setNoteError(err.message || "Error submitting review note.");
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const getChecklistCategoryBadge = (cat: string) => {
    switch (cat) {
      case "DOCUMENT_COMPLETENESS":
        return "bg-blue-950/80 text-blue-300 border-blue-500/40";
      case "FINANCIAL_VERIFICATION":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-500/40";
      case "LOAN_PURPOSE_ALIGNMENT":
        return "bg-purple-950/80 text-purple-300 border-purple-500/40";
      case "DATA_CONSISTENCY":
        return "bg-amber-950/80 text-amber-300 border-amber-500/40";
      case "POLICY_EVIDENCE":
        return "bg-cyan-950/80 text-cyan-300 border-cyan-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SUBMITTED":
        return "bg-blue-950 text-blue-300 border-blue-600/40";
      case "UNDER_REVIEW":
        return "bg-amber-950 text-amber-300 border-amber-500/40 animate-pulse";
      case "ADDITIONAL_INFO_REQUIRED":
        return "bg-purple-950 text-purple-300 border-purple-500/40";
      case "APPROVED":
        return "bg-emerald-950 text-emerald-300 border-emerald-500/40";
      case "DECLINED":
        return "bg-rose-950 text-rose-300 border-rose-500/40";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const getChecklistStatusColor = (status: string) => {
    switch (status) {
      case "REVIEWED":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-500/50";
      case "REQUIRES_INFORMATION":
        return "bg-sky-950/80 text-sky-300 border-sky-500/50";
      case "NOT_APPLICABLE":
        return "bg-slate-800/80 text-slate-400 border-slate-700";
      case "PENDING":
      default:
        return "bg-amber-950/80 text-amber-300 border-amber-500/50";
    }
  };

  const getDocumentStatusBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
      case "ACCEPTED":
        return "bg-emerald-950 text-emerald-300 border-emerald-500/40";
      case "REJECTED":
        return "bg-rose-950 text-rose-300 border-rose-500/40";
      case "REQUIRES_REUPLOAD":
        return "bg-amber-950 text-amber-300 border-amber-500/40";
      case "UNDER_REVIEW":
        return "bg-blue-950 text-blue-300 border-blue-500/40";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <EmployeeLayout>
      <div className="max-w-7xl mx-auto space-y-6 pb-12">
        {/* Breadcrumb & Top Navigation */}
        <div className="flex items-center gap-2">
          <Link
            href={`/employee/applications/${id}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold border border-slate-700 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Application Dossier</span>
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-xs font-mono text-slate-400 truncate max-w-[220px]">
            Case #{id ? id.slice(0, 8) : ""} / Compliance Workspace
          </span>
        </div>

        {/* Success Alert */}
        {successMessage && (
          <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-200 text-xs flex items-center gap-2 shadow-sm animate-in fade-in duration-200">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="font-medium">{successMessage}</span>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="p-16 text-center text-slate-400">
            <div className="w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-xs uppercase tracking-wider font-mono">
              Loading Compliance Workspace...
            </p>
          </div>
        )}

        {/* Conflict of Interest Block */}
        {conflictError && (
          <div className="p-8 rounded-2xl bg-amber-950/40 border-2 border-amber-500/60 text-amber-200 shadow-2xl space-y-4">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 border border-amber-500/40">
                <Lock className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white uppercase tracking-wider">
                  Conflict of Interest Protected
                </h2>
                <p className="text-xs text-amber-300/90 font-mono mt-0.5">
                  POLICY ENFORCEMENT: RULE 12-B (INDEPENDENT REVIEW MANDATE)
                </p>
                <p className="text-sm text-amber-100 mt-2 leading-relaxed">
                  {conflictError}
                </p>
                <p className="text-xs text-amber-300/80 mt-2 leading-relaxed">
                  Under institutional banking underwriting guidelines, loan officers and authorized bank employees cannot review, evaluate, or approve applications submitted by themselves. This application has been flagged in the centralized queue and will be processed exclusively by an independent officer.
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-amber-500/30 flex items-center justify-end">
              <Link
                href="/employee/applications"
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold transition-colors shadow-sm"
              >
                Return to Operational Queue
              </Link>
            </div>
          </div>
        )}

        {/* General Error */}
        {generalError && !conflictError && (
          <div className="p-6 rounded-xl bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-bold text-sm text-rose-100">Access Restricted</p>
              <p className="mt-1">{generalError}</p>
              <div className="mt-4">
                <Link
                  href="/employee/applications"
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
                >
                  Return to Application Queue
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Loaded Compliance Workspace */}
        {data && !loading && (
          <div className="space-y-6">
            {/* Header Banner */}
            <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <ShieldCheck className="h-5 w-5 text-emerald-400" />
                    <h1 className="text-lg font-bold text-white tracking-tight">
                      Compliance Workspace: {data.applicant.full_name}
                    </h1>
                    <span
                      className={`px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${getStatusBadge(
                        data.application.status
                      )}`}
                    >
                      {tStatus(data.application.status)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    APPLICATION ID: {data.application.id} • FACILITY:{" "}
                    {tLoanType(data.application.loan_type)} • SUBMITTED:{" "}
                    {data.application.created_at
                      ? new Date(data.application.created_at).toLocaleString()
                      : "N/A"}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <span className="px-3 py-1.5 rounded-lg bg-slate-800 text-emerald-300 border border-slate-700 font-mono text-xs font-bold">
                    REQUESTED FACILITY: {formatINR(data.application.requested_amount)}
                  </span>
                  <Link
                    href={`/employee/applications/${data.application.id}`}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>View Application Dossier</span>
                  </Link>
                </div>
              </div>
            </div>

            {/* M10 Architectural Boundary Notice Banner */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-blue-950/40 border border-emerald-500/30 shadow-sm flex items-start gap-3.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-mono font-bold tracking-wider uppercase">
                    MODULE M10 BOUNDARY: MANUAL COMPLIANCE AUDITING ACTIVE
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Adaptive RAG, hybrid BM25 / vector retrieval, evidence reranking, and automated policy cross-referencing are reserved for <strong className="text-white">Module M10</strong>. This compliance review workspace is strictly human-verified. Checklist evaluations and notes are recorded directly to the bank&apos;s immutable audit trail.
                </p>
              </div>
            </div>

            {/* Main 2-Column Responsive Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Left 2 Columns: Application Data, Document Checklist & Interactive Compliance Checklist */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* Application & Applicant KYC Summary */}
                <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2 text-slate-200">
                      <User className="h-4 w-4 text-emerald-400" />
                      <h2 className="text-xs font-bold uppercase tracking-wider">
                        Applicant Profile & Facility Summary
                      </h2>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      Applicant ID: {data.applicant.id ? data.applicant.id.slice(0, 8) : "N/A"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="text-slate-500 block">Full Legal Name</span>
                      <span className="font-semibold text-slate-200">{data.applicant.full_name}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Contact Email</span>
                      <span className="font-semibold text-slate-200">{data.applicant.email}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Phone Number</span>
                      <span className="font-semibold text-slate-200">{data.applicant.phone_number || "Not provided"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Date of Birth</span>
                      <span className="font-semibold text-slate-200">{data.applicant.date_of_birth || "Not provided"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Location / City</span>
                      <span className="font-semibold text-slate-200">
                        {[data.applicant.city, data.applicant.state, data.applicant.pincode].filter(Boolean).join(", ") || "Not provided"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Loan Purpose</span>
                      <span className="font-semibold text-slate-200">{data.application.purpose}</span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div>
                      <span className="text-slate-500 block">Declared Employment</span>
                      <span className="text-slate-300 font-mono text-[11px]">{data.application.employment_info || "None declared"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Declared Income</span>
                      <span className="text-slate-300 font-mono text-[11px]">{data.application.income_info || "None declared"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Existing Liabilities</span>
                      <span className="text-slate-300 font-mono text-[11px]">{data.application.existing_liabilities || "None declared"}</span>
                    </div>
                  </div>
                </div>

                {/* Uploaded Documents Verification Status */}
                <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2 text-slate-200">
                      <FileText className="h-4 w-4 text-emerald-400" />
                      <h2 className="text-xs font-bold uppercase tracking-wider">
                        Submitted Verification Documents ({data.documents.length})
                      </h2>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      Inspect uploaded evidence files
                    </span>
                  </div>

                  {data.documents.length === 0 ? (
                    <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-400 text-center">
                      No documents currently attached to this application.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {data.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white uppercase tracking-wider">
                                {doc.document_type.replace(/_/g, " ")}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getDocumentStatusBadge(
                                  doc.status
                                )}`}
                              >
                                {doc.status}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 font-mono">
                              Uploaded: {doc.created_at ? new Date(doc.created_at).toLocaleString() : "N/A"}
                            </p>
                            {doc.review_notes && (
                              <p className="text-xs text-amber-300/90 italic mt-1">
                                Officer Note: {doc.review_notes}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}${doc.file_url}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 rounded text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
                            >
                              <ExternalLink className="h-3 w-3" />
                              <span>View File</span>
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Interactive Compliance Verification Checklist */}
                <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center gap-2 text-slate-200">
                      <ClipboardList className="h-4 w-4 text-emerald-400" />
                      <h2 className="text-xs font-bold uppercase tracking-wider">
                        Compliance Verification Checklist ({data.checklist_items.length} Items)
                      </h2>
                    </div>
                    <span className="text-[11px] text-slate-400 font-mono">
                      Institutional Audit Standards
                    </span>
                  </div>

                  {itemSaveError && (
                    <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
                      <span>{itemSaveError}</span>
                    </div>
                  )}

                  <div className="space-y-4">
                    {data.checklist_items.map((item, idx) => {
                      const draft = checklistDrafts[item.id] || {
                        status: item.status,
                        notes: item.notes || ""
                      };
                      const isSaving = savingItemId === item.id;

                      return (
                        <div
                          key={item.id}
                          className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 hover:border-slate-700 transition-colors"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 font-mono text-[11px] font-bold flex items-center justify-center">
                                {idx + 1}
                              </span>
                              <span className="text-xs font-bold text-white">
                                {item.title}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getChecklistCategoryBadge(
                                  item.category
                                )}`}
                              >
                                {item.category.replace(/_/g, " ")}
                              </span>
                            </div>

                            <span
                              className={`px-2.5 py-0.5 rounded text-[10px] font-bold font-mono uppercase border self-start sm:self-auto ${getChecklistStatusColor(
                                item.status
                              )}`}
                            >
                              Current: {item.status.replace(/_/g, " ")}
                            </span>
                          </div>

                          {item.description && (
                            <p className="text-xs text-slate-400 leading-relaxed">
                              {item.description}
                            </p>
                          )}

                          {/* Interactive Status Selector and Officer Notes */}
                          <div className="pt-2 border-t border-slate-800/80 space-y-3">
                            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                              <label className="text-xs font-semibold text-slate-300 shrink-0">
                                Verification Status:
                              </label>
                              <div className="flex flex-wrap gap-1.5">
                                {(
                                  [
                                    "PENDING",
                                    "REVIEWED",
                                    "REQUIRES_INFORMATION",
                                    "NOT_APPLICABLE"
                                  ] as const
                                ).map((st) => {
                                  const isSelected = draft.status === st;
                                  return (
                                    <button
                                      key={st}
                                      type="button"
                                      onClick={() =>
                                        handleChecklistFieldChange(item.id, "status", st)
                                      }
                                      className={`px-2.5 py-1 rounded text-xs font-semibold border transition-all ${
                                        isSelected
                                          ? "bg-emerald-600 text-white border-emerald-500 shadow-sm"
                                          : "bg-slate-800 text-slate-300 hover:text-white border-slate-700 hover:bg-slate-700"
                                      }`}
                                    >
                                      {st.replace(/_/g, " ")}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>

                            <div>
                              <label className="block text-xs font-semibold text-slate-300 mb-1">
                                Verification Notes & Findings:
                              </label>
                              <textarea
                                value={draft.notes}
                                onChange={(e) =>
                                  handleChecklistFieldChange(item.id, "notes", e.target.value)
                                }
                                placeholder="Record verification rationale, policy reference, or rationale for status change..."
                                rows={2}
                                className="w-full px-3 py-2 bg-[#0F172A] border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-400"
                              />
                            </div>

                            <div className="flex items-center justify-between pt-1">
                              <div className="text-[11px] text-slate-500 font-mono">
                                {item.updated_by_name && (
                                  <span>
                                    Last verified by {item.updated_by_name}
                                    {item.updated_at &&
                                      ` on ${new Date(item.updated_at).toLocaleString()}`}
                                  </span>
                                )}
                              </div>

                              <button
                                type="button"
                                onClick={() => handleSaveChecklistItem(item.id)}
                                disabled={isSaving}
                                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/40 text-white rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-colors shadow-sm disabled:cursor-not-allowed"
                              >
                                {isSaving ? (
                                  <>
                                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    <span>Saving...</span>
                                  </>
                                ) : (
                                  <>
                                    <Save className="h-3.5 w-3.5" />
                                    <span>Save Item</span>
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Additional Information Requests Overview */}
                {data.information_requests.length > 0 && (
                  <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                    <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                      <MessageSquare className="h-4 w-4 text-blue-400" />
                      <h2 className="text-xs font-bold uppercase tracking-wider">
                        Information Requests Record ({data.information_requests.length})
                      </h2>
                    </div>

                    <div className="space-y-3">
                      {data.information_requests.map((req) => (
                        <div
                          key={req.id}
                          className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white">{req.title}</span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                                req.status === "RESOLVED" || req.status === "RESPONDED"
                                  ? "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                                  : "bg-blue-950 text-blue-300 border-blue-500/40"
                              }`}
                            >
                              {req.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">{req.description}</p>
                          {req.response_notes && (
                            <div className="p-2.5 rounded bg-emerald-950/20 border border-emerald-500/30 text-xs text-slate-200">
                              <span className="font-bold text-emerald-400 text-[10px] uppercase block font-mono">
                                Applicant Response:
                              </span>
                              {req.response_notes}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Officer Notes Form, Review History, and Audit Trail */}
              <div className="space-y-6">
                
                {/* Officer Compliance Review Notes */}
                <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <h2 className="text-xs font-bold uppercase tracking-wider">
                      Compliance Officer Notes
                    </h2>
                  </div>

                  {noteError && (
                    <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs">
                      {noteError}
                    </div>
                  )}

                  <form onSubmit={handleAddNote} className="space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">
                        Add Review Note (Internal Only):
                      </label>
                      <textarea
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        placeholder="Record compliance observations, regulatory concerns, or underwriting notes..."
                        rows={3}
                        className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-400"
                        required
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={isSubmittingNote || !newNote.trim()}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/40 text-white rounded-lg text-xs font-bold inline-flex items-center gap-1.5 transition-colors disabled:cursor-not-allowed shadow-sm"
                      >
                        {isSubmittingNote ? (
                          <>
                            <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <span>Recording...</span>
                          </>
                        ) : (
                          <>
                            <Send className="h-3.5 w-3.5" />
                            <span>Record Compliance Note</span>
                          </>
                        )}
                      </button>
                    </div>
                  </form>

                  {/* Notes History */}
                  <div className="pt-3 border-t border-slate-800 space-y-3">
                    <h3 className="text-[11px] font-mono uppercase text-slate-400 font-bold">
                      Recorded Observations ({data.review_notes.length})
                    </h3>

                    {data.review_notes.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">
                        No compliance notes recorded yet.
                      </p>
                    ) : (
                      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                        {data.review_notes.map((rn) => (
                          <div
                            key={rn.id}
                            className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5"
                          >
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-bold text-emerald-400">
                                {rn.author_name}
                              </span>
                              <span className="font-mono text-slate-500">
                                {rn.created_at
                                  ? new Date(rn.created_at).toLocaleString()
                                  : ""}
                              </span>
                            </div>
                            <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                              {rn.note}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Audit Trail Events */}
                <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                    <Clock className="h-4 w-4 text-emerald-400" />
                    <h2 className="text-xs font-bold uppercase tracking-wider">
                      Audit Trail & Governance Log
                    </h2>
                  </div>

                  {data.audit_events.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">
                      No audit events recorded for this application.
                    </p>
                  ) : (
                    <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1 border-l-2 border-slate-800 ml-2 pl-3">
                      {data.audit_events.map((ev) => (
                        <div key={ev.id} className="relative pb-2">
                          <div className="absolute -left-[19px] top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-[#0F172A]"></div>
                          <p className="text-xs font-bold text-slate-200">{ev.title}</p>
                          <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                            {ev.description}
                          </p>
                          <span className="text-[10px] text-slate-500 font-mono block mt-1">
                            {ev.created_at
                              ? new Date(ev.created_at).toLocaleString()
                              : "Date recorded"}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

            </div>
          </div>
        )}
      </div>
    </EmployeeLayout>
  );
}
