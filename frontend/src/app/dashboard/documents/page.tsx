"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect, useRef, useMemo } from "react";
import { 
  FileText, 
  Search, 
  Upload, 
  X, 
  CheckCircle, 
  Clock, 
  FileWarning, 
  Trash2, 
  ShieldCheck, 
  FolderOpen, 
  AlertTriangle,
  ExternalLink 
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";

export default function DocumentsPage() {
  const { t, tDocType } = useLanguage();
  const [documents, setDocuments] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Upload State
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadData, setUploadData] = useState({ document_type: 'IDENTITY_PROOF', application_id: '' });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const [docsRes, appsRes] = await Promise.all([
        fetch(`${apiUrl}/api/documents`, { credentials: 'include' }),
        fetch(`${apiUrl}/api/applications`, { credentials: 'include' })
      ]);

      if (docsRes.ok) {
        const data = await docsRes.json();
        setDocuments(data || []);
      } else {
        setError(t("documents.failedUpload"));
      }

      if (appsRes.ok) {
        const appsData = await appsRes.json();
        setApplications(appsData || []);
      }
    } catch {
      setError(t("documents.failedUpload"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a file to upload.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append('document_type', uploadData.document_type);
      formData.append('file', selectedFile);
      if (uploadData.application_id) {
        formData.append('application_id', uploadData.application_id);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/documents`, {
        method: 'POST',
        body: formData,
        credentials: 'include'
      });

      if (res.ok) {
        setShowUploadModal(false);
        setSelectedFile(null);
        setUploadData({ document_type: 'IDENTITY_PROOF', application_id: '' });
        fetchDocuments();
      } else {
        const errJson = await res.json().catch(() => null);
        setUploadError(errJson?.detail || t("documents.failedUpload"));
      }
    } catch {
      setUploadError(t("documents.failedUpload"));
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("documents.deleteConfirm"))) return;
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/documents/${id}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (res.ok) {
        fetchDocuments();
      } else {
        alert("Failed to delete document.");
      }
    } catch {
      alert("Network error while deleting document.");
    }
  };

  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase();
    return documents.filter((doc) => 
      (doc.document_type && doc.document_type.toLowerCase().includes(q)) ||
      (doc.file_url && doc.file_url.toLowerCase().includes(q)) ||
      (doc.application_id && doc.application_id.toLowerCase().includes(q))
    );
  }, [documents, searchQuery]);

  const getStatusBadge = (status: string) => {
    switch(status) {
      case 'UPLOADED': 
        return {
          label: t("status.uploaded"),
          className: 'bg-slate-100 text-slate-800 border-slate-300',
          icon: <Clock className="h-3 w-3 text-slate-600" />
        };
      case 'PROCESSING': 
        return {
          label: t("status.processing"),
          className: 'bg-amber-50 text-amber-800 border-amber-300',
          icon: <div className="h-3 w-3 rounded-full border-2 border-amber-600 border-t-transparent animate-spin" />
        };
      case 'VERIFIED': 
        return {
          label: t("status.verified"),
          className: 'bg-emerald-50 text-emerald-800 border-emerald-300',
          icon: <CheckCircle className="h-3 w-3 text-emerald-600" />
        };
      case 'REJECTED': 
        return {
          label: t("status.rejected"),
          className: 'bg-red-50 text-red-800 border-red-300',
          icon: <FileWarning className="h-3 w-3 text-red-600" />
        };
      case 'REQUIRES_REUPLOAD':
        return {
          label: t("status.requiresReupload"),
          className: 'bg-purple-50 text-purple-800 border-purple-300',
          icon: <AlertTriangle className="h-3 w-3 text-purple-600" />
        };
      default: 
        return {
          label: status,
          className: 'bg-slate-50 text-slate-700 border-slate-200',
          icon: <FileText className="h-3 w-3 text-slate-500" />
        };
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
                {t("documents.title")}
              </h1>
              <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                {filteredDocuments.length} Documents on File
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{t("documents.subtitle")}</p>
          </div>

          <button 
            onClick={() => { setShowUploadModal(true); setUploadError(null); }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors shadow-xs"
          >
            <Upload className="h-4 w-4" />
            <span>{t("documents.uploadDocument")}</span>
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 text-xs text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Regulatory Advisory Banner */}
        <div className="p-3.5 bg-slate-50 border border-slate-200 rounded flex items-start gap-2.5 text-xs text-slate-600">
          <ShieldCheck className="h-4 w-4 text-blue-700 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-slate-900 font-semibold">Statutory Compliance Notice:</strong> All documents submitted are securely registered and associated with your loan dossier. Verification and OCR extraction are conducted during credit underwriting review (M07).
          </p>
        </div>

        {/* Document Ledger Table */}
        <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div className="relative w-full max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input 
                type="text" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("documents.searchPlaceholder")} 
                className="w-full pl-9 pr-4 py-2 text-xs border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white font-sans"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex flex-col h-48 items-center justify-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{t("common.loading")}</p>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="text-center py-12 px-4">
              <FolderOpen className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">{t("documents.noDocsTitle")}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">{t("documents.noDocsSubtitle")}</p>
              <button 
                onClick={() => { setShowUploadModal(true); setUploadError(null); }}
                className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors"
              >
                <Upload className="h-3.5 w-3.5" />
                <span>{t("documents.uploadFirstDoc")}</span>
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="text-[11px] text-slate-600 uppercase tracking-wider bg-slate-100/70 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("documents.tableDoc")}</th>
                    <th className="px-4 py-3 font-semibold">{t("documents.tableApp")}</th>
                    <th className="px-4 py-3 font-semibold">{t("documents.tableStatus")}</th>
                    <th className="px-4 py-3 font-semibold">{t("documents.tableDate")}</th>
                    <th className="px-4 py-3 font-semibold text-right">{t("documents.tableActions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-sans">
                  {filteredDocuments.map((doc) => {
                    const badge = getStatusBadge(doc.status);
                    return (
                      <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="p-1.5 bg-slate-100 rounded text-slate-600 shrink-0">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-slate-900">{tDocType(doc.document_type)}</p>
                              <p className="text-[11px] text-slate-500 truncate max-w-[200px]" title={doc.file_url}>
                                {doc.file_url.split('/').pop()}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-slate-700">
                          {doc.application_id ? (
                            <span className="font-mono">{doc.application_id}</span>
                          ) : (
                            <span className="text-slate-400 italic">General Portfolio</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${badge.className}`}>
                            {badge.icon}
                            <span>{badge.label}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {doc.created_at ? new Date(doc.created_at).toLocaleDateString('en-IN', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric'
                          }) : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/documents/${doc.id}/content`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-2 py-1 text-slate-600 hover:text-blue-600 rounded hover:bg-slate-100 text-xs font-semibold transition-colors"
                              title="View Document"
                              aria-label="View Document"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>View</span>
                            </a>
                            <button 
                              onClick={() => handleDelete(doc.id)}
                              disabled={doc.status === 'VERIFIED' || doc.status === 'PROCESSING'}
                              className="text-slate-400 hover:text-red-600 disabled:opacity-30 disabled:hover:text-slate-400 transition-colors p-1 rounded hover:bg-slate-100"
                              title={t("common.delete")}
                              aria-label={t("common.delete")}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
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

      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/50 backdrop-blur-xs">
          <div className="bg-white rounded border border-slate-200 shadow-xl w-full max-w-md overflow-hidden animate-in fade-in-50 duration-150">
            <div className="flex justify-between items-center px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                {t("documents.uploadModalTitle")}
              </h3>
              <button 
                onClick={() => setShowUploadModal(false)} 
                className="text-slate-400 hover:text-slate-700 p-1" 
                aria-label={t("common.close")}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            
            <form onSubmit={handleUploadSubmit} className="p-5 space-y-4 text-xs">
              {uploadError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded">
                  {uploadError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("documents.docTypeLabel")}</label>
                <select 
                  value={uploadData.document_type}
                  onChange={(e) => setUploadData({ ...uploadData, document_type: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs"
                >
                  <option value="IDENTITY_PROOF">{tDocType("IDENTITY_PROOF")}</option>
                  <option value="ADDRESS_PROOF">{tDocType("ADDRESS_PROOF")}</option>
                  <option value="INCOME_PROOF">{tDocType("INCOME_PROOF")}</option>
                  <option value="BANK_STATEMENT">{tDocType("BANK_STATEMENT")}</option>
                  <option value="OTHER">{tDocType("OTHER")}</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("documents.appLinkLabel")}</label>
                <select 
                  value={uploadData.application_id}
                  onChange={(e) => setUploadData({ ...uploadData, application_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs font-mono"
                >
                  <option value="">{t("documents.optionalLink")}</option>
                  {applications.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.loan_type} — {app.id} ({app.status})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("documents.fileLabel")}</label>
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="border border-dashed border-slate-300 rounded p-4 text-center cursor-pointer hover:bg-slate-50 transition-colors"
                >
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileChange} 
                    className="hidden" 
                    accept=".pdf,.jpg,.jpeg,.png"
                  />
                  {selectedFile ? (
                    <div className="space-y-1">
                      <p className="font-semibold text-slate-900 truncate">{selectedFile.name}</p>
                      <p className="text-[11px] text-slate-500 font-mono">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <Upload className="h-5 w-5 text-slate-400 mx-auto" />
                      <p className="text-slate-600">Click to select PDF or image file</p>
                      <p className="text-[10px] text-slate-400">Supported: PDF, JPEG, PNG (Max 10MB)</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded text-xs font-semibold hover:bg-slate-50 transition-colors"
                >
                  {t("documents.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !selectedFile}
                  className="px-4 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isUploading ? t("documents.uploading") : t("documents.uploadAndSave")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </AuthenticatedLayout>
  );
}
