"use client";

import React, { useEffect, useState } from "react";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { RegulatoryAuthority } from "@/types";
import { 
  Landmark, 
  Plus, 
  RefreshCw, 
  ExternalLink, 
  Edit, 
  PowerOff, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  X,
  Search,
  Building
} from "lucide-react";

const AUTHORITY_TYPES = [
  { value: "CENTRAL_BANK", label: "Central Bank" },
  { value: "FINANCIAL_REGULATOR", label: "Financial Regulator" },
  { value: "DATA_PROTECTION", label: "Data Protection Authority" },
  { value: "GOVERNMENT_MINISTRY", label: "Government Ministry" },
  { value: "STATUTORY_BODY", label: "Statutory Body" },
];

export default function RegulatoryAuthoritiesPage() {
  const [authorities, setAuthorities] = useState<RegulatoryAuthority[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    name: "",
    short_name: "",
    authority_type: "CENTRAL_BANK",
    jurisdiction: "",
    website_url: "",
    description: "",
    is_active: true
  });

  // Edit Modal State
  const [editingAuth, setEditingAuth] = useState<RegulatoryAuthority | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    short_name: "",
    authority_type: "",
    jurisdiction: "",
    website_url: "",
    description: "",
    is_active: true
  });

  // Deactivate Modal State
  const [deactivatingAuth, setDeactivatingAuth] = useState<RegulatoryAuthority | null>(null);
  const [deactivateSubmitting, setDeactivateSubmitting] = useState(false);

  const fetchAuthorities = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (statusFilter === "ACTIVE") params.is_active = true;
      if (statusFilter === "INACTIVE") params.is_active = false;
      if (typeFilter !== "ALL") params.authority_type = typeFilter;

      const data = await adminApi.getRegulatoryAuthorities(params);
      setAuthorities(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load regulatory authorities.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuthorities();
  }, [statusFilter, typeFilter]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      if (!createForm.name.trim() || !createForm.short_name.trim()) {
        throw new Error("Name and Short Name are mandatory.");
      }
      await adminApi.createRegulatoryAuthority({
        name: createForm.name.trim(),
        short_name: createForm.short_name.trim(),
        authority_type: createForm.authority_type,
        jurisdiction: createForm.jurisdiction.trim() || undefined,
        website_url: createForm.website_url.trim() || undefined,
        description: createForm.description.trim() || undefined,
        is_active: createForm.is_active
      });

      setSuccessMessage(`Authority "${createForm.short_name.toUpperCase()}" registered successfully.`);
      setIsCreateOpen(false);
      setCreateForm({
        name: "",
        short_name: "",
        authority_type: "CENTRAL_BANK",
        jurisdiction: "",
        website_url: "",
        description: "",
        is_active: true
      });
      await fetchAuthorities();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create authority.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  const openEditModal = (auth: RegulatoryAuthority) => {
    setEditingAuth(auth);
    setEditForm({
      name: auth.name,
      short_name: auth.short_name,
      authority_type: auth.authority_type,
      jurisdiction: auth.jurisdiction || "",
      website_url: auth.website_url || "",
      description: auth.description || "",
      is_active: auth.is_active
    });
    setEditError(null);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAuth) return;
    setEditSubmitting(true);
    setEditError(null);
    try {
      await adminApi.updateRegulatoryAuthority(editingAuth.id, {
        name: editForm.name.trim(),
        short_name: editForm.short_name.trim(),
        authority_type: editForm.authority_type,
        jurisdiction: editForm.jurisdiction.trim() || undefined,
        website_url: editForm.website_url.trim() || undefined,
        description: editForm.description.trim() || undefined,
        is_active: editForm.is_active
      });

      setSuccessMessage(`Authority "${editForm.short_name.toUpperCase()}" updated successfully.`);
      setEditingAuth(null);
      await fetchAuthorities();
    } catch (err: any) {
      setEditError(err.message || "Failed to update authority.");
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivatingAuth) return;
    setDeactivateSubmitting(true);
    try {
      await adminApi.deactivateRegulatoryAuthority(deactivatingAuth.id);
      setSuccessMessage(`Authority "${deactivatingAuth.short_name}" deactivated.`);
      setDeactivatingAuth(null);
      await fetchAuthorities();
    } catch (err: any) {
      setError(err.message || "Failed to deactivate authority.");
    } finally {
      setDeactivateSubmitting(false);
    }
  };

  const filteredAuthorities = authorities.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.name.toLowerCase().includes(q) ||
      a.short_name.toLowerCase().includes(q) ||
      (a.jurisdiction && a.jurisdiction.toLowerCase().includes(q))
    );
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase">
                Regulatory Authorities
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                GOVERNANCE DIRECTORY
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Central supervisory authorities, standard-setting bodies, and government regulatory registries
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchAuthorities}
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
              <span>Register Authority</span>
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

        {/* Filter Controls */}
        <div className="bg-white p-4 border border-slate-200 rounded-xl shadow-xs space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search by name, code or jurisdiction..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-hidden focus:ring-1 focus:ring-amber-500"
              />
            </div>

            {/* Type Filter */}
            <div>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-hidden focus:ring-1 focus:ring-amber-500"
              >
                <option value="ALL">All Authority Types</option>
                {AUTHORITY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-hidden focus:ring-1 focus:ring-amber-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active Only</option>
                <option value="INACTIVE">Inactive Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Authorities Data Table */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Authority Name</th>
                  <th className="px-4 py-3">Code / Acronym</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Jurisdiction</th>
                  <th className="px-4 py-3">Official Portal</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin text-amber-500" />
                        <span>Loading regulatory authorities...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredAuthorities.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                      No regulatory authorities found.
                    </td>
                  </tr>
                ) : (
                  filteredAuthorities.map((auth) => (
                    <tr key={auth.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 font-semibold text-slate-800">
                        <div className="flex items-center gap-2">
                          <Building className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                          <span>{auth.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono font-bold text-slate-700">
                        {auth.short_name}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {auth.authority_type.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 font-mono">
                        {auth.jurisdiction || "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {auth.website_url ? (
                          <a
                            href={auth.website_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 flex items-center gap-1 inline-flex"
                          >
                            <span className="truncate max-w-[140px]">{auth.website_url}</span>
                            <ExternalLink className="h-3 w-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {auth.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                            ACTIVE
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                            INACTIVE
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openEditModal(auth)}
                            className="p-1 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded"
                            title="Edit Authority"
                          >
                            <Edit className="h-3.5 w-3.5" />
                          </button>
                          {auth.is_active && (
                            <button
                              onClick={() => setDeactivatingAuth(auth)}
                              className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                              title="Deactivate Authority"
                            >
                              <PowerOff className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal: Create Authority */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <Landmark className="h-4 w-4 text-amber-600" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase">
                    Register Regulatory Authority
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

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Full Authority Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Reserve Bank of India"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Short Name / Code *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. RBI"
                      value={createForm.short_name}
                      onChange={(e) => setCreateForm({ ...createForm, short_name: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Authority Type
                    </label>
                    <select
                      value={createForm.authority_type}
                      onChange={(e) => setCreateForm({ ...createForm, authority_type: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    >
                      {AUTHORITY_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Jurisdiction
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. IN or US"
                      value={createForm.jurisdiction}
                      onChange={(e) => setCreateForm({ ...createForm, jurisdiction: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Website URL
                    </label>
                    <input
                      type="url"
                      placeholder="https://www.rbi.org.in"
                      value={createForm.website_url}
                      onChange={(e) => setCreateForm({ ...createForm, website_url: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                    Description / Scope
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Mandate and regulatory authority scope..."
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
                    {createSubmitting ? "Registering..." : "Save Authority"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Edit Authority */}
        {editingAuth && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full overflow-hidden border border-slate-200">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <Edit className="h-4 w-4 text-slate-700" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase">
                    Edit Authority ({editingAuth.short_name})
                  </h2>
                </div>
                <button
                  onClick={() => setEditingAuth(null)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
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
                    Full Authority Name
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Short Name
                    </label>
                    <input
                      type="text"
                      required
                      value={editForm.short_name}
                      onChange={(e) => setEditForm({ ...editForm, short_name: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono uppercase focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Authority Type
                    </label>
                    <select
                      value={editForm.authority_type}
                      onChange={(e) => setEditForm({ ...editForm, authority_type: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    >
                      {AUTHORITY_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Jurisdiction
                    </label>
                    <input
                      type="text"
                      value={editForm.jurisdiction}
                      onChange={(e) => setEditForm({ ...editForm, jurisdiction: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[11px] font-bold uppercase tracking-wider text-slate-600 font-mono">
                      Website URL
                    </label>
                    <input
                      type="url"
                      value={editForm.website_url}
                      onChange={(e) => setEditForm({ ...editForm, website_url: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-amber-500 focus:outline-hidden"
                    />
                  </div>
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
                    onClick={() => setEditingAuth(null)}
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

        {/* Modal: Deactivate Confirmation */}
        {deactivatingAuth && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden border border-slate-200">
              <div className="p-5 space-y-3">
                <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Deactivate Regulatory Authority?
                  </h3>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    Are you sure you want to deactivate <span className="font-semibold text-slate-900">{deactivatingAuth.name} ({deactivatingAuth.short_name})</span>?
                    This will mark the authority as inactive across administrative directories.
                  </p>
                </div>
              </div>

              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDeactivatingAuth(null)}
                  disabled={deactivateSubmitting}
                  className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeactivate}
                  disabled={deactivateSubmitting}
                  className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {deactivateSubmitting ? "Deactivating..." : "Confirm Deactivation"}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </AdminLayout>
  );
}
