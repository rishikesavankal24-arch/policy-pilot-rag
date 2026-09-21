"use client";

import { useEffect, useState } from "react";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  Building2, 
  ShieldCheck, 
  Layers, 
  Globe, 
  FileText, 
  CheckCircle2, 
  RefreshCw 
} from "lucide-react";

interface OrgData {
  organization_name: string;
  department: string;
  division: string;
  jurisdiction: string;
  branch_code: string;
  regulatory_body: string;
  compliance_framework: string;
  portal_version: string;
  active_workforce_unit: string;
}

export default function EmployeeOrganizationPage() {
  const [org, setOrg] = useState<OrgData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchOrg = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/organization`, {
        credentials: "include"
      });
      if (res.ok) {
        const json = await res.json();
        setOrg(json);
      }
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrg();
  }, []);

  return (
    <EmployeeLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Institutional Organization & Hierarchy
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                REGULATORY NODE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Institutional entity mapping, oversight jurisdiction, and statutory branch alignment
            </p>
          </div>

          <button
            onClick={fetchOrg}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Organization Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-4 pb-6 border-b border-slate-800">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center">
              <Building2 className="h-7 w-7" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                {org?.organization_name || "State Bank Operations & Governance Division"}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {org?.department} • {org?.division}
              </p>
            </div>
          </div>

          {/* Institutional Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-xs">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Apex Regulatory Authority</span>
              <span className="font-semibold text-amber-400 mt-0.5 block">{org?.regulatory_body || "Reserve Bank of India (RBI)"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Branch & Node Identifier</span>
              <span className="font-mono font-semibold text-slate-200 mt-0.5 block">{org?.branch_code || "DL-014 (Central Operations)"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Territorial Jurisdiction</span>
              <span className="font-semibold text-slate-200 mt-0.5 block">{org?.jurisdiction || "National Banking Sector (India)"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Active Workforce Unit</span>
              <span className="font-semibold text-slate-200 mt-0.5 block">{org?.active_workforce_unit || "Underwriting Desk A"}</span>
            </div>

            <div className="col-span-1 sm:col-span-2">
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Statutory Compliance Framework</span>
              <span className="text-slate-300 mt-0.5 block font-mono text-[11px]">
                {org?.compliance_framework || "Master Directions - Priority Sector Lending & Digital Lending Guidelines 2024-25"}
              </span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Platform Release Core</span>
              <span className="font-mono text-slate-400 mt-0.5 block">{org?.portal_version || "PolicyPilot Enterprise Core v1.4"}</span>
            </div>
          </div>
        </div>

        {/* Governance Certificate Banner */}
        <div className="p-4 bg-[#0A1224] border border-slate-800 rounded-xl flex items-center gap-3 text-xs text-slate-400">
          <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0" />
          <span>
            Institutional node verified under National Banking Governance Registry. Active operational parameters synced.
          </span>
        </div>

      </div>
    </EmployeeLayout>
  );
}
