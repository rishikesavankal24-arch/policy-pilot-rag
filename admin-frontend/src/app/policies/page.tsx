"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { Policy, RegulatoryAuthority, PolicyStatus } from "@/types";
import { PolicyStatusBadge } from "@/components/policies/PolicyStatusBadge";
import { 
  BookOpen, 
  Plus, 
  RefreshCw, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight, 
  ArrowRight, 
  FileText, 
  Building2, 
  AlertTriangle, 
  CheckCircle2, 
  X,
  Scale
} from "lucide-react";

const CATEGORIES = [
  "LENDING",
  "MORTGAGE",
  "CREDIT",
  "KYC_AML",
  "RISK_MANAGEMENT",
  "OPERATIONS",
  "COMPLIANCE",
  "CONSUMER_PROTECTION"
];

const POLICY_TYPES = [
  "REGULATORY",
  "STATUTORY",
  "INTERNAL",
  "BOARD_APPROVED",
  "OPERATIONAL_GUIDELINE"
];

export default function PoliciesListPage() {
  const router = useRouter();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [authorities, setAuthorities] = useState<RegulatoryAuthority[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Pagination & Filtering State
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [authorityFilter, setAuthorityFilter] = useState<string>("ALL");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Create Policy Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    policy_code: "",
    title: "",
    description: "",
    category: "LENDING",
    policy_type: "REGULATORY",
    institution: "",
    jurisdiction: "IN",
    regulatory_authority_id: ""
  });

  const fetchAuthorities = async () => {
    try {
      const data = await adminApi.getRegulatoryAuthorities({ is_active: true });
      setAuthorities(data || []);
    } catch {
      // Non-blocking fallback
    }
  };

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {
        page,
        page_size: pageSize
      };
      if (statusFilter !== "ALL") params.status = statusFilter;
      if (categoryFilter !== "ALL") params.category = categoryFilter;
      if (typeFilter !== "ALL") params.policy_type = typeFilter;
      if (authorityFilter !== "ALL") params.regulatory_authority_id = authorityFilter;
      if (search.trim()) params.search = search.trim();

      const res = await adminApi.getPolicies(params);
      setPolicies(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err: any) {
      setError(err.message || "Failed to load policies from supervisory database.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuthorities();
  }, []);

  useEffect(() => {
    fetchPolicies();
  }, [page, pageSize, statusFilter, categoryFilter, typeFilter, authorityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchPolicies();
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      if (!createForm.policy_code.trim() || !createForm.title.trim()) {
        throw new Error("Policy Code and Title are mandatory.");
      }

      const created = await adminApi.createPolicy({
        policy_code: createForm.policy_code.trim().toUpperCase(),
        title: createForm.title.trim(),
        description: createForm.description.trim() || undefined,
        category: createForm.category || undefined,
        policy_type: createForm.policy_type || undefined,
        institution: createForm.institution.trim() || undefined,
        jurisdiction: createForm.jurisdiction.trim() || undefined,
        regulatory_authority_id: createForm.regulatory_authority_id || undefined
      });

      setIsCreateOpen(false);
      setSuccessMessage(`Policy ${created.policy_code} successfully registered in DRAFT state.`);
      router.push(`/policies/${created.id}`);
    } catch (err: any) {
      setCreateError(err.message || "Failed to register policy.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                Policies & Regulations
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                POLICY REPOSITORY
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Master repository of institutional credit policies, statutory circulars, and regulatory mandates
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => { setPage(1); fetchPolicies(); }}
              disabled={loading}
              className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Create Policy</span>
            </button>
          </div>
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

        {/* Filter Controls Panel */}
        <div className="bg-white p-4 border border-slate-200 rounded-xl shadow-xs space-y-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search by policy code, title, keywords..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold"
            >
              Search
            </button>
          </form>

          {/* Filter Dropdowns Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-100 text-xs">
            {/* Status Filter */}
            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block mb-1">
                Lifecycle Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs"
              >
                <option value="ALL">All Statuses</option>
                <option value="DRAFT">DRAFT</option>
                <option value="PUBLISHED">PUBLISHED</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="SUPERSEDED">SUPERSEDED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>

            {/* Category Filter */}
            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block mb-1">
                Domain Category
              </label>
              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs"
              >
                <option value="ALL">All Categories</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>

            {/* Policy Type Filter */}
            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block mb-1">
                Policy Type
              </label>
              <select
                value={typeFilter}
                onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs"
              >
                <option value="ALL">All Policy Types</option>
                {POLICY_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>

            {/* Regulatory Authority Filter */}
            <div>
              <label className="text-[10px] font-bold uppercase text-slate-400 font-mono block mb-1">
                Authority
              </label>
              <select
                value={authorityFilter}
                onChange={(e) => { setAuthorityFilter(e.target.value); setPage(1); }}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs"
              >
                <option value="ALL">All Authorities</option>
                {authorities.map((a) => (
                  <option key={a.id} value={a.id}>{a.short_name} - {a.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Policies Table */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Policy Code</th>
                  <th className="px-4 py-3">Title & Category</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Institution / Jurisdiction</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Current Version</th>
                  <th className="px-4 py-3">Last Updated</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <RefreshCw className="h-5 w-5 animate-spin text-amber-500" />
                        <span className="font-mono text-xs">Querying supervisory policy registry...</span>
                      </div>
                    </td>
                  </tr>
                ) : policies.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-1">
                        <FileText className="h-6 w-6 text-slate-300" />
                        <span className="font-semibold text-slate-600 text-sm">No policies found.</span>
                        <span className="text-xs text-slate-400">Try adjusting your filters or search terms.</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  policies.map((policy) => {
                    const authority = authorities.find((a) => a.id === policy.regulatory_authority_id);
                    return (
                      <tr key={policy.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 font-mono font-bold text-slate-900">
                          <Link
                            href={`/policies/${policy.id}`}
                            className="hover:text-amber-700 hover:underline"
                          >
                            {policy.policy_code}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-0.5">
                            <span className="font-semibold text-slate-800 line-clamp-1">{policy.title}</span>
                            <div className="flex items-center gap-1.5">
                              {policy.category && (
                                <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                                  {policy.category}
                                </span>
                              )}
                              {authority && (
                                <span className="text-[10px] font-mono text-amber-800 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200">
                                  {authority.short_name}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">
                          {policy.policy_type || "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          <div className="flex flex-col text-[11px]">
                            <span className="font-medium text-slate-700">{policy.institution || "All Institutions"}</span>
                            <span className="text-slate-400 font-mono text-[10px]">{policy.jurisdiction || "Global"}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <PolicyStatusBadge status={policy.status} />
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600">
                          {policy.current_version_id ? (
                            <span className="text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                              Linked
                            </span>
                          ) : (
                            <span className="text-slate-400">None</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">
                          {policy.updated_at ? new Date(policy.updated_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link
                            href={`/policies/${policy.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold transition-colors"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="h-3 w-3" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
            <div>
              Showing <span className="font-bold text-slate-800">{policies.length}</span> of{" "}
              <span className="font-bold text-slate-800">{total}</span> policies
              {totalPages > 1 && ` (Page ${page} of ${totalPages})`}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="px-2.5 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40 font-semibold flex items-center gap-1"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>Previous</span>
              </button>

              <span className="px-2 font-mono font-bold text-slate-700">
                {page} / {totalPages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="px-2.5 py-1 bg-white border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40 font-semibold flex items-center gap-1"
              >
                <span>Next</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Modal: Create Policy */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-amber-600" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase">
                    Register New Policy (DRAFT)
                  </h2>
                </div>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="p-5 space-y-4">
                {createError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs">
                    {createError}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Policy Code *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. POL-LEND-2026"
                      value={createForm.policy_code}
                      onChange={(e) => setCreateForm({ ...createForm, policy_code: e.target.value.toUpperCase() })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Category
                    </label>
                    <select
                      value={createForm.category}
                      onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Policy Title *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Master Direction on Digital Lending Operations"
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Policy Type
                    </label>
                    <select
                      value={createForm.policy_type}
                      onChange={(e) => setCreateForm({ ...createForm, policy_type: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    >
                      {POLICY_TYPES.map((t) => (
                        <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Regulatory Authority
                    </label>
                    <select
                      value={createForm.regulatory_authority_id}
                      onChange={(e) => setCreateForm({ ...createForm, regulatory_authority_id: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    >
                      <option value="">None / Internal Policy</option>
                      {authorities.map((a) => (
                        <option key={a.id} value={a.id}>{a.short_name} - {a.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Target Institution
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Apex Bank"
                      value={createForm.institution}
                      onChange={(e) => setCreateForm({ ...createForm, institution: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Jurisdiction
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. IN"
                      value={createForm.jurisdiction}
                      onChange={(e) => setCreateForm({ ...createForm, jurisdiction: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Executive Summary / Description
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Scope, regulatory purpose, and operational mandates..."
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createSubmitting}
                    className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-xs font-bold disabled:opacity-50"
                  >
                    {createSubmitting ? "Creating..." : "Create Policy"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </AdminLayout>
  );
}
