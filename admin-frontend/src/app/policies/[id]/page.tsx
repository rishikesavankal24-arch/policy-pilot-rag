"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { 
  Policy, 
  RegulatoryAuthority, 
  PolicyApplicability, 
  PolicyVersionHistoryItem,
  PolicyStatus 
} from "@/types";
import { PolicyStatusBadge } from "@/components/policies/PolicyStatusBadge";
import { 
  ArrowLeft, 
  RefreshCw, 
  FileText, 
  UploadCloud, 
  CheckCircle2, 
  AlertTriangle, 
  X, 
  Edit, 
  Plus, 
  Trash2, 
  ExternalLink, 
  Download, 
  Eye, 
  Layers, 
  Calendar, 
  Building2, 
  ShieldCheck, 
  Clock, 
  Archive,
  ArrowRight,
  Send,
  Sparkles,
  Lock
} from "lucide-react";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PolicyDetailPage({ params }: PageProps) {
  const router = useRouter();
  const resolvedParams = use(params);
  const policyId = resolvedParams.id;

  const [policy, setPolicy] = useState<Policy | null>(null);
  const [authorities, setAuthorities] = useState<RegulatoryAuthority[]>([]);
  const [applicabilities, setApplicabilities] = useState<PolicyApplicability[]>([]);
  const [history, setHistory] = useState<PolicyVersionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Active Tab: "overview" | "applicability" | "versions" | "lifecycle"
  const [activeTab, setActiveTab] = useState<"overview" | "applicability" | "versions" | "lifecycle">("overview");

  // Edit Policy Metadata Modal
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    title: "",
    description: "",
    category: "",
    policy_type: "",
    institution: "",
    jurisdiction: "",
    regulatory_authority_id: ""
  });

  // Add Applicability Modal
  const [isAddAppOpen, setIsAddAppOpen] = useState(false);
  const [appSubmitting, setAppSubmitting] = useState(false);
  const [appError, setAppError] = useState<string | null>(null);
  const [appForm, setAppForm] = useState({
    institution: "",
    jurisdiction: "",
    loan_type: "",
    department: ""
  });
  const [deletingAppId, setDeletingAppId] = useState<string | null>(null);

  // Upload Version Modal
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadSubmitting, setUploadSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadChangelog, setUploadChangelog] = useState("");
  const [uploadEffectiveFrom, setUploadEffectiveFrom] = useState("");
  const [uploadEffectiveTo, setUploadEffectiveTo] = useState("");

  // Edit Version Metadata Modal
  const [editingVersion, setEditingVersion] = useState<PolicyVersionHistoryItem | null>(null);
  const [vMetaSubmitting, setVMetaSubmitting] = useState(false);
  const [vMetaError, setVMetaError] = useState<string | null>(null);
  const [vMetaForm, setVMetaForm] = useState({
    changelog: "",
    effective_from: "",
    effective_to: ""
  });

  // Lifecycle Modals
  const [isPublishOpen, setIsPublishOpen] = useState(false);
  const [isActivateOpen, setIsActivateOpen] = useState(false);
  const [isSupersedeOpen, setIsSupersedeOpen] = useState(false);
  const [isArchiveOpen, setIsArchiveOpen] = useState(false);
  const [lifecycleSubmitting, setLifecycleSubmitting] = useState(false);
  const [lifecycleError, setLifecycleError] = useState<string | null>(null);

  // Activation & Supersede Selection
  const [selectedVersionForActivation, setSelectedVersionForActivation] = useState<string>("");
  const [selectedNewVersionForSupersede, setSelectedNewVersionForSupersede] = useState<string>("");

  const fetchPolicyData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [polData, authList, appList, histList] = await Promise.all([
        adminApi.getPolicy(policyId),
        adminApi.getRegulatoryAuthorities().catch(() => []),
        adminApi.getPolicyApplicability(policyId).catch(() => []),
        adminApi.getPolicyHistory(policyId).catch(() => [])
      ]);
      setPolicy(polData);
      setAuthorities(authList);
      setApplicabilities(appList);
      setHistory(histList);
    } catch (err: any) {
      setError(err.message || "Failed to load policy record.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicyData();
  }, [policyId]);

  // Open Edit Metadata Modal
  const openEditPolicyModal = () => {
    if (!policy) return;
    setEditForm({
      title: policy.title,
      description: policy.description || "",
      category: policy.category || "LENDING",
      policy_type: policy.policy_type || "REGULATORY",
      institution: policy.institution || "",
      jurisdiction: policy.jurisdiction || "",
      regulatory_authority_id: policy.regulatory_authority_id || ""
    });
    setEditError(null);
    setIsEditOpen(true);
  };

  // Submit Edit Metadata
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditSubmitting(true);
    setEditError(null);
    try {
      await adminApi.updatePolicy(policyId, {
        title: editForm.title.trim(),
        description: editForm.description.trim() || undefined,
        category: editForm.category || undefined,
        policy_type: editForm.policy_type || undefined,
        institution: editForm.institution.trim() || undefined,
        jurisdiction: editForm.jurisdiction.trim() || undefined,
        regulatory_authority_id: editForm.regulatory_authority_id || undefined
      });
      setSuccessMessage("Policy metadata updated successfully.");
      setIsEditOpen(false);
      await fetchPolicyData();
    } catch (err: any) {
      setEditError(err.message || "Failed to update policy metadata.");
    } finally {
      setEditSubmitting(false);
    }
  };

  // Add Applicability Rule
  const handleAddApplicability = async (e: React.FormEvent) => {
    e.preventDefault();
    setAppSubmitting(true);
    setAppError(null);
    try {
      if (!appForm.institution && !appForm.jurisdiction && !appForm.loan_type && !appForm.department) {
        throw new Error("At least one applicability dimension (Institution, Jurisdiction, Loan Type, or Department) is required.");
      }
      await adminApi.addPolicyApplicability(policyId, {
        institution: appForm.institution.trim() || undefined,
        jurisdiction: appForm.jurisdiction.trim() || undefined,
        loan_type: appForm.loan_type.trim() || undefined,
        department: appForm.department.trim() || undefined
      });
      setSuccessMessage("Applicability rule attached successfully.");
      setIsAddAppOpen(false);
      setAppForm({ institution: "", jurisdiction: "", loan_type: "", department: "" });
      const updatedApps = await adminApi.getPolicyApplicability(policyId);
      setApplicabilities(updatedApps || []);
    } catch (err: any) {
      setAppError(err.message || "Failed to add applicability rule.");
    } finally {
      setAppSubmitting(false);
    }
  };

  // Delete Applicability Rule
  const handleDeleteApplicability = async (applicabilityId: string) => {
    try {
      await adminApi.deletePolicyApplicability(policyId, applicabilityId);
      setSuccessMessage("Applicability rule removed.");
      setDeletingAppId(null);
      const updatedApps = await adminApi.getPolicyApplicability(policyId);
      setApplicabilities(updatedApps || []);
    } catch (err: any) {
      setError(err.message || "Failed to delete applicability rule.");
    }
  };

  // Upload Version Document
  const handleUploadVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a valid PDF or image file.");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setUploadError("File exceeds 10 MB limit.");
      return;
    }

    setUploadSubmitting(true);
    setUploadError(null);
    try {
      const fd = new FormData();
      fd.append("file", selectedFile);
      if (uploadChangelog.trim()) fd.append("changelog", uploadChangelog.trim());
      if (uploadEffectiveFrom) fd.append("effective_from", new Date(uploadEffectiveFrom).toISOString());
      if (uploadEffectiveTo) fd.append("effective_to", new Date(uploadEffectiveTo).toISOString());

      await adminApi.uploadPolicyVersion(policyId, fd);
      setSuccessMessage("New policy version document uploaded and validated.");
      setIsUploadOpen(false);
      setSelectedFile(null);
      setUploadChangelog("");
      setUploadEffectiveFrom("");
      setUploadEffectiveTo("");
      await fetchPolicyData();
    } catch (err: any) {
      setUploadError(err.message || "Upload failed. Verify document integrity.");
    } finally {
      setUploadSubmitting(false);
    }
  };

  // Edit Version Metadata (Changelog & Effective Dates)
  const openEditVersionModal = (v: PolicyVersionHistoryItem) => {
    setEditingVersion(v);
    setVMetaForm({
      changelog: v.changelog || "",
      effective_from: v.effective_from ? v.effective_from.slice(0, 16) : "",
      effective_to: v.effective_to ? v.effective_to.slice(0, 16) : ""
    });
    setVMetaError(null);
  };

  const handleEditVersionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingVersion) return;
    setVMetaSubmitting(true);
    setVMetaError(null);
    try {
      await adminApi.updatePolicyVersionMetadata(policyId, editingVersion.id, {
        changelog: vMetaForm.changelog.trim() || undefined,
        effective_from: vMetaForm.effective_from ? new Date(vMetaForm.effective_from).toISOString() : undefined,
        effective_to: vMetaForm.effective_to ? new Date(vMetaForm.effective_to).toISOString() : undefined
      });
      setSuccessMessage(`Metadata for Version ${editingVersion.version_number} updated.`);
      setEditingVersion(null);
      await fetchPolicyData();
    } catch (err: any) {
      setVMetaError(err.message || "Failed to update version metadata.");
    } finally {
      setVMetaSubmitting(false);
    }
  };

  // Lifecycle Transitions
  const handlePublish = async () => {
    setLifecycleSubmitting(true);
    setLifecycleError(null);
    try {
      await adminApi.publishPolicy(policyId);
      setSuccessMessage("Policy successfully transitioned from DRAFT to PUBLISHED.");
      setIsPublishOpen(false);
      await fetchPolicyData();
    } catch (err: any) {
      setLifecycleError(err.message || "Publish transition rejected by state machine.");
    } finally {
      setLifecycleSubmitting(false);
    }
  };

  const handleActivate = async () => {
    setLifecycleSubmitting(true);
    setLifecycleError(null);
    try {
      await adminApi.activatePolicy(policyId, selectedVersionForActivation || undefined);
      setSuccessMessage("Policy version activated.");
      setIsActivateOpen(false);
      await fetchPolicyData();
    } catch (err: any) {
      setLifecycleError(err.message || "Activation transition rejected.");
    } finally {
      setLifecycleSubmitting(false);
    }
  };

  const handleSupersede = async () => {
    if (!selectedNewVersionForSupersede) {
      setLifecycleError("Please select a target version to supersede this active policy.");
      return;
    }
    setLifecycleSubmitting(true);
    setLifecycleError(null);
    try {
      await adminApi.supersedePolicy(policyId, selectedNewVersionForSupersede);
      setSuccessMessage("Policy successfully superseded with selected version.");
      setIsSupersedeOpen(false);
      await fetchPolicyData();
    } catch (err: any) {
      setLifecycleError(err.message || "Supersede transition rejected.");
    } finally {
      setLifecycleSubmitting(false);
    }
  };

  const handleArchive = async () => {
    setLifecycleSubmitting(true);
    setLifecycleError(null);
    try {
      await adminApi.archivePolicy(policyId);
      setSuccessMessage("Policy moved to terminal ARCHIVED state.");
      setIsArchiveOpen(false);
      await fetchPolicyData();
    } catch (err: any) {
      setLifecycleError(err.message || "Archive transition rejected.");
    } finally {
      setLifecycleSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3 text-slate-500">
          <RefreshCw className="h-6 w-6 animate-spin text-amber-500" />
          <span className="text-xs uppercase tracking-wider font-mono">Loading supervisory policy record...</span>
        </div>
      </AdminLayout>
    );
  }

  if (error || !policy) {
    return (
      <AdminLayout>
        <div className="p-6 bg-white border border-slate-200 rounded-xl space-y-4">
          <div className="flex items-center gap-2 text-rose-600 font-bold">
            <AlertTriangle className="h-5 w-5" />
            <span>Policy Not Found or Access Denied</span>
          </div>
          <p className="text-xs text-slate-600">
            {error || "The requested policy could not be found."}
          </p>
          <Link
            href="/policies"
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Policies Directory</span>
          </Link>
        </div>
      </AdminLayout>
    );
  }

  const authority = authorities.find((a) => a.id === policy.regulatory_authority_id);
  const currentVersion = history.find((h) => h.id === policy.current_version_id);

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Navigation Breadcrumb & Back Link */}
        <div className="flex items-center justify-between">
          <Link
            href="/policies"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Policies Directory</span>
          </Link>

          <span className="text-[11px] font-mono text-slate-400">
            UUID: {policy.id}
          </span>
        </div>

        {/* Global Feedback Banners */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {successMessage && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-500 hover:text-emerald-700">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Policy Header Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="font-mono text-lg font-bold text-slate-950">
                  {policy.policy_code}
                </span>
                <PolicyStatusBadge status={policy.status} size="md" />
                {policy.category && (
                  <span className="text-[11px] font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-semibold">
                    {policy.category}
                  </span>
                )}
                {authority && (
                  <span className="text-[11px] font-mono bg-amber-50 text-amber-900 px-2 py-0.5 rounded border border-amber-200 font-semibold">
                    {authority.short_name}
                  </span>
                )}
              </div>
              <h1 className="text-lg font-bold text-slate-900 leading-snug">
                {policy.title}
              </h1>
              <p className="text-xs text-slate-500">
                {policy.description || "No formal executive description registered."}
              </p>
            </div>

            {/* Quick Lifecycle Action Toolbar */}
            <div className="flex items-center gap-2 flex-wrap shrink-0">
              {policy.status === "DRAFT" && (
                <>
                  <button
                    onClick={openEditPolicyModal}
                    className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Edit className="h-3.5 w-3.5" />
                    <span>Edit Metadata</span>
                  </button>

                  <button
                    onClick={() => { setLifecycleError(null); setIsPublishOpen(true); }}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
                  >
                    <Send className="h-3.5 w-3.5" />
                    <span>Publish Policy</span>
                  </button>
                </>
              )}

              {policy.status === "PUBLISHED" && (
                <button
                  onClick={() => {
                    setLifecycleError(null);
                    setSelectedVersionForActivation(policy.current_version_id || (history[0]?.id || ""));
                    setIsActivateOpen(true);
                  }}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Activate Policy</span>
                </button>
              )}

              {policy.status === "ACTIVE" && (
                <>
                  <button
                    onClick={() => {
                      setLifecycleError(null);
                      const otherVersions = history.filter((h) => h.id !== policy.current_version_id);
                      setSelectedNewVersionForSupersede(otherVersions[0]?.id || "");
                      setIsSupersedeOpen(true);
                    }}
                    className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors"
                  >
                    <Layers className="h-3.5 w-3.5" />
                    <span>Supersede</span>
                  </button>

                  <button
                    onClick={() => { setLifecycleError(null); setIsArchiveOpen(true); }}
                    className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Archive className="h-3.5 w-3.5" />
                    <span>Archive</span>
                  </button>
                </>
              )}

              {policy.status === "SUPERSEDED" && (
                <button
                  onClick={() => { setLifecycleError(null); setIsArchiveOpen(true); }}
                  className="px-3 py-1.5 bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-300 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  <Archive className="h-3.5 w-3.5" />
                  <span>Archive</span>
                </button>
              )}

              {policy.status === "ARCHIVED" && (
                <span className="px-3 py-1 bg-stone-100 text-stone-600 border border-stone-300 rounded-lg text-xs font-mono font-semibold flex items-center gap-1">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Archived (Immutable)</span>
                </span>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-slate-200 text-xs font-semibold pt-2 gap-6">
            <button
              onClick={() => setActiveTab("overview")}
              className={`pb-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "overview"
                  ? "border-amber-500 text-slate-900 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Overview</span>
            </button>

            <button
              onClick={() => setActiveTab("applicability")}
              className={`pb-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "applicability"
                  ? "border-amber-500 text-slate-900 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              <span>Applicability Scope ({applicabilities.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("versions")}
              className={`pb-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "versions"
                  ? "border-amber-500 text-slate-900 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Versions & Ingestion ({history.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("lifecycle")}
              className={`pb-3 border-b-2 flex items-center gap-1.5 transition-colors ${
                activeTab === "lifecycle"
                  ? "border-amber-500 text-slate-900 font-bold"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Clock className="h-3.5 w-3.5" />
              <span>Lifecycle State Machine</span>
            </button>
          </div>
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Metadata Card */}
            <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
                Policy Parameters & Governance
              </h2>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Policy Code</span>
                  <span className="font-mono font-bold text-slate-800">{policy.policy_code}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Domain Category</span>
                  <span className="font-semibold text-slate-800">{policy.category || "—"}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Policy Type</span>
                  <span className="font-semibold text-slate-800">{policy.policy_type || "—"}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Target Institution</span>
                  <span className="font-semibold text-slate-800">{policy.institution || "Universal / All Banks"}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Jurisdiction</span>
                  <span className="font-mono font-semibold text-slate-800">{policy.jurisdiction || "Global"}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Current Active Version</span>
                  <span className="font-mono text-emerald-700 font-bold">
                    {currentVersion ? `v${currentVersion.version_number}` : "None Linked"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Created Timestamp</span>
                  <span className="text-slate-600 font-mono">
                    {policy.created_at ? new Date(policy.created_at).toLocaleString() : "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Last Updated</span>
                  <span className="text-slate-600 font-mono">
                    {policy.updated_at ? new Date(policy.updated_at).toLocaleString() : "—"}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-mono text-[10px] uppercase block">Author Officer ID</span>
                  <span className="font-mono text-slate-600 truncate block">
                    {policy.created_by || "System Admin"}
                  </span>
                </div>
              </div>

              {/* Regulatory Authority Context */}
              <div className="pt-4 border-t border-slate-100">
                <span className="text-slate-400 font-mono text-[10px] uppercase block mb-1">
                  Governing Regulatory Authority
                </span>
                {authority ? (
                  <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg">
                    <div>
                      <span className="font-bold text-slate-800 text-xs block">{authority.name} ({authority.short_name})</span>
                      <span className="text-[11px] text-slate-500 font-mono">{authority.authority_type} • {authority.jurisdiction}</span>
                    </div>
                    {authority.website_url && (
                      <a
                        href={authority.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 font-semibold"
                      >
                        <span>Official Website</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ) : (
                  <span className="text-xs text-slate-500 italic">No external regulatory authority assigned. (Internal Policy)</span>
                )}
              </div>
            </div>

            {/* Side Information Summary */}
            <div className="space-y-4">
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
                  Supervisory Status
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Lifecycle State:</span>
                    <PolicyStatusBadge status={policy.status} />
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Total Versions:</span>
                    <span className="font-mono font-bold text-slate-800">{history.length}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Applicability Rules:</span>
                    <span className="font-mono font-bold text-slate-800">{applicabilities.length}</span>
                  </div>
                </div>
              </div>

              <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-4 text-slate-300 space-y-2 text-xs">
                <div className="flex items-center gap-2 text-amber-400 font-bold">
                  <ShieldCheck className="h-4 w-4" />
                  <span>Audit & Immutability Protocol</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Published and Active policies are bound by strict banking immutability. Version documents, hashes, and numbers cannot be modified once published.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: APPLICABILITY */}
        {activeTab === "applicability" && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-4 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase">
                  Policy Applicability Scopes
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Define which institutions, jurisdictions, loan products, or departments this policy applies to
                </p>
              </div>

              <button
                onClick={() => setIsAddAppOpen(true)}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors self-start sm:self-auto"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add Applicability Scope</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Institution</th>
                    <th className="px-4 py-3">Jurisdiction</th>
                    <th className="px-4 py-3">Loan Type / Product</th>
                    <th className="px-4 py-3">Department</th>
                    <th className="px-4 py-3">Attached Date</th>
                    <th className="px-4 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {applicabilities.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                        No applicability rules defined. This policy currently applies universally.
                      </td>
                    </tr>
                  ) : (
                    applicabilities.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-semibold text-slate-800">
                          {app.institution || "Any"}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600">
                          {app.jurisdiction || "Any"}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600">
                          {app.loan_type ? (
                            <span className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px] font-semibold text-slate-700">
                              {app.loan_type}
                            </span>
                          ) : "Any"}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {app.department || "Any"}
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {app.created_at ? new Date(app.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setDeletingAppId(app.id)}
                            className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                            title="Remove Scope"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: VERSIONS & INGESTION */}
        {activeTab === "versions" && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs space-y-4 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase">
                  Version History & Source Documents
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Controlled document ingestion, structural validation (magic-byte & PDF parsing), and version lineage
                </p>
              </div>

              <button
                onClick={() => { setUploadError(null); setIsUploadOpen(true); }}
                className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors self-start sm:self-auto"
              >
                <UploadCloud className="h-4 w-4" />
                <span>Upload New Version</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Status Context</th>
                    <th className="px-4 py-3">Document Specs</th>
                    <th className="px-4 py-3">SHA-256 Hash</th>
                    <th className="px-4 py-3">Effective Range</th>
                    <th className="px-4 py-3">Changelog</th>
                    <th className="px-4 py-3">Uploaded At</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                        No policy versions uploaded yet. Upload a validated document to begin.
                      </td>
                    </tr>
                  ) : (
                    history.map((v) => {
                      const isActive = policy.current_version_id === v.id;
                      return (
                        <tr key={v.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-mono font-bold text-slate-800">
                            v{v.version_number}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                              isActive 
                                ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                                : "bg-slate-100 text-slate-700 border border-slate-200"
                            }`}>
                              {v.status_context || (isActive ? "ACTIVE VERSION" : "HISTORICAL")}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">
                            {v.page_count ? `${v.page_count} pages` : "1 page"} • {
                              v.file_size_bytes 
                                ? `${(v.file_size_bytes / 1024).toFixed(1)} KB`
                                : "—"
                            }
                          </td>
                          <td className="px-4 py-3 text-slate-500 font-mono text-[10px]" title={v.file_hash || ""}>
                            {v.file_hash ? `${v.file_hash.slice(0, 12)}...` : "—"}
                          </td>
                          <td className="px-4 py-3 text-slate-600 font-mono text-[10px]">
                            <div>From: {v.effective_from ? new Date(v.effective_from).toLocaleDateString() : "Immediate"}</div>
                            <div>To: {v.effective_to ? new Date(v.effective_to).toLocaleDateString() : "Indefinite"}</div>
                          </td>
                          <td className="px-4 py-3 text-slate-600 text-xs max-w-xs">
                            <span className="line-clamp-2">{v.changelog || "Initial upload"}</span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                            {v.created_at ? new Date(v.created_at).toLocaleDateString() : "—"}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* Open in tab */}
                              <button
                                onClick={() => adminApi.viewPolicyVersionFileInTab(policyId, v.id)}
                                className="p-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded"
                                title="View Document in Tab"
                              >
                                <Eye className="h-3.5 w-3.5" />
                              </button>

                              {/* Download file */}
                              <button
                                onClick={() => adminApi.downloadPolicyVersionFile(policyId, v.id, `${policy.policy_code}_v${v.version_number}.pdf`)}
                                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
                                title="Download Document"
                              >
                                <Download className="h-3.5 w-3.5" />
                              </button>

                              {/* Edit Version Metadata */}
                              <button
                                onClick={() => openEditVersionModal(v)}
                                className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded"
                                title="Edit Mutable Metadata (Changelog / Dates)"
                              >
                                <Edit className="h-3.5 w-3.5" />
                              </button>
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
        )}

        {/* TAB 4: LIFECYCLE STATE MACHINE */}
        {activeTab === "lifecycle" && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-6">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase">
                Policy Lifecycle State Engine
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                M08.4 Authoritative State Machine transitions and audit logging
              </p>
            </div>

            {/* Visual State Pipeline */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono">
                {["DRAFT", "PUBLISHED", "ACTIVE", "SUPERSEDED", "ARCHIVED"].map((step, idx) => {
                  const isCurrent = policy.status === step;
                  return (
                    <React.Fragment key={step}>
                      <div className={`flex items-center gap-2 p-2.5 rounded-lg border w-full sm:w-auto justify-center ${
                        isCurrent
                          ? "bg-amber-400 text-slate-950 border-amber-500 font-bold shadow-xs"
                          : "bg-white text-slate-600 border-slate-200 font-medium"
                      }`}>
                        <span className={`w-2 h-2 rounded-full ${isCurrent ? "bg-slate-950" : "bg-slate-300"}`} />
                        <span>{step}</span>
                      </div>
                      {idx < 4 && (
                        <ArrowRight className="h-4 w-4 text-slate-300 hidden sm:block shrink-0" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>

            {/* State Explanatory Rules */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <h4 className="font-bold text-slate-800 uppercase font-mono text-[11px]">
                  Current Status: {policy.status}
                </h4>
                <p className="text-slate-600 leading-relaxed">
                  {policy.status === "DRAFT" && "This policy is in draft mode. Metadata is editable, and source document versions can be uploaded. To proceed, publish this policy."}
                  {policy.status === "PUBLISHED" && "This policy is published and locked. A validated source document exists. To enter regulatory force, activate the policy with an effective date."}
                  {policy.status === "ACTIVE" && "This policy is actively in force and referenced by compliance checks. To update the underlying rules, upload a new version and supersede."}
                  {policy.status === "SUPERSEDED" && "This policy has been superseded by a newer version. It remains preserved for historical audit and compliance review."}
                  {policy.status === "ARCHIVED" && "This policy has reached terminal archive state. It cannot be edited or reactivated."}
                </p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                <h4 className="font-bold text-slate-800 uppercase font-mono text-[11px]">
                  Authorized Next Transitions
                </h4>
                <ul className="list-disc pl-4 space-y-1 text-slate-600">
                  {policy.status === "DRAFT" && (
                    <>
                      <li><strong>Publish:</strong> Locks metadata and prepares version for activation.</li>
                      <li><strong>Archive:</strong> Discard draft if obsolete.</li>
                    </>
                  )}
                  {policy.status === "PUBLISHED" && (
                    <>
                      <li><strong>Activate:</strong> Designates current version as ACTIVE with effective date.</li>
                      <li><strong>Archive:</strong> Move directly to archive.</li>
                    </>
                  )}
                  {policy.status === "ACTIVE" && (
                    <>
                      <li><strong>Supersede:</strong> Replaces active version with an uploaded replacement version.</li>
                      <li><strong>Archive:</strong> Retires policy from active enforcement.</li>
                    </>
                  )}
                  {policy.status === "SUPERSEDED" && (
                    <li><strong>Archive:</strong> Move superseded historical policy into terminal archive.</li>
                  )}
                  {policy.status === "ARCHIVED" && (
                    <li className="text-slate-400 italic">No transitions available from terminal ARCHIVED state.</li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: EDIT POLICY METADATA */}
        {isEditOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <h2 className="text-sm font-bold text-slate-900 uppercase">
                  Edit Policy Metadata ({policy.policy_code})
                </h2>
                <button onClick={() => setIsEditOpen(false)} className="text-slate-400 hover:text-slate-600 p-1">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleEditSubmit} className="p-5 space-y-4">
                {editError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {editError}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Policy Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.title}
                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Category
                    </label>
                    <input
                      type="text"
                      value={editForm.category}
                      onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Policy Type
                    </label>
                    <input
                      type="text"
                      value={editForm.policy_type}
                      onChange={(e) => setEditForm({ ...editForm, policy_type: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Target Institution
                    </label>
                    <input
                      type="text"
                      value={editForm.institution}
                      onChange={(e) => setEditForm({ ...editForm, institution: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Jurisdiction
                    </label>
                    <input
                      type="text"
                      value={editForm.jurisdiction}
                      onChange={(e) => setEditForm({ ...editForm, jurisdiction: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Regulatory Authority
                  </label>
                  <select
                    value={editForm.regulatory_authority_id}
                    onChange={(e) => setEditForm({ ...editForm, regulatory_authority_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  >
                    <option value="">None / Internal Policy</option>
                    {authorities.map((a) => (
                      <option key={a.id} value={a.id}>{a.short_name} - {a.name}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsEditOpen(false)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={editSubmitting}
                    className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {editSubmitting ? "Updating..." : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: ADD APPLICABILITY RULE */}
        {isAddAppOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <h2 className="text-sm font-bold text-slate-900 uppercase">
                  Add Applicability Scope Rule
                </h2>
                <button onClick={() => setIsAddAppOpen(false)} className="text-slate-400 hover:text-slate-600 p-1">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleAddApplicability} className="p-5 space-y-3">
                {appError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {appError}
                  </div>
                )}
                <p className="text-[11px] text-slate-500">
                  Specify at least one criterion below to narrow where this policy applies:
                </p>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">Institution</label>
                  <input
                    type="text"
                    placeholder="e.g. Apex Bank"
                    value={appForm.institution}
                    onChange={(e) => setAppForm({ ...appForm, institution: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">Jurisdiction</label>
                  <input
                    type="text"
                    placeholder="e.g. IN"
                    value={appForm.jurisdiction}
                    onChange={(e) => setAppForm({ ...appForm, jurisdiction: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">Loan Type</label>
                  <input
                    type="text"
                    placeholder="e.g. HOME_LOAN, PERSONAL_LOAN"
                    value={appForm.loan_type}
                    onChange={(e) => setAppForm({ ...appForm, loan_type: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">Department</label>
                  <input
                    type="text"
                    placeholder="e.g. Credit Risk, Underwriting"
                    value={appForm.department}
                    onChange={(e) => setAppForm({ ...appForm, department: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsAddAppOpen(false)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={appSubmitting}
                    className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {appSubmitting ? "Adding..." : "Add Scope"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: DELETE APPLICABILITY CONFIRMATION */}
        {deletingAppId && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Remove Applicability Scope?
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Are you sure you want to remove this applicability rule?
                  </p>
                </div>
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDeletingAppId(null)}
                  className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteApplicability(deletingAppId)}
                  className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold"
                >
                  Delete Rule
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: UPLOAD NEW VERSION */}
        {isUploadOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <UploadCloud className="h-4 w-4 text-amber-600" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase">
                    Upload Policy Source Document
                  </h2>
                </div>
                <button onClick={() => setIsUploadOpen(false)} className="text-slate-400 hover:text-slate-600 p-1">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleUploadVersion} className="p-5 space-y-4">
                {uploadError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {uploadError}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Document File (PDF / PNG / JPG, max 10MB) *
                  </label>
                  <input
                    type="file"
                    required
                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                  {selectedFile && (
                    <div className="text-[11px] text-emerald-700 font-mono pt-1">
                      Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Version Changelog / Notes
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Summary of amendments, statutory circular references..."
                    value={uploadChangelog}
                    onChange={(e) => setUploadChangelog(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Effective From
                    </label>
                    <input
                      type="datetime-local"
                      value={uploadEffectiveFrom}
                      onChange={(e) => setUploadEffectiveFrom(e.target.value)}
                      className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Effective To
                    </label>
                    <input
                      type="datetime-local"
                      value={uploadEffectiveTo}
                      onChange={(e) => setUploadEffectiveTo(e.target.value)}
                      className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsUploadOpen(false)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={uploadSubmitting}
                    className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {uploadSubmitting ? "Ingesting Document..." : "Upload & Validate"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: EDIT VERSION METADATA */}
        {editingVersion && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <h2 className="text-sm font-bold text-slate-900 uppercase">
                  Edit Metadata (Version {editingVersion.version_number})
                </h2>
                <button onClick={() => setEditingVersion(null)} className="text-slate-400 hover:text-slate-600 p-1">
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleEditVersionSubmit} className="p-5 space-y-4">
                {vMetaError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {vMetaError}
                  </div>
                )}

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600 space-y-1">
                  <div className="flex items-center gap-1 font-bold text-slate-800">
                    <Lock className="h-3 w-3" />
                    <span>Protected Immutability Notice</span>
                  </div>
                  <p>Document binary, SHA-256 hash, and version number are permanently frozen and cannot be modified.</p>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Changelog / Notes
                  </label>
                  <textarea
                    rows={2}
                    value={vMetaForm.changelog}
                    onChange={(e) => setVMetaForm({ ...vMetaForm, changelog: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Effective From
                  </label>
                  <input
                    type="datetime-local"
                    value={vMetaForm.effective_from}
                    onChange={(e) => setVMetaForm({ ...vMetaForm, effective_from: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Effective To
                  </label>
                  <input
                    type="datetime-local"
                    value={vMetaForm.effective_to}
                    onChange={(e) => setVMetaForm({ ...vMetaForm, effective_to: e.target.value })}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setEditingVersion(null)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={vMetaSubmitting}
                    className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {vMetaSubmitting ? "Saving..." : "Save Metadata"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: PUBLISH CONFIRMATION */}
        {isPublishOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                  <Send className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Publish Policy?
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Transitioning to <span className="font-semibold text-slate-900">PUBLISHED</span> locks policy metadata from further direct editing. Note that publishing does not automatically activate enforcement until an effective date is set.
                  </p>
                </div>
                {lifecycleError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {lifecycleError}
                  </div>
                )}
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsPublishOpen(false)}
                  disabled={lifecycleSubmitting}
                  className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={lifecycleSubmitting}
                  className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {lifecycleSubmitting ? "Publishing..." : "Confirm Publish"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: ACTIVATE CONFIRMATION */}
        {isActivateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Activate Policy Version
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Select a validated version to activate. Activated policies enter immediate regulatory force.
                  </p>
                </div>

                {lifecycleError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {lifecycleError}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">
                    Select Version to Activate
                  </label>
                  <select
                    value={selectedVersionForActivation}
                    onChange={(e) => setSelectedVersionForActivation(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                  >
                    {history.map((v) => (
                      <option key={v.id} value={v.id}>
                        Version {v.version_number} ({v.page_count} pages) - {v.changelog || "No changelog"}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsActivateOpen(false)}
                  disabled={lifecycleSubmitting}
                  className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleActivate}
                  disabled={lifecycleSubmitting}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {lifecycleSubmitting ? "Activating..." : "Confirm Activation"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: SUPERSEDE CONFIRMATION */}
        {isSupersedeOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center">
                  <Layers className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Supersede Active Policy
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Select the replacement version. The current version will be archived into history, and the new version will become active.
                  </p>
                </div>

                {lifecycleError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {lifecycleError}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase text-slate-600 font-mono">
                    Replacement Version *
                  </label>
                  <select
                    value={selectedNewVersionForSupersede}
                    onChange={(e) => setSelectedNewVersionForSupersede(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                  >
                    {history
                      .filter((v) => v.id !== policy.current_version_id)
                      .map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.version_number} - {v.changelog || "Upload"}
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsSupersedeOpen(false)}
                  disabled={lifecycleSubmitting}
                  className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSupersede}
                  disabled={lifecycleSubmitting}
                  className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {lifecycleSubmitting ? "Superseding..." : "Confirm Supersede"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: ARCHIVE CONFIRMATION */}
        {isArchiveOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-stone-100 text-stone-600 flex items-center justify-center">
                  <Archive className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Archive Policy?
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Are you sure you want to archive <span className="font-semibold text-slate-900">{policy.policy_code}</span>? ARCHIVED is a terminal state. Once archived, this policy cannot be published or activated again.
                  </p>
                </div>

                {lifecycleError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {lifecycleError}
                  </div>
                )}
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsArchiveOpen(false)}
                  disabled={lifecycleSubmitting}
                  className="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleArchive}
                  disabled={lifecycleSubmitting}
                  className="px-3.5 py-1.5 bg-stone-700 hover:bg-stone-800 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {lifecycleSubmitting ? "Archiving..." : "Confirm Archive"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </AdminLayout>
  );
}
