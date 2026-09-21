"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  ArrowLeft, 
  ShieldAlert, 
  Lock, 
  CheckCircle2, 
  FileText, 
  User, 
  Building2, 
  Calendar, 
  CreditCard, 
  Clock, 
  FolderCheck, 
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Info,
  Layers,
  Check,
  XCircle,
  HelpCircle,
  Send,
  MessageSquare,
  FileCheck,
  FileX
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

interface ApplicationDetailData {
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
  information_requests: InformationRequestItem[];
  timeline: {
    event: string;
    title: string;
    description: string;
    timestamp: string | null;
  }[];
  compliance: {
    status: string;
    module: string;
    compliance_score: number | null;
    flags: string[];
    notes: string;
  };
  decision: {
    status: string;
    module: string;
    can_decide: boolean;
    notes: string;
  };
}

export default function EmployeeApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { t, tStatus, tLoanType } = useLanguage();

  const id = params?.id as string;

  const [data, setData] = useState<ApplicationDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isStartingReview, setIsStartingReview] = useState(false);
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Document Review State
  const [reviewingDocId, setReviewingDocId] = useState<string | null>(null);
  const [docReviewModalOpen, setDocReviewModalOpen] = useState(false);
  const [docReviewTarget, setDocReviewTarget] = useState<DocumentItem | null>(null);
  const [docReviewAction, setDocReviewAction] = useState<"ACCEPTED" | "REQUIRES_REUPLOAD">("REQUIRES_REUPLOAD");
  const [docReviewReason, setDocReviewReason] = useState("");
  const [docReviewError, setDocReviewError] = useState<string | null>(null);

  // Information Request State
  const [infoRequestModalOpen, setInfoRequestModalOpen] = useState(false);
  const [infoRequestTitle, setInfoRequestTitle] = useState("");
  const [infoRequestDesc, setInfoRequestDesc] = useState("");
  const [infoRequestDocType, setInfoRequestDocType] = useState("");
  const [isSubmittingInfoReq, setIsSubmittingInfoReq] = useState(false);
  const [infoReqError, setInfoReqError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setConflictError(null);
      setGeneralError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}`, {
        credentials: "include"
      });

      if (res.status === 403) {
        const errData = await res.json().catch(() => ({}));
        if (errData.detail && errData.detail.toLowerCase().includes("conflict of interest")) {
          setConflictError(errData.detail);
        } else {
          setGeneralError(errData.detail || "Forbidden: You do not have permission to view this application.");
        }
        return;
      }

      if (res.status === 404) {
        setGeneralError("Application not found in the institutional operations queue.");
        return;
      }

      if (res.status === 400) {
        const errData = await res.json().catch(() => ({}));
        setGeneralError(errData.detail || "Cannot inspect this application.");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to load application details (HTTP ${res.status})`);
      }

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setGeneralError(err.message || "Failed to load application dossier.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleStartReview = async () => {
    if (!id) return;
    try {
      setIsStartingReview(true);
      setTransitionError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}/transition-review`, {
        method: "POST",
        credentials: "include"
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to start review (HTTP ${res.status})`);
      }
      const updated = await res.json();
      setData(updated);
      setSuccessMessage("Underwriting review started successfully.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setTransitionError(err.message || "Failed to initiate underwriting review.");
    } finally {
      setIsStartingReview(false);
    }
  };

  const handleOpenDocReviewModal = (doc: DocumentItem, action: "ACCEPTED" | "REQUIRES_REUPLOAD") => {
    setDocReviewTarget(doc);
    setDocReviewAction(action);
    setDocReviewReason("");
    setDocReviewError(null);

    // If accepting, execute immediately or allow confirmation
    if (action === "ACCEPTED") {
      submitDocReview(doc.id, "ACCEPTED", "");
    } else {
      setDocReviewModalOpen(true);
    }
  };

  const submitDocReview = async (docId: string, status: string, reason: string) => {
    try {
      setReviewingDocId(docId);
      setDocReviewError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/documents/${docId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          status: status,
          reason: reason.trim() || undefined
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to update document review (HTTP ${res.status})`);
      }

      setDocReviewModalOpen(false);
      setDocReviewTarget(null);
      setDocReviewReason("");
      setSuccessMessage(`Document ${status === "ACCEPTED" ? "accepted" : "marked for re-upload"}.`);
      setTimeout(() => setSuccessMessage(null), 4000);
      await fetchDetail();
    } catch (err: any) {
      setDocReviewError(err.message || "Failed to review document.");
    } finally {
      setReviewingDocId(null);
    }
  };

  const handleCreateInfoRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !infoRequestTitle.trim() || !infoRequestDesc.trim()) {
      setInfoReqError("Title and description are required.");
      return;
    }

    try {
      setIsSubmittingInfoReq(true);
      setInfoReqError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/applications/${id}/information-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title: infoRequestTitle.trim(),
          description: infoRequestDesc.trim(),
          requested_document_type: infoRequestDocType.trim() || undefined
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to create information request (HTTP ${res.status})`);
      }

      setInfoRequestModalOpen(false);
      setInfoRequestTitle("");
      setInfoRequestDesc("");
      setInfoRequestDocType("");
      setSuccessMessage("Information request sent to applicant. Application status updated to ADDITIONAL_INFO_REQUIRED.");
      setTimeout(() => setSuccessMessage(null), 5000);
      await fetchDetail();
    } catch (err: any) {
      setInfoReqError(err.message || "Failed to submit information request.");
    } finally {
      setIsSubmittingInfoReq(false);
    }
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

  const getDocBadge = (status: string) => {
    switch (status) {
      case "ACCEPTED":
      case "VERIFIED":
        return "bg-emerald-950/70 text-emerald-300 border-emerald-500/40";
      case "REQUIRES_REUPLOAD":
        return "bg-amber-950/70 text-amber-300 border-amber-500/40";
      case "REJECTED":
        return "bg-rose-950/70 text-rose-300 border-rose-500/40";
      case "UPLOADED":
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-3">
          <Link
            href="/employee/applications"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold border border-slate-700 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Application Queue</span>
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-xs font-mono text-slate-400 truncate max-w-[200px]">
            Case #{id ? id.slice(0, 8) : ""}
          </span>
        </div>

        {/* Success Banner */}
        {successMessage && (
          <div className="p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/50 text-emerald-200 text-xs flex items-center gap-2 shadow-sm animate-in fade-in duration-200">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="font-medium">{successMessage}</span>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="p-16 text-center text-slate-400">
            <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-xs uppercase tracking-wider font-mono">Loading Underwriting Dossier...</p>
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

        {/* Loaded Application Dossier */}
        {data && !loading && (
          <div className="space-y-6">
            
            {/* Header Banner */}
            <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h1 className="text-lg font-bold text-white tracking-tight">
                      Application Dossier: {data.applicant.full_name}
                    </h1>
                    <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${getStatusBadge(data.application.status)}`}>
                      {tStatus(data.application.status)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    CASE ID: {data.application.id} • SUBMITTED: {data.application.created_at ? new Date(data.application.created_at).toLocaleString() : "N/A"}
                    {data.application.updated_at && (
                      <span> • LAST UPDATED: {new Date(data.application.updated_at).toLocaleString()}</span>
                    )}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <span className="px-3 py-1.5 rounded-lg bg-slate-800 text-amber-300 border border-slate-700 font-mono text-xs font-bold">
                    FACILITY: {formatINR(data.application.requested_amount)}
                  </span>

                  <Link
                    id="compliance-review-nav-btn"
                    href={`/employee/applications/${data.application.id}/compliance`}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Compliance Review</span>
                  </Link>

                  {data.application.status === "SUBMITTED" && (
                    <button
                      id="start-review-btn"
                      onClick={handleStartReview}
                      disabled={isStartingReview}
                      className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-600/50 text-slate-950 rounded-lg text-xs font-bold tracking-wider uppercase transition-all flex items-center gap-1.5 shadow-md shadow-amber-500/10 cursor-pointer disabled:cursor-not-allowed"
                    >
                      {isStartingReview ? (
                        <>
                          <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></div>
                          <span>Initiating Review...</span>
                        </>
                      ) : (
                        <>
                          <Check className="h-3.5 w-3.5 stroke-[3]" />
                          <span>Start Review</span>
                        </>
                      )}
                    </button>
                  )}

                  {(data.application.status === "UNDER_REVIEW" || data.application.status === "ADDITIONAL_INFO_REQUIRED") && (
                    <>
                      <button
                        id="request-info-btn"
                        onClick={() => setInfoRequestModalOpen(true)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                      >
                        <MessageSquare className="h-3.5 w-3.5" />
                        <span>Request Additional Information</span>
                      </button>

                      <span className="px-3 py-1.5 rounded-lg bg-blue-950/80 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5 text-blue-400" />
                        <span>{data.application.status === "ADDITIONAL_INFO_REQUIRED" ? "Awaiting Applicant Info" : "Review in Progress"}</span>
                      </span>
                    </>
                  )}
                </div>
              </div>

              {transitionError && (
                <div className="mt-4 p-3 rounded-lg bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0" />
                  <span>{transitionError}</span>
                </div>
              )}
            </div>

            {/* Grid: Applicant Profile & Loan Facility */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Applicant Profile Card */}
              <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                  <User className="h-4 w-4 text-amber-400" />
                  <h2 className="text-xs font-bold uppercase tracking-wider">Applicant KYC & Contact Information</h2>
                </div>

                <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Full Name</span>
                    <span className="font-semibold text-slate-200">{data.applicant.full_name}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Primary Email</span>
                    <span className="font-mono text-slate-300 truncate block">{data.applicant.email}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Contact Mobile</span>
                    <span className="font-mono text-slate-300">{data.applicant.phone_number || "Not provided"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Date of Birth</span>
                    <span className="text-slate-300">{data.applicant.date_of_birth || "Not provided"}</span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Residential Address</span>
                    <span className="text-slate-300">
                      {[data.applicant.address, data.applicant.city, data.applicant.state, data.applicant.pincode].filter(Boolean).join(", ") || "No address on file"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Loan Facility Parameters */}
              <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                  <CreditCard className="h-4 w-4 text-amber-400" />
                  <h2 className="text-xs font-bold uppercase tracking-wider">Requested Credit Facility Details</h2>
                </div>

                <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Loan Product</span>
                    <span className="font-semibold text-amber-400">{tLoanType(data.application.loan_type)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Requested Amount</span>
                    <span className="font-bold text-white">{formatINR(data.application.requested_amount)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Tenure Duration</span>
                    <span className="text-slate-300">{data.application.tenure} {t("common.months")}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Declared Purpose</span>
                    <span className="text-slate-300 truncate block">{data.application.purpose}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Employment Status</span>
                    <span className="text-slate-300">{data.application.employment_info || "Standard salaried"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Income Declaration</span>
                    <span className="text-slate-300">{data.application.income_info || "Verified by bank"}</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Document Evidence Repository with Underwriting Review Actions */}
            <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 bg-[#070D1E] border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderCheck className="h-4 w-4 text-amber-400" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Applicant Submitted Documents ({data.documents.length})
                  </h2>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  DOCUMENT REVIEW & RE-UPLOAD GOVERNANCE
                </span>
              </div>

              {data.documents.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No supporting documents currently uploaded by the applicant for this loan case.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#0A1224] text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-2.5">Document Details</th>
                        <th className="px-4 py-2.5">Status</th>
                        <th className="px-4 py-2.5">Upload Date</th>
                        <th className="px-4 py-2.5">Review Notes</th>
                        <th className="px-4 py-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {data.documents.map((doc) => {
                        const canReview = ["SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFO_REQUIRED"].includes(data.application.status);
                        const isDocReviewing = reviewingDocId === doc.id;

                        return (
                          <tr key={doc.id} className="hover:bg-slate-800/40">
                            <td className="px-4 py-3 font-medium text-slate-200">
                              <div>{doc.document_type.replace(/_/g, " ")}</div>
                              <span className="text-[10px] font-mono text-slate-500">ID: {doc.id.slice(0, 8)}</span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getDocBadge(doc.status)}`}>
                                {doc.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                              {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "N/A"}
                            </td>
                            <td className="px-4 py-3 text-slate-300 text-[11px] max-w-xs">
                              {doc.review_notes ? (
                                <div className="p-1.5 rounded bg-slate-900/80 border border-slate-800 text-amber-200/90 text-[11px]">
                                  {doc.review_notes}
                                </div>
                              ) : (
                                <span className="text-slate-500 italic">No notes recorded</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="inline-flex items-center justify-end gap-2">
                                <a
                                  href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${doc.id}/content`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-slate-300 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold border border-slate-700 transition-colors"
                                  title="Open original document content"
                                >
                                  <span>View</span>
                                  <ExternalLink className="h-3 w-3" />
                                </a>

                                {canReview && (
                                  <>
                                    <button
                                      onClick={() => handleOpenDocReviewModal(doc, "ACCEPTED")}
                                      disabled={isDocReviewing || doc.status === "ACCEPTED"}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/40 rounded text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                      title="Accept document"
                                    >
                                      <FileCheck className="h-3 w-3" />
                                      <span>Accept</span>
                                    </button>

                                    <button
                                      onClick={() => handleOpenDocReviewModal(doc, "REQUIRES_REUPLOAD")}
                                      disabled={isDocReviewing}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/40 rounded text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                      title="Require applicant to re-upload"
                                    >
                                      <FileX className="h-3 w-3" />
                                      <span>Require Re-upload</span>
                                    </button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Information Requests Workspace */}
            <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="px-5 py-3.5 bg-[#070D1E] border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-amber-400" />
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Additional Information Requests ({data.information_requests ? data.information_requests.length : 0})
                  </h2>
                </div>
                
                {(data.application.status === "UNDER_REVIEW" || data.application.status === "ADDITIONAL_INFO_REQUIRED") && (
                  <button
                    onClick={() => setInfoRequestModalOpen(true)}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-amber-400 hover:text-amber-300"
                  >
                    <span>+ New Query</span>
                  </button>
                )}
              </div>

              {!data.information_requests || data.information_requests.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No additional information requests have been created for this applicant.
                </div>
              ) : (
                <div className="divide-y divide-slate-800/80">
                  {data.information_requests.map((req) => {
                    const isResponded = req.status === "RESPONDED";

                    return (
                      <div key={req.id} className="p-4 hover:bg-slate-800/30 transition-colors space-y-2">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-xs font-bold text-slate-200">{req.title}</h3>
                              {isResponded ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 flex items-center gap-1">
                                  <CheckCircle2 className="h-3 w-3" />
                                  <span>NEW DOCUMENT RECEIVED</span>
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-500/50">
                                  OPEN (AWAITING CUSTOMER)
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-1">{req.description}</p>
                            {req.requested_document_type && (
                              <p className="text-[10px] font-mono text-slate-500 mt-0.5">
                                REQUESTED DOCUMENT TYPE: {req.requested_document_type}
                              </p>
                            )}
                          </div>

                          <div className="text-right shrink-0">
                            <span className="text-[10px] text-slate-500 font-mono block">
                              Requested: {req.created_at ? new Date(req.created_at).toLocaleDateString() : "N/A"}
                            </span>
                            {req.responded_at && (
                              <span className="text-[10px] text-emerald-400 font-mono block mt-0.5">
                                Responded: {new Date(req.responded_at).toLocaleString()}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Customer Response Box */}
                        {isResponded && (
                          <div className="mt-2 p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between gap-4">
                            <div className="space-y-0.5">
                              <span className="text-[10px] uppercase font-mono text-emerald-400 font-bold block">
                                Customer Response Notes:
                              </span>
                              <p className="text-xs text-slate-200">
                                {req.response_notes || "Document submitted without supplementary notes."}
                              </p>
                            </div>

                            {req.response_document_id && (
                              <a
                                href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${req.response_document_id}/content`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold inline-flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
                              >
                                <ExternalLink className="h-3 w-3" />
                                <span>View Uploaded File</span>
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Audit Timeline */}
            <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
                <Clock className="h-4 w-4 text-amber-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider">Operational Audit Trail</h2>
              </div>

              <div className="space-y-4 relative pl-4 border-l-2 border-slate-800 ml-2">
                {data.timeline.map((item, idx) => (
                  <div key={idx} className="relative">
                    <div className="absolute -left-[21px] top-0.5 w-3 h-3 rounded-full bg-amber-500 border-2 border-[#0F172A]"></div>
                    <p className="text-xs font-bold text-slate-200">{item.title}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">{item.description}</p>
                    <span className="text-[10px] text-slate-500 font-mono block mt-1">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Date recorded"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Clean Integration Boundaries: Compliance Assessment & Credit Decisioning */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Compliance Boundary */}
              <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-slate-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Compliance Evaluation
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    {data.compliance.module}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {data.compliance.notes}
                </p>
                <div className="p-2.5 rounded bg-[#0A1224] border border-slate-800 text-[11px] text-slate-500 font-mono">
                  Integration status: {data.compliance.status}
                </div>
                <div>
                  <Link
                    href={`/employee/applications/${data.application.id}/compliance`}
                    className="w-full py-2 px-3 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
                  >
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <span>Open Compliance Workspace</span>
                  </Link>
                </div>
              </div>

              {/* Credit Decisioning Boundary */}
              <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-slate-400" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                      Underwriting Decision
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    {data.decision.module}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {data.decision.notes}
                </p>
                <div className="p-2.5 rounded bg-[#0A1224] border border-slate-800 text-[11px] text-slate-500 font-mono">
                  Autonomous deciders: DISABLED • Human Underwriter Assigned
                </div>
              </div>

            </div>

          </div>
        )}

      </div>

      {/* Modal: Document Review Reason (Require Re-upload) */}
      {docReviewModalOpen && docReviewTarget && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-[#0F172A] border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-amber-400">
                <FileX className="h-5 w-5" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Require Document Re-upload</h3>
              </div>
              <button
                onClick={() => setDocReviewModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div>
              <p className="text-xs text-slate-300">
                Document: <span className="font-semibold text-white">{docReviewTarget.document_type.replace(/_/g, " ")}</span>
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                Please provide the exact reason why this document cannot be accepted. This reason will be displayed to the applicant.
              </p>
            </div>

            {docReviewError && (
              <div className="p-3 rounded bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs">
                {docReviewError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Deficiency Reason <span className="text-rose-400">*</span>
              </label>
              <textarea
                value={docReviewReason}
                onChange={(e) => setDocReviewReason(e.target.value)}
                placeholder="e.g. Document image is blurry or pages 2-3 are missing authorization stamp..."
                rows={3}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                required
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setDocReviewModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => submitDocReview(docReviewTarget.id, "REQUIRES_REUPLOAD", docReviewReason)}
                disabled={reviewingDocId !== null || !docReviewReason.trim()}
                className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-600/40 text-slate-950 rounded-lg text-xs font-bold transition-colors disabled:cursor-not-allowed"
              >
                {reviewingDocId ? "Submitting..." : "Submit Re-upload Request"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Request Additional Information */}
      {infoRequestModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-[#0F172A] border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-blue-400">
                <MessageSquare className="h-5 w-5" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Request Additional Information</h3>
              </div>
              <button
                onClick={() => setInfoRequestModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              This request will be sent directly to the applicant and set application status to <span className="text-amber-400 font-mono font-bold">ADDITIONAL_INFO_REQUIRED</span>.
            </p>

            {infoReqError && (
              <div className="p-3 rounded bg-rose-950/60 border border-rose-600/40 text-rose-200 text-xs">
                {infoReqError}
              </div>
            )}

            <form onSubmit={handleCreateInfoRequest} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Request Title <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={infoRequestTitle}
                  onChange={(e) => setInfoRequestTitle(e.target.value)}
                  placeholder="e.g. Audited Balance Sheet FY2025"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-400"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Detailed Instructions <span className="text-rose-400">*</span>
                </label>
                <textarea
                  value={infoRequestDesc}
                  onChange={(e) => setInfoRequestDesc(e.target.value)}
                  placeholder="e.g. Please provide the complete audited financials including notes to accounts and statutory auditor's report..."
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-400"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Expected Document Type (Optional)
                </label>
                <input
                  type="text"
                  value={infoRequestDocType}
                  onChange={(e) => setInfoRequestDocType(e.target.value)}
                  placeholder="e.g. AUDITED_BALANCE_SHEET, BANK_STATEMENT"
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-400"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setInfoRequestModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingInfoReq || !infoRequestTitle.trim() || !infoRequestDesc.trim()}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/40 text-white rounded-lg text-xs font-bold transition-colors disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  {isSubmittingInfoReq ? "Transmitting..." : "Send Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </EmployeeLayout>
  );
}
