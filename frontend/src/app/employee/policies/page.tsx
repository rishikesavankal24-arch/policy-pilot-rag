"use client";

import React, { useState, useEffect, useCallback, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { 
  BookOpen, 
  Search, 
  Filter, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  ChevronRight, 
  Building2, 
  Calendar, 
  FileText, 
  ShieldCheck, 
  ArrowUpDown,
  ExternalLink,
  SlidersHorizontal,
  X
} from "lucide-react";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  fetchEmployeePolicies, 
  EmployeePolicyListItem, 
  PolicyFilterParams 
} from "@/lib/employeePolicyApi";

export default function EmployeePolicyCatalogPage() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  // Search & Filter state
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [policyTypeFilter, setPolicyTypeFilter] = useState("ALL");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("ALL");
  const [loanTypeFilter, setLoanTypeFilter] = useState("ALL");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  
  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Data state
  const [policies, setPolicies] = useState<EmployeePolicyListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1); // Reset to page 1 on new search
    }, 350);
    return () => clearTimeout(handler);
  }, [searchInput]);

  // Load policies
  const loadPolicies = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params: PolicyFilterParams = {
        search: debouncedSearch,
        category: categoryFilter,
        policy_type: policyTypeFilter,
        jurisdiction: jurisdictionFilter,
        loan_type: loanTypeFilter,
        department: departmentFilter,
        page,
        page_size: pageSize
      };

      const res = await fetchEmployeePolicies(params);
      setPolicies(res.items || []);
      setTotalCount(res.total || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load policy catalog.");
    } finally {
      setIsLoading(false);
    }
  }, [debouncedSearch, categoryFilter, policyTypeFilter, jurisdictionFilter, loanTypeFilter, departmentFilter, page]);

  useEffect(() => {
    loadPolicies();
  }, [loadPolicies]);

  // Reset all filters
  const handleResetFilters = () => {
    setSearchInput("");
    setCategoryFilter("ALL");
    setPolicyTypeFilter("ALL");
    setJurisdictionFilter("ALL");
    setLoanTypeFilter("ALL");
    setDepartmentFilter("ALL");
    setPage(1);
  };

  const hasActiveFilters = 
    searchInput.trim() !== "" || 
    categoryFilter !== "ALL" || 
    policyTypeFilter !== "ALL" || 
    jurisdictionFilter !== "ALL" || 
    loanTypeFilter !== "ALL" || 
    departmentFilter !== "ALL";

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  // Formatting helpers
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

  const getCategoryBadgeClass = (category: string) => {
    switch (category?.toUpperCase()) {
      case "LENDING":
      case "CREDIT":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "REGULATORY":
      case "STATUTORY":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "AML_KYC":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "RISK":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "OPERATIONAL":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/30";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6 max-w-7xl mx-auto">
        
        {/* Header Strip */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <BookOpen className="h-4 w-4" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Policy Catalog
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                ACTIVE REPOSITORY
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              Verified institutional repository of active credit policies, underwriting standards, statutory directives, and regulatory frameworks.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={() => loadPolicies()}
              disabled={isLoading}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-amber-400" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Security & Access Boundary Banner */}
        <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs text-slate-300">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Verified Employee Workspace:</strong> All documents displayed represent the current <strong>ACTIVE</strong> versions authorized for institutional compliance and underwriting review.
            </span>
          </div>
          <span className="hidden sm:inline-block text-[10px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
            READ-ONLY CATALOG
          </span>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-4 space-y-4 shadow-sm">
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              id="employee-policy-search-input"
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search active policies by code, title, or keywords (e.g., POL-RETAIL, Master Direction, KYC)..."
              className="w-full pl-10 pr-10 py-2.5 bg-slate-900/90 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-400/40 focus:border-amber-400/60 transition-all font-sans"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-200 rounded"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Filter Dropdowns Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
            
            {/* Category Filter */}
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
                Category
              </label>
              <select
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
              >
                <option value="ALL">All Categories</option>
                <option value="LENDING">Lending</option>
                <option value="CREDIT">Credit</option>
                <option value="REGULATORY">Regulatory</option>
                <option value="RISK">Risk Management</option>
                <option value="AML_KYC">AML / KYC</option>
                <option value="OPERATIONAL">Operational</option>
                <option value="GENERAL">General</option>
              </select>
            </div>

            {/* Policy Type Filter */}
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
                Policy Type
              </label>
              <select
                value={policyTypeFilter}
                onChange={(e) => {
                  setPolicyTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
              >
                <option value="ALL">All Types</option>
                <option value="INTERNAL_DIRECTIVE">Internal Directive</option>
                <option value="STATUTORY_REGULATION">Statutory Regulation</option>
                <option value="CREDIT_FRAMEWORK">Credit Framework</option>
                <option value="OPERATIONAL_GUIDELINE">Operational Guideline</option>
                <option value="CIRCULAR">Circular</option>
                <option value="MASTER_DIRECTION">Master Direction</option>
              </select>
            </div>

            {/* Jurisdiction Filter */}
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
                Jurisdiction
              </label>
              <select
                value={jurisdictionFilter}
                onChange={(e) => {
                  setJurisdictionFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
              >
                <option value="ALL">All Jurisdictions</option>
                <option value="NATIONAL">National / India</option>
                <option value="STATE">State Level</option>
                <option value="GLOBAL">Global</option>
              </select>
            </div>

            {/* Loan Type Filter */}
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
                Loan Product
              </label>
              <select
                value={loanTypeFilter}
                onChange={(e) => {
                  setLoanTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
              >
                <option value="ALL">All Products</option>
                <option value="HOME_LOAN">Home Loan</option>
                <option value="PERSONAL_LOAN">Personal Loan</option>
                <option value="VEHICLE_LOAN">Vehicle Loan</option>
                <option value="EDUCATION_LOAN">Education Loan</option>
                <option value="BUSINESS_LOAN">Business Loan</option>
              </select>
            </div>

            {/* Department Filter */}
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 font-mono">
                Department
              </label>
              <select
                value={departmentFilter}
                onChange={(e) => {
                  setDepartmentFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-400"
              >
                <option value="ALL">All Departments</option>
                <option value="UNDERWRITING">Underwriting</option>
                <option value="RISK">Risk Management</option>
                <option value="COMPLIANCE">Compliance</option>
                <option value="LEGAL">Legal</option>
                <option value="OPERATIONS">Operations</option>
              </select>
            </div>

            {/* Reset Action */}
            <div className="flex items-end">
              <button
                onClick={handleResetFilters}
                disabled={!hasActiveFilters}
                className={`w-full py-1.5 px-3 rounded-lg text-xs font-medium border flex items-center justify-center gap-1.5 transition-colors ${
                  hasActiveFilters
                    ? "bg-slate-800 hover:bg-slate-700 text-amber-300 border-slate-700"
                    : "bg-slate-900 text-slate-600 border-slate-800 cursor-not-allowed"
                }`}
              >
                <SlidersHorizontal className="h-3 w-3" />
                <span>Reset Filters</span>
              </button>
            </div>

          </div>

        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-4 bg-rose-950/70 border border-rose-600/40 rounded-xl flex items-center gap-3 text-rose-200 text-xs">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-rose-100">Catalog Access Error</p>
              <p className="text-rose-300 mt-0.5">{error}</p>
            </div>
            <button
              onClick={() => loadPolicies()}
              className="px-2.5 py-1 bg-rose-900/60 hover:bg-rose-800 text-white rounded text-[11px] font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* Policies Table View */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#070D1E] border-b border-slate-800 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">Policy Code</th>
                  <th className="py-3 px-4 font-semibold">Title & Framework</th>
                  <th className="py-3 px-4 font-semibold">Category</th>
                  <th className="py-3 px-4 font-semibold">Type</th>
                  <th className="py-3 px-4 font-semibold">Authority</th>
                  <th className="py-3 px-4 font-semibold">Jurisdiction</th>
                  <th className="py-3 px-4 font-semibold text-center">Version</th>
                  <th className="py-3 px-4 font-semibold">Effective Period</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-24"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-48"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-20"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-24"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-16"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-20"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-12 mx-auto"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-24"></div></td>
                      <td className="py-4 px-4"><div className="h-4 bg-slate-800 rounded w-16 ml-auto"></div></td>
                    </tr>
                  ))
                ) : policies.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-12 px-4 text-center">
                      <div className="flex flex-col items-center justify-center max-w-sm mx-auto space-y-2">
                        <BookOpen className="h-10 w-10 text-slate-600 mb-1" />
                        <p className="text-sm font-semibold text-slate-200">No active policies found</p>
                        <p className="text-xs text-slate-400">
                          {hasActiveFilters 
                            ? "Try adjusting your search query or relaxing filter criteria."
                            : "There are currently no active policies published in the employee repository."}
                        </p>
                        {hasActiveFilters && (
                          <button
                            onClick={handleResetFilters}
                            className="mt-3 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg text-xs font-medium border border-slate-700"
                          >
                            Clear All Filters
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  policies.map((p) => (
                    <tr
                      key={p.id}
                      className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                      onClick={() => router.push(`/employee/policies/${p.id}`)}
                    >
                      {/* Code */}
                      <td className="py-3 px-4 font-mono font-bold text-amber-400 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span>{p.policy_code}</span>
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Active Policy"></span>
                        </div>
                      </td>

                      {/* Title & Description */}
                      <td className="py-3 px-4 max-w-xs">
                        <p className="font-semibold text-slate-100 group-hover:text-amber-300 transition-colors truncate">
                          {p.title}
                        </p>
                        {p.description && (
                          <p className="text-[11px] text-slate-400 truncate mt-0.5">
                            {p.description}
                          </p>
                        )}
                      </td>

                      {/* Category */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border uppercase ${getCategoryBadgeClass(p.category)}`}>
                          {p.category}
                        </span>
                      </td>

                      {/* Type */}
                      <td className="py-3 px-4 text-slate-300 whitespace-nowrap font-mono text-[11px]">
                        {p.policy_type?.replace(/_/g, " ")}
                      </td>

                      {/* Regulatory Authority */}
                      <td className="py-3 px-4 text-slate-200 whitespace-nowrap">
                        {p.regulatory_authority ? (
                          <div className="flex items-center gap-1" title={p.regulatory_authority.name}>
                            <Building2 className="h-3 w-3 text-slate-400" />
                            <span className="font-semibold">{p.regulatory_authority.code}</span>
                          </div>
                        ) : (
                          <span className="text-slate-500 font-mono text-[11px]">INTERNAL</span>
                        )}
                      </td>

                      {/* Jurisdiction */}
                      <td className="py-3 px-4 text-slate-300 whitespace-nowrap font-mono text-[11px]">
                        {p.jurisdiction}
                      </td>

                      {/* Current Version */}
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700 font-mono font-semibold text-[11px]">
                          v{p.current_version_number ?? "1.0"}
                        </span>
                      </td>

                      {/* Effective Period */}
                      <td className="py-3 px-4 whitespace-nowrap text-[11px] text-slate-400 font-mono">
                        <div>
                          <span>From: {formatDate(p.effective_from)}</span>
                          {p.effective_to && (
                            <span className="block text-slate-500">To: {formatDate(p.effective_to)}</span>
                          )}
                        </div>
                      </td>

                      {/* Action */}
                      <td className="py-3 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={`/employee/policies/${p.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 rounded text-[11px] font-medium border border-slate-700 hover:border-amber-400/40 transition-colors"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Table Footer with Pagination */}
          <div className="p-3 bg-[#070D1E] border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
            <div>
              Showing <span className="font-semibold text-slate-200">{policies.length}</span> of{" "}
              <span className="font-semibold text-slate-200">{totalCount}</span> active policies
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || isLoading}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 text-slate-200 rounded text-xs font-medium border border-slate-700 transition-colors"
              >
                Previous
              </button>
              
              <span className="px-2 font-mono text-[11px]">
                Page {page} of {totalPages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || isLoading}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 text-slate-200 rounded text-xs font-medium border border-slate-700 transition-colors"
              >
                Next
              </button>
            </div>
          </div>

        </div>

      </div>
    </EmployeeLayout>
  );
}
