"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { 
  ArrowLeft, 
  Send, 
  CheckCircle, 
  FileText, 
  AlertCircle, 
  Edit3, 
  Upload, 
  X, 
  Save, 
  Trash2,
  ShieldCheck,
  HelpCircle,
  FileUp,
  ExternalLink,
  CheckCircle2,
  Clock,
  XCircle
} from "lucide-react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  formatFileSize, 
  getMimeBadge, 
  formatPageCount, 
  sanitizeErrorMessage 
} from "@/lib/documentUtils";

interface Application {
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
  created_at: string;
  updated_at: string | null;
}

interface ApplicationDocument {
  id: string;
  application_id: string | null;
  document_type: string;
  file_url: string;
  status: string;
  reviewed_at?: string | null;
  review_notes?: string | null;
  created_at: string;
  original_filename?: string | null;
  file_size_bytes?: number | null;
  mime_type?: string | null;
  file_hash?: string | null;
  page_count?: number | null;
}

interface InformationRequestItem {
  id: string;
  application_id: string;
  title: string;
  description: string;
  requested_document_type: string | null;
  status: string;
  response_document_id: string | null;
  response_notes: string | null;
  created_at: string | null;
  responded_at: string | null;
}

export default function ApplicationDetailsPage() {
  const { id } = useParams();
  const { t, tStatus, tLoanType, tDocType } = useLanguage();
  
  const [application, setApplication] = useState<Application | null>(null);
  const [documents, setDocuments] = useState<ApplicationDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  
  // Edit mode state (for DRAFT only)
  const [isEditing, setIsEditing] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    loan_type: "",
    requested_amount: "",
    tenure: "",
    purpose: "",
    employment_info: "",
    income_info: "",
    existing_liabilities: ""
  });

  // Document upload state
  const [showDocUpload, setShowDocUpload] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState(false);
  const [docType, setDocType] = useState("INCOME_PROOF");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docUploadError, setDocUploadError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Document Replacement state (REQUIRES_REUPLOAD)
  const [replacingDoc, setReplacingDoc] = useState<ApplicationDocument | null>(null);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const [isUploadingReplacement, setIsUploadingReplacement] = useState(false);
  const [replacementError, setReplacementError] = useState<string | null>(null);

  // Supplementary Information Request response state
  const [informationRequests, setInformationRequests] = useState<InformationRequestItem[]>([]);
  const [respondingReq, setRespondingReq] = useState<InformationRequestItem | null>(null);
  const [responseFile, setResponseFile] = useState<File | null>(null);
  const [responseNotes, setResponseNotes] = useState("");
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);
  const [responseError, setResponseError] = useState<string | null>(null);

  const inFlightRef = useRef(false);
  const isEditingRef = useRef(isEditing);
  useEffect(() => {
    isEditingRef.current = isEditing;
  }, [isEditing]);

  const fetchApplication = useCallback(async (isBackground = false) => {
    if (!id || inFlightRef.current) return;
    inFlightRef.current = true;

    if (!isBackground) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/applications/${id}`, { 
        credentials: 'include' 
      });
      
      if (res.ok) {
        const json = await res.json();
        setApplication(json.application);
        setDocuments(json.documents || []);
        setInformationRequests(json.information_requests || []);
        
        // Preserve user's in-progress form entries if they are currently editing
        if (!isEditingRef.current && json.application) {
          setEditForm({
            loan_type: json.application.loan_type || "",
            requested_amount: String(json.application.requested_amount || ""),
            tenure: String(json.application.tenure || ""),
            purpose: json.application.purpose || "",
            employment_info: json.application.employment_info || "",
            income_info: json.application.income_info || "",
            existing_liabilities: json.application.existing_liabilities || ""
          });
        }
        setError(null);
      } else if (res.status === 401) {
        setError(t("applications.sessionExpired"));
      } else if (res.status === 404 || res.status === 403) {
        setError(t("applicationDetails.accessRestricted"));
      } else if (res.status >= 500) {
        setError(t("applications.serverError"));
      } else {
        setError(t("applications.failedToLoad"));
      }
    } catch {
      if (!isBackground) {
        setError(t("applications.networkError"));
      }
    } finally {
      inFlightRef.current = false;
      if (!isBackground) {
        setIsLoading(false);
      }
    }
  }, [id, t]);

  useEffect(() => {
    // Initial fetch
    fetchApplication(false);

    // Active polling every 4 seconds (3-5s requirement)
    const interval = setInterval(() => {
      // Respect visibility: pause polling when tab is hidden
      if (typeof document !== 'undefined' && document.hidden) {
        return;
      }
      fetchApplication(true);
    }, 4000);

    // Immediately refetch whenever tab becomes visible
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchApplication(true);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchApplication]);

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!application || application.status !== 'DRAFT') return;
    
    setIsSavingEdit(true);
    setEditError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const payload = {
        loan_type: editForm.loan_type,
        requested_amount: parseInt(editForm.requested_amount, 10),
        tenure: parseInt(editForm.tenure, 10),
        purpose: editForm.purpose,
        employment_info: editForm.employment_info || null,
        income_info: editForm.income_info || null,
        existing_liabilities: editForm.existing_liabilities || null
      };

      const res = await fetch(`${apiUrl}/api/applications/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (res.ok) {
        setIsEditing(false);
        setActionSuccess(t("applicationDetails.appInfoTitle"));
        setTimeout(() => setActionSuccess(null), 4000);
        await fetchApplication();
      } else {
        const errData = await res.json().catch(() => ({}));
        setEditError(errData.detail || t("newApplication.createFailed"));
      }
    } catch {
      setEditError(t("newApplication.networkError"));
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleSubmitApplication = async () => {
    if (!application || application.status !== 'DRAFT') return;
    
    setIsSubmitting(true);
    setShowSubmitConfirm(false);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/applications/${id}/submit`, {
        method: 'POST',
        credentials: 'include'
      });

      if (res.ok) {
        setActionSuccess(t("applicationDetails.submittedForReview"));
        setTimeout(() => setActionSuccess(null), 5000);
        await fetchApplication();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || t("applicationDetails.submitApplication"));
      }
    } catch {
      alert(t("newApplication.networkError"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !application) return;

    setUploadingDoc(true);
    setDocUploadError(null);
    try {
      const formData = new FormData();
      formData.append("document_type", docType);
      formData.append("application_id", application.id);
      formData.append("file", selectedFile);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/documents/`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (res.ok) {
        setSelectedFile(null);
        setShowDocUpload(false);
        setActionSuccess(t("applicationDetails.attachedDocsTitle"));
        setTimeout(() => setActionSuccess(null), 4000);
        await fetchApplication();
      } else {
        const errData = await res.json().catch(() => ({}));
        setDocUploadError(sanitizeErrorMessage(errData.detail || errData.message || t("documents.uploadError")));
      }
    } catch {
      setDocUploadError(t("newApplication.networkError"));
    } finally {
      setUploadingDoc(false);
    }
  };

  const handleReplaceDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replacementFile || !replacingDoc || !application) return;

    setIsUploadingReplacement(true);
    setReplacementError(null);
    try {
      const formData = new FormData();
      formData.append("document_type", replacingDoc.document_type);
      formData.append("application_id", application.id);
      formData.append("replaces_document_id", replacingDoc.id);
      formData.append("file", replacementFile);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/documents/`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (res.ok) {
        setReplacementFile(null);
        setReplacingDoc(null);
        setActionSuccess("Replacement document uploaded successfully.");
        setTimeout(() => setActionSuccess(null), 4000);
        await fetchApplication();
      } else {
        const errData = await res.json().catch(() => ({}));
        setReplacementError(sanitizeErrorMessage(errData.detail || errData.message || "Failed to upload replacement document."));
      }
    } catch {
      setReplacementError("Network error while uploading replacement document.");
    } finally {
      setIsUploadingReplacement(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm(t("common.deleteConfirm") || "Are you sure?")) return;
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/documents/${docId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (res.ok) {
        setActionSuccess(t("common.deleteSuccess"));
        setTimeout(() => setActionSuccess(null), 3000);
        await fetchApplication();
      } else {
        alert(t("common.deleteFailed"));
      }
    } catch {
      alert(t("newApplication.networkError"));
    }
  };

  const handleRespondToRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!application || !respondingReq || !responseFile) {
      setResponseError("Please select a document file to upload.");
      return;
    }

    setIsSubmittingResponse(true);
    setResponseError(null);
    try {
      const formData = new FormData();
      formData.append("file", responseFile);
      if (responseNotes.trim()) {
        formData.append("notes", responseNotes.trim());
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/customer/applications/${application.id}/information-requests/${respondingReq.id}/respond`, {
        method: "POST",
        body: formData,
        credentials: "include"
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(sanitizeErrorMessage(errData.detail || errData.message || "Failed to submit response."));
      }

      setRespondingReq(null);
      setResponseFile(null);
      setResponseNotes("");
      setActionSuccess("Requested document submitted successfully. Application returned to underwriter review.");
      setTimeout(() => setActionSuccess(null), 5000);
      await fetchApplication();
    } catch (err: any) {
      setResponseError(sanitizeErrorMessage(err.message || "Failed to submit response."));
    } finally {
      setIsSubmittingResponse(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DRAFT':
        return <span className="px-3 py-1 bg-slate-100 text-slate-700 border border-slate-300 rounded-full text-xs font-semibold uppercase tracking-wider">{tStatus('DRAFT')}</span>;
      case 'SUBMITTED':
        return <span className="px-3 py-1 bg-blue-50 text-blue-800 border border-blue-300 rounded-full text-xs font-semibold uppercase tracking-wider">{tStatus('SUBMITTED')}</span>;
      case 'UNDER_REVIEW':
        return <span className="px-3 py-1 bg-blue-50 text-blue-800 border border-blue-300 rounded-full text-xs font-semibold uppercase tracking-wider">{tStatus('UNDER_REVIEW')}</span>;
      case 'ADDITIONAL_INFO_REQUIRED':
        return <span className="px-3 py-1 bg-amber-50 text-amber-800 border border-amber-300 rounded-full text-xs font-semibold uppercase tracking-wider">{tStatus('ADDITIONAL_INFO_REQUIRED')}</span>;
      case 'APPROVED':
        return <span className="px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-300 rounded-full text-xs font-bold uppercase tracking-wider">{tStatus('APPROVED')}</span>;
      case 'DECLINED':
        return <span className="px-3 py-1 bg-rose-50 text-rose-800 border border-rose-300 rounded-full text-xs font-bold uppercase tracking-wider">{tStatus('DECLINED')}</span>;
      default:
        return <span className="px-3 py-1 bg-slate-100 text-slate-800 border border-slate-300 rounded-full text-xs font-semibold">{status}</span>;
    }
  };

  const getDocStatusBadge = (status: string) => {
    switch (status) {
      case 'ACCEPTED':
      case 'VERIFIED':
        return <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs font-medium">{t("status.verified")}</span>;
      case 'REJECTED':
        return <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded text-xs font-medium">{t("status.rejected")}</span>;
      case 'REQUIRES_REUPLOAD':
        return <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-xs font-medium">{t("status.reuploadRequired")}</span>;
      default:
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-medium">{t("status.uploaded")}</span>;
    }
  };

  if (isLoading) {
    return (
      <AuthenticatedLayout>
        <div className="flex h-64 items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-900"></div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error || !application) {
    return (
      <AuthenticatedLayout>
        <div className="max-w-2xl mx-auto mt-12 bg-white border border-slate-200 rounded-xl p-8 text-center shadow-sm">
          <AlertCircle className="h-12 w-12 text-rose-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-900">{t("applicationDetails.accessRestricted")}</h2>
          <p className="text-slate-600 mt-2 text-sm">{error || t("applicationDetails.accessRestricted")}</p>
          <div className="mt-6">
            <Link 
              href="/dashboard/applications" 
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-lg text-sm font-semibold hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              {t("applicationDetails.backToApplications")}
            </Link>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const isDraft = application.status === 'DRAFT';
  const isSubmitted = application.status !== 'DRAFT';
  const isUnderReviewOrBeyond = ['UNDER_REVIEW', 'ADDITIONAL_INFO_REQUIRED', 'APPROVED', 'DECLINED'].includes(application.status);
  const isDecided = ['APPROVED', 'DECLINED'].includes(application.status);

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 text-[#0F172A] max-w-5xl mx-auto pb-12">
        
        {/* Navigation & Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-6">
          <div className="flex items-center gap-4">
            <Link 
              href="/dashboard/applications" 
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200 text-slate-600"
              title={t("applicationDetails.backToApplications")}
              aria-label={t("applicationDetails.backToApplications")}
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900">{tLoanType(application.loan_type)}</h1>
                {getStatusBadge(application.status)}
              </div>
              <p className="text-xs text-slate-500 mt-1 font-mono">{t("applicationDetails.reference")}: {application.id}</p>
            </div>
          </div>

          {/* Action Buttons for DRAFT */}
          {isDraft && (
            <div className="flex items-center gap-3">
              {!isEditing && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-50 transition-colors"
                >
                  <Edit3 className="h-4 w-4" />
                  {t("applicationDetails.editDetails")}
                </button>
              )}
              <button
                onClick={() => setShowSubmitConfirm(true)}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2 bg-emerald-600 text-white rounded-md text-sm font-semibold hover:bg-emerald-700 transition-colors disabled:opacity-50 shadow-sm"
              >
                <Send className="h-4 w-4" />
                {isSubmitting ? t("applicationDetails.submitting") : t("applicationDetails.submitApplication")}
              </button>
            </div>
          )}
        </div>

        {/* Global Notification Banner */}
        {actionSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3 text-emerald-800 text-sm">
            <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Approved State Banner */}
        {application.status === 'APPROVED' && (
          <div className="p-6 bg-emerald-50/90 border-2 border-emerald-500 rounded-xl shadow-sm space-y-4 animate-in fade-in duration-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-emerald-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 rounded-xl text-emerald-700 shrink-0 border border-emerald-300">
                  <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-emerald-950">
                      Application Approved: Facility Sanctioned
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase bg-emerald-200 text-emerald-900 border border-emerald-300">
                      {tStatus('APPROVED')}
                    </span>
                  </div>
                  <p className="text-xs text-emerald-800 mt-0.5">
                    Your loan application has been formally approved following underwriting evaluation.
                  </p>
                </div>
              </div>

              {application.updated_at && (
                <div className="text-left sm:text-right text-xs font-mono text-emerald-800">
                  <span className="text-[10px] uppercase block text-emerald-600 font-sans font-semibold">Decision Date</span>
                  {new Date(application.updated_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white/80 p-3.5 rounded-lg border border-emerald-200 text-xs">
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block">Sanctioned Amount</span>
                <span className="text-sm font-bold text-slate-900 font-mono">
                  ₹{Number(application.requested_amount).toLocaleString('en-IN')}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block">Facility Type</span>
                <span className="font-semibold text-slate-800">{tLoanType(application.loan_type)}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block">Tenure</span>
                <span className="font-semibold text-slate-800">{application.tenure} {t("newApplication.monthsSuffix")}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase font-semibold text-slate-500 block">Record Status</span>
                <span className="font-bold text-emerald-700">Official / Locked</span>
              </div>
            </div>

            <p className="text-xs text-emerald-900/90 leading-relaxed">
              Official confirmation of your approved facility is committed in bank records. An automated notice has been sent to your registered communication channels. Further disbursement procedures and sanction documents are administered through operations.
            </p>
          </div>
        )}

        {/* Declined State Banner */}
        {application.status === 'DECLINED' && (
          <div className="p-6 bg-rose-50/90 border-2 border-rose-300 rounded-xl shadow-sm space-y-4 animate-in fade-in duration-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-rose-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-rose-100 rounded-xl text-rose-700 shrink-0 border border-rose-300">
                  <XCircle className="h-6 w-6 text-rose-600" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-rose-950">
                      Application Declined: Evaluation Concluded
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase bg-rose-200 text-rose-900 border border-rose-300">
                      {tStatus('DECLINED')}
                    </span>
                  </div>
                  <p className="text-xs text-rose-800 mt-0.5">
                    We regret to inform you that your loan application could not be approved at this time.
                  </p>
                </div>
              </div>

              {application.updated_at && (
                <div className="text-left sm:text-right text-xs font-mono text-rose-800">
                  <span className="text-[10px] uppercase block text-rose-600 font-sans font-semibold">Decision Date</span>
                  {new Date(application.updated_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
              )}
            </div>

            <div className="p-3.5 bg-white/80 rounded-lg border border-rose-200 text-xs text-rose-950 space-y-1">
              <p className="font-semibold text-rose-900">Institutional Decision Explanation:</p>
              <p className="text-xs text-slate-700 leading-relaxed">
                Following thorough underwriting evaluation of credit parameters, debt-to-income benchmarks, and submitted documentation against institutional lending criteria, this application does not satisfy the requirements necessary for approval.
              </p>
            </div>

            <p className="text-xs text-slate-500 italic">
              This application dossier is concluded and locked in accordance with data preservation policies. No further documentation or changes can be accepted for this case reference.
            </p>
          </div>
        )}

        {/* Under Review Banner */}
        {application.status === 'UNDER_REVIEW' && (
          <div className="p-5 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-4 shadow-sm animate-in fade-in duration-200">
            <div className="p-2.5 bg-blue-100 rounded-lg text-blue-700 shrink-0 mt-0.5 border border-blue-200">
              <Clock className="h-6 w-6 text-blue-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-blue-950 text-base">
                  Application Under Review
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-200 text-blue-900">
                  {tStatus('UNDER_REVIEW')}
                </span>
              </div>
              <p className="text-xs text-blue-900/90 mt-1.5 leading-relaxed">
                Your loan application is currently under formal evaluation by our credit underwriting team. All documentation and eligibility criteria are being verified. You will be notified automatically if supplementary details are required or when a final decision is recorded.
              </p>
            </div>
          </div>
        )}

        {/* Action Required Banner for ADDITIONAL_INFO_REQUIRED */}
        {application.status === 'ADDITIONAL_INFO_REQUIRED' && (
          <div className="p-5 bg-amber-50 border-2 border-amber-400 rounded-xl flex items-start gap-4 shadow-sm animate-in fade-in duration-200">
            <div className="p-2.5 bg-amber-100 rounded-lg text-amber-800 shrink-0 mt-0.5">
              <AlertCircle className="h-6 w-6 text-amber-700" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-amber-950 text-base">
                  Action Required: Supplementary Documentation Requested
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-200/80 text-amber-900">
                  Underwriter Query
                </span>
              </div>
              <p className="text-xs text-amber-900/90 mt-1.5 leading-relaxed">
                The institutional credit underwriter reviewing your application has requested additional information or supporting documentation. Please inspect the queries below and upload the requested evidence to resume processing.
              </p>
            </div>
          </div>
        )}

        {/* Submit Confirmation Modal */}
        {showSubmitConfirm && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
              <div className="flex items-center gap-3 text-amber-600 mb-3">
                <AlertCircle className="h-6 w-6" />
                <h3 className="font-bold text-lg text-slate-900">{t("applicationDetails.confirmSubmission")}</h3>
              </div>
              <p className="text-sm text-slate-600">
                {t("applicationDetails.confirmNotice")}
              </p>
              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => setShowSubmitConfirm(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-md transition-colors"
                >
                  {t("applicationDetails.cancel")}
                </button>
                <button
                  onClick={handleSubmitApplication}
                  className="px-5 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-md hover:bg-emerald-700 transition-colors shadow-sm"
                >
                  {t("applicationDetails.confirmAndSubmit")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Columns (Application Details & Documents) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Application Information Card */}
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
                <h2 className="font-semibold text-base text-slate-900">{t("applicationDetails.appInfoTitle")}</h2>
                {isDraft && !isEditing && (
                  <button 
                    onClick={() => setIsEditing(true)}
                    className="text-xs font-semibold text-blue-600 hover:text-blue-700"
                  >
                    {t("applicationDetails.editDraft")}
                  </button>
                )}
              </div>

              {isEditing ? (
                /* Inline Edit Form for DRAFT */
                <form onSubmit={handleSaveEdit} className="p-6 space-y-4">
                  {editError && (
                    <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-md">
                      {editError}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.loanType")}</label>
                      <select
                        value={editForm.loan_type}
                        onChange={(e) => setEditForm({ ...editForm, loan_type: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                        required
                      >
                        <option value="Personal Loan">{tLoanType("Personal Loan")}</option>
                        <option value="Home Loan">{tLoanType("Home Loan")}</option>
                        <option value="Business Loan">{tLoanType("Business Loan")}</option>
                        <option value="Education Loan">{tLoanType("Education Loan")}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.requestedAmount")}</label>
                      <input
                        type="number"
                        value={editForm.requested_amount}
                        onChange={(e) => setEditForm({ ...editForm, requested_amount: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                        min="1000"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.tenure")}</label>
                      <input
                        type="number"
                        value={editForm.tenure}
                        onChange={(e) => setEditForm({ ...editForm, tenure: e.target.value })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                        min="1"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.monthlyIncome")}</label>
                      <input
                        type="text"
                        value={editForm.income_info}
                        onChange={(e) => setEditForm({ ...editForm, income_info: e.target.value })}
                        placeholder={t("newApplication.monthlyIncomePlaceholder")}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.purpose")}</label>
                    <textarea
                      value={editForm.purpose}
                      onChange={(e) => setEditForm({ ...editForm, purpose: e.target.value })}
                      rows={2}
                      className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.employmentInfo")}</label>
                      <input
                        type="text"
                        value={editForm.employment_info}
                        onChange={(e) => setEditForm({ ...editForm, employment_info: e.target.value })}
                        placeholder={t("newApplication.employmentPlaceholder")}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("newApplication.existingLiabilities")}</label>
                      <input
                        type="text"
                        value={editForm.existing_liabilities}
                        onChange={(e) => setEditForm({ ...editForm, existing_liabilities: e.target.value })}
                        placeholder={t("newApplication.liabilitiesPlaceholder")}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      disabled={isSavingEdit}
                      className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-50 transition-colors"
                    >
                      {t("applicationDetails.cancel")}
                    </button>
                    <button
                      type="submit"
                      disabled={isSavingEdit}
                      className="flex items-center gap-2 px-5 py-2 bg-slate-900 text-white rounded-md text-sm font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
                    >
                      <Save className="h-4 w-4" />
                      {isSavingEdit ? t("newApplication.saving") : t("newApplication.saveDraft")}
                    </button>
                  </div>
                </form>
              ) : (
                /* Read-only details display */
                <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-8">
                  <div>
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.requestedAmount")}</span>
                    <p className="text-2xl font-bold text-slate-900 mt-1">₹{Number(application.requested_amount).toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.repaymentTenure")}</span>
                    <p className="text-lg font-semibold text-slate-900 mt-1">{application.tenure} {t("newApplication.monthsSuffix")}</p>
                  </div>

                  <div className="sm:col-span-2 bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.purposeOfLoan")}</span>
                    <p className="text-sm text-slate-800 mt-1">{application.purpose}</p>
                  </div>

                  <div>
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.employmentInfo")}</span>
                    <p className="text-sm font-medium text-slate-800 mt-1">{application.employment_info || t("applicationDetails.notProvided")}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.monthlyIncome")}</span>
                    <p className="text-sm font-medium text-slate-800 mt-1">{application.income_info || t("applicationDetails.notProvided")}</p>
                  </div>

                  <div className="sm:col-span-2">
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{t("applicationDetails.existingLiabilities")}</span>
                    <p className="text-sm font-medium text-slate-800 mt-1">{application.existing_liabilities || t("applicationDetails.noneDeclared")}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Dedicated Workflow 1: DOCUMENT REPLACEMENT REQUIRED (Rule 1: Existing Deficient Documents) */}
            {!isDecided && documents.some(d => d.status === 'REQUIRES_REUPLOAD') && (
              <div className="bg-amber-50/90 border-2 border-amber-300 rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-amber-200 bg-amber-100/70 flex items-center justify-between">
                  <div className="flex items-center gap-2.5 text-amber-950">
                    <AlertCircle className="h-5 w-5 text-amber-700 shrink-0" />
                    <div>
                      <h2 className="font-bold text-sm uppercase tracking-wider text-amber-950">
                        DOCUMENT REPLACEMENT REQUIRED
                      </h2>
                      <p className="text-xs text-amber-900/80">
                        An existing submitted document requires replacement or correction based on underwriting review.
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded bg-amber-200 text-amber-900 border border-amber-300">
                    {documents.filter(d => d.status === 'REQUIRES_REUPLOAD').length} Replacement(s) Required
                  </span>
                </div>

                <div className="divide-y divide-amber-200/80">
                  {documents.filter(d => d.status === 'REQUIRES_REUPLOAD').map((doc) => {
                    const reasonText = doc.review_notes && !["nil", "none"].includes(doc.review_notes.trim().toLowerCase()) 
                      ? doc.review_notes 
                      : "Correction or clearer copy required";

                    return (
                      <div key={doc.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-amber-700" />
                            <span className="font-bold text-sm text-slate-900">
                              {doc.document_type.replace(/_/g, " ").toUpperCase()}
                            </span>
                            <span className="text-[10px] font-mono text-slate-500">ID: {doc.id.slice(0, 8)}</span>
                          </div>
                          <div className="text-xs text-amber-950 bg-white/90 p-2.5 rounded-lg border border-amber-200">
                            <span className="font-semibold text-amber-900">Deficiency Reason: </span>
                            <span>{reasonText}</span>
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            setReplacingDoc(doc);
                            setReplacementFile(null);
                            setReplacementError(null);
                          }}
                          className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm flex items-center gap-1.5 shrink-0 self-start sm:self-center cursor-pointer"
                        >
                          <Upload className="h-3.5 w-3.5" />
                          <span>Replace Document</span>
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Dedicated Workflow 2: ADDITIONAL INFORMATION REQUIRED (Rule 2: New Information / Queries) */}
            {informationRequests && informationRequests.length > 0 && (
              <div className="bg-blue-50/70 border-2 border-blue-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-blue-100 flex justify-between items-center bg-blue-100/60">
                  <div className="flex items-center gap-2.5 text-blue-950">
                    <HelpCircle className="h-5 w-5 text-blue-700 shrink-0" />
                    <div>
                      <h2 className="font-bold text-sm uppercase tracking-wider text-blue-950">
                        ADDITIONAL INFORMATION REQUIRED
                      </h2>
                      <p className="text-xs text-blue-900/80">
                        The underwriter requires new information, clarification, or a document that was not previously submitted.
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded bg-blue-200 text-blue-900">
                    {informationRequests.filter(r => r.status === 'OPEN').length} Open Query
                  </span>
                </div>

                <div className="divide-y divide-blue-100">
                  {informationRequests.map((req) => {
                    const isOpen = req.status === 'OPEN';
                    const isResolved = req.status === 'RESOLVED';

                    return (
                      <div key={req.id} className="p-6 space-y-3 hover:bg-blue-50/40 transition-colors">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-sm text-slate-900">{req.title}</h3>
                            {isResolved ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700 border border-slate-300 flex items-center gap-1">
                                <CheckCircle className="h-3 w-3 text-emerald-600" />
                                <span>RESOLVED</span>
                              </span>
                            ) : isOpen ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-900 border border-blue-300">
                                ACTION REQUIRED
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                                <CheckCircle className="h-3 w-3 text-emerald-600" />
                                <span>RESPONDED</span>
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-slate-500 font-mono">
                            Requested: {req.created_at ? new Date(req.created_at).toLocaleDateString() : "N/A"}
                          </span>
                        </div>

                        <p className="text-xs text-slate-700 leading-relaxed">
                          {req.description}
                        </p>

                        {req.requested_document_type && (
                          <p className="text-[11px] font-mono text-blue-950 bg-white p-2 rounded border border-blue-200">
                            Requested Document Type: <span className="font-semibold text-blue-900">{req.requested_document_type}</span>
                          </p>
                        )}

                        {isOpen && !isDecided ? (
                          <div className="pt-2 flex justify-end">
                            <button
                              onClick={() => {
                                setRespondingReq(req);
                                setResponseFile(null);
                                setResponseNotes("");
                                setResponseError(null);
                              }}
                              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                            >
                              <Upload className="h-3.5 w-3.5" />
                              <span>Respond / Upload</span>
                            </button>
                          </div>
                        ) : isResolved ? (
                          <div className="mt-2 p-3 bg-slate-100 rounded-lg border border-slate-200 text-xs text-slate-600">
                            <span className="font-semibold text-slate-800">Review Status: </span>
                            <span>Satisfactorily reviewed and marked resolved by underwriter.</span>
                          </div>
                        ) : (
                          <div className="mt-2 p-3 bg-emerald-50 rounded-lg border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                            <div className="space-y-0.5">
                              <span className="font-semibold text-emerald-900 block">Response Submitted:</span>
                              <p className="text-slate-600 italic">
                                {req.response_notes || "Document submitted successfully."}
                              </p>
                              {req.responded_at && (
                                <span className="text-[11px] text-emerald-700 font-mono block">
                                  Timestamp: {new Date(req.responded_at).toLocaleString()}
                                </span>
                              )}
                            </div>
                            {req.response_document_id && (
                              <a
                                href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${req.response_document_id}/content`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold inline-flex items-center gap-1 transition-colors shrink-0 shadow-sm"
                              >
                                <span>View Uploaded File</span>
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Linked Documents Card */}
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-slate-600" />
                  <h2 className="font-semibold text-base text-slate-900">{t("applicationDetails.attachedDocsTitle")} ({documents.length})</h2>
                </div>
                {isDraft && (
                  <button
                    onClick={() => setShowDocUpload(!showDocUpload)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-md text-xs font-medium hover:bg-slate-800 transition-colors"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    {t("applicationDetails.attachDocument")}
                  </button>
                )}
              </div>

              {/* Upload Document Form */}
              {showDocUpload && (
                <form onSubmit={handleUploadDocument} className="p-6 bg-slate-50 border-b border-slate-200 space-y-4">
                  <div className="flex justify-between items-center">
                    <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <FileUp className="h-4 w-4 text-blue-600" />
                      {t("applicationDetails.attachDocModalTitle")}
                    </h4>
                    <button 
                      type="button" 
                      onClick={() => setShowDocUpload(false)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {docUploadError && (
                    <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-md">
                      {docUploadError}
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("applicationDetails.docType")}</label>
                      <select
                        value={docType}
                        onChange={(e) => setDocType(e.target.value)}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="IDENTITY_PROOF">{tDocType("IDENTITY_PROOF")}</option>
                        <option value="ADDRESS_PROOF">{tDocType("ADDRESS_PROOF")}</option>
                        <option value="INCOME_PROOF">{tDocType("INCOME_PROOF")}</option>
                        <option value="BANK_STATEMENT">{tDocType("BANK_STATEMENT")}</option>
                        <option value="OTHER">{tDocType("OTHER")}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">{t("applicationDetails.chooseFile")}</label>
                      <input
                        type="file"
                        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                        className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-200 file:text-slate-800 hover:file:bg-slate-300"
                        required
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowDocUpload(false)}
                      className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800"
                    >
                      {t("applicationDetails.cancel")}
                    </button>
                    <button
                      type="submit"
                      disabled={uploadingDoc || !selectedFile}
                      className="px-4 py-1.5 bg-blue-600 text-white rounded-md text-xs font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                      {uploadingDoc ? t("applicationDetails.uploading") : t("applicationDetails.uploadAndAttach")}
                    </button>
                  </div>
                </form>
              )}

              {/* Document List */}
              <div className="p-0">
                {documents.length === 0 ? (
                  <div className="p-8 text-center">
                    <FileText className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm font-medium text-slate-700">{t("applicationDetails.noDocsAttached")}</p>
                    <p className="text-xs text-slate-500 mt-1">{t("applicationDetails.uploadPrompt")}</p>
                  </div>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {documents.map((doc) => {
                      const mimeBadge = getMimeBadge(doc.mime_type, doc.original_filename);
                      const pageText = formatPageCount(doc.page_count, doc.mime_type, doc.original_filename);
                      const displayName = doc.original_filename || doc.file_url.split('/').pop() || "Document";

                      return (
                        <li key={doc.id} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-colors">
                          <div className="flex items-start gap-3">
                            <div className="p-2 bg-slate-100 rounded-lg text-slate-600 mt-0.5 shrink-0">
                              <FileText className="h-5 w-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-sm font-semibold text-slate-900">{tDocType(doc.document_type)}</span>
                                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-200/80 text-slate-700">
                                  {mimeBadge}
                                </span>
                                {doc.file_size_bytes != null && (
                                  <span className="text-[11px] font-mono text-slate-500">
                                    ({formatFileSize(doc.file_size_bytes)})
                                  </span>
                                )}
                                {pageText && (
                                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-50 text-blue-800 border border-blue-200">
                                    {pageText}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-500 mt-0.5 truncate max-w-sm" title={displayName}>
                                {displayName} • {new Date(doc.created_at).toLocaleDateString()}
                              </p>
                              {doc.status === 'REQUIRES_REUPLOAD' && doc.review_notes && !["nil", "none"].includes(doc.review_notes.trim().toLowerCase()) && (
                                <div className="mt-1 p-2 rounded bg-amber-50 border border-amber-200 text-amber-900 text-xs">
                                  <span className="font-semibold">Re-upload note: </span>{doc.review_notes}
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            {getDocStatusBadge(doc.status)}
                            {doc.status === 'REQUIRES_REUPLOAD' && !isDecided && (
                              <button
                                onClick={() => {
                                  setReplacingDoc(doc);
                                  setReplacementFile(null);
                                  setReplacementError(null);
                                }}
                                className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-bold transition-colors inline-flex items-center gap-1 shadow-sm cursor-pointer"
                                title="Replace Document"
                              >
                                <Upload className="h-3 w-3" />
                                <span>Replace</span>
                              </button>
                            )}
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${doc.id}/content`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1 text-slate-500 hover:text-blue-600 transition-colors"
                              title="View Document"
                              aria-label="View Document"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                            {isDraft && (
                              <button
                                onClick={() => handleDeleteDocument(doc.id)}
                                className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                                title={t("common.delete")}
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            </div>

          </div>

          {/* Right Column (Application Timeline & Metadata) */}
          <div className="space-y-6">
            
            {/* Real Application Timeline */}
            <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
              <h3 className="font-semibold text-sm text-slate-900 uppercase tracking-wider mb-5">{t("applicationDetails.statusMilestones")}</h3>
              
              <div className="relative pl-6 space-y-6">
                {/* Vertical timeline line */}
                <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-slate-200"></div>
                
                {/* Milestone 1: Draft Created */}
                <div className="relative">
                  <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-emerald-500 ring-4 ring-white"></div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{t("applicationDetails.milestoneStarted")}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {new Date(application.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </p>
                  </div>
                </div>

                {/* Milestone 2: Submitted */}
                <div className="relative">
                  <div className={`absolute -left-6 top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${isSubmitted ? 'bg-emerald-500' : 'bg-slate-200'}`}></div>
                  <div>
                    <p className={`text-sm font-semibold ${isSubmitted ? 'text-slate-900' : 'text-slate-400'}`}>{t("applicationDetails.milestoneSubmitted")}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {isSubmitted 
                        ? (application.updated_at ? `${t("applicationDetails.submittedOn")} ${new Date(application.updated_at).toLocaleDateString()}` : t("applicationDetails.submittedForReview"))
                        : t("applicationDetails.pendingSubmission")}
                    </p>
                  </div>
                </div>

                {/* Milestone 3: Under Review */}
                <div className="relative">
                  <div className={`absolute -left-6 top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${isUnderReviewOrBeyond ? 'bg-emerald-500' : 'bg-slate-200'}`}></div>
                  <div>
                    <p className={`text-sm font-semibold ${isUnderReviewOrBeyond ? 'text-slate-900' : 'text-slate-400'}`}>{t("applicationDetails.milestoneUnderReview")}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {application.status === 'UNDER_REVIEW' && t("applicationDetails.verificationByCredit")}
                      {application.status === 'ADDITIONAL_INFO_REQUIRED' && t("applicationDetails.infoRequested")}
                      {isDecided && t("applicationDetails.verificationComplete")}
                      {!isUnderReviewOrBeyond && t("applicationDetails.awaitingQueue")}
                    </p>
                  </div>
                </div>

                {/* Milestone 4: Final Decision */}
                <div className="relative">
                  <div className={`absolute -left-6 top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${
                    application.status === 'APPROVED' ? 'bg-emerald-500' :
                    application.status === 'DECLINED' ? 'bg-rose-500' : 'bg-slate-200'
                  }`}></div>
                  <div>
                    <p className={`text-sm font-semibold ${isDecided ? 'text-slate-900' : 'text-slate-400'}`}>
                      {application.status === 'APPROVED' ? tStatus('APPROVED') : application.status === 'DECLINED' ? tStatus('DECLINED') : t("applicationDetails.milestoneFinalDecision")}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {application.status === 'APPROVED' && t("applicationDetails.sanctionPrepared")}
                      {application.status === 'DECLINED' && t("applicationDetails.criteriaUnmet")}
                      {!isDecided && t("applicationDetails.finalDecisionPending")}
                    </p>
                    {isDecided && application.updated_at && (
                      <p className="text-[11px] text-slate-500 font-mono mt-1 flex items-center gap-1">
                        <Clock className="h-3 w-3 text-slate-400 shrink-0" />
                        <span>
                          {new Date(application.updated_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Compliance & Security Guarantee */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-slate-800 font-semibold text-sm">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span>{t("applicationDetails.bankingComplianceTitle")}</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {t("applicationDetails.bankingComplianceText")}
              </p>
            </div>

            {/* AI Assistant Navigation */}
            <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-blue-900 font-semibold text-sm">
                <HelpCircle className="h-4 w-4 text-blue-600" />
                <span>{t("aiAssistant.title")}</span>
              </div>
              <p className="text-xs text-slate-600">
                {t("aiAssistant.subtitle")}
              </p>
              <Link
                href="/dashboard/ai"
                className="inline-flex items-center text-xs font-semibold text-blue-700 hover:text-blue-800 hover:underline"
              >
                {t("aiAssistant.askButton")} →
              </Link>
            </div>

          </div>

        </div>

      </div>

      {/* Modal: Respond to Information Request */}
      {respondingReq && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-amber-700">
                <Upload className="h-5 w-5" />
                <h3 className="font-bold text-base text-slate-900">Upload Requested Document</h3>
              </div>
              <button
                type="button"
                onClick={() => setRespondingReq(null)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 space-y-1 text-xs">
              <p className="font-bold text-amber-950">{respondingReq.title}</p>
              <p className="text-amber-900/90">{respondingReq.description}</p>
              {respondingReq.requested_document_type && (
                <p className="text-[11px] font-mono text-amber-800 mt-1">
                  Expected type: {respondingReq.requested_document_type}
                </p>
              )}
            </div>

            {responseError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                {responseError}
              </div>
            )}

            <form onSubmit={handleRespondToRequest} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select Document File <span className="text-rose-500">*</span>
                </label>
                <input
                  type="file"
                  onChange={(e) => setResponseFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-800 hover:file:bg-slate-200 border border-slate-300 rounded-lg p-1"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Supplementary Notes (Optional)
                </label>
                <textarea
                  value={responseNotes}
                  onChange={(e) => setResponseNotes(e.target.value)}
                  placeholder="Provide any additional explanation or clarification for the credit officer..."
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setRespondingReq(null)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingResponse || !responseFile}
                  className="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                >
                  {isSubmittingResponse ? "Uploading & Responding..." : "Submit Response"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Replace Deficient Document */}
      {replacingDoc && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-amber-700">
                <Upload className="h-5 w-5" />
                <h3 className="font-bold text-sm uppercase tracking-wider text-slate-900">
                  Replace Document
                </h3>
              </div>
              <button
                onClick={() => setReplacingDoc(null)}
                className="text-slate-400 hover:text-slate-600 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-950 space-y-1">
              <p className="font-semibold">
                Document: {tDocType(replacingDoc.document_type)}
              </p>
              <p className="text-[11px] font-mono text-amber-800 truncate" title={replacingDoc.original_filename || replacingDoc.file_url}>
                Current file: {replacingDoc.original_filename || replacingDoc.file_url.split('/').pop()}
              </p>
              <p className="text-amber-900">
                <span className="font-semibold">Underwriter reason: </span>
                {replacingDoc.review_notes && !["nil", "none"].includes(replacingDoc.review_notes.trim().toLowerCase()) 
                  ? replacingDoc.review_notes 
                  : "Correction or clearer copy required"}
              </p>
              <p className="text-[10px] text-amber-700 mt-1">
                Supported formats: PDF, JPEG, PNG (Max 10 MB)
              </p>
            </div>

            {replacementError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                {replacementError}
              </div>
            )}

            <form onSubmit={handleReplaceDocument} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Choose Replacement File <span className="text-rose-500">*</span>
                </label>
                <input
                  type="file"
                  onChange={(e) => setReplacementFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-amber-100 file:text-amber-900 hover:file:bg-amber-200 border border-slate-300 rounded-lg p-1"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setReplacingDoc(null)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploadingReplacement || !replacementFile}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-400 text-white rounded-lg text-xs font-bold transition-colors disabled:cursor-not-allowed cursor-pointer"
                >
                  {isUploadingReplacement ? "Uploading Replacement..." : "Upload Replacement"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}

