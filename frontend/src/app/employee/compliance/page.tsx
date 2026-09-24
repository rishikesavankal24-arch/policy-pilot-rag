"use client";

import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  ShieldCheck, 
  BookOpen, 
  FileCheck, 
  CheckCircle2, 
  AlertCircle, 
  Building2, 
  Layers, 
  Shield, 
  ExternalLink,
  ClipboardList
} from "lucide-react";

export default function EmployeeCompliancePage() {
  const directives = [
    {
      code: "RBI/DOR/2024-25/112",
      title: "Master Direction – Digital Lending Guidelines (Updated 2024)",
      description: "Direct loan disbursal mandate, cooling-off/look-up period, and mandatory key fact statement (KFS) disclosures.",
      status: "COMPLIANT",
      category: "LENDING OPERATIONS"
    },
    {
      code: "RBI/FIDD/2023-24/098",
      title: "Priority Sector Lending (PSL) Targets and Classifications",
      description: "Mandatory quotas for agriculture, MSME micro-enterprises, and education credit quotas.",
      status: "MONITORED",
      category: "CREDIT ALLOCATION"
    },
    {
      code: "RBI/DBR/2023-24/074",
      title: "Master Direction – Know Your Customer (KYC) Direction",
      description: "Customer identification procedures (CIP), Central KYC Registry (CKYCR) linkage, and risk categorization.",
      status: "ACTIVE",
      category: "AML / KYC"
    },
    {
      code: "RBI/DPSS/2024-25/019",
      title: "Cyber Security Framework for Regulated Entities",
      description: "Data residency in Indian data centers, audit trail integrity, and end-to-end payload encryption.",
      status: "VERIFIED",
      category: "SECURITY & DATA"
    }
  ];

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Policy Directives & Compliance Console
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                RBI GUIDELINE REFERENCE 2024-25
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Reference banking guidelines, regulatory directives, and policy review rules
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/employee/applications"
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
            >
              <ClipboardList className="h-4 w-4" />
              <span>Application Queue & Workspaces</span>
            </Link>
          </div>
        </div>

        {/* Adaptive RAG / M10-M11 Integration Boundary */}
        <div className="p-5 bg-[#0F172A] border border-blue-900/40 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-400">
              <ShieldCheck className="h-5 w-5" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                Policy Evaluation Architecture (Module M10/M11 Boundary)
              </h2>
            </div>
            <span className="text-[10px] font-mono font-bold bg-blue-500/10 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded">
              RESERVED INTEGRATION BOUNDARY
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Automated compliance evaluation via Adaptive RAG (hybrid BM25/vector search, reranking, and automated policy cross-referencing) is scheduled for future implementation in <strong className="text-white">Module M10 & M11</strong>. Currently, all compliance checks and audit evaluations in this workspace operate under manual human officer review.
          </p>
          <div className="pt-2 flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-400">
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
              CURRENT MODE: MANUAL_OFFICER_REVIEW
            </span>
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
              AUTOMATED PIPELINE: SCHEDULED_FOR_M10
            </span>
            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800">
              STATUS: INTEGRATION_BOUNDARY_ACTIVE
            </span>
          </div>
        </div>

        {/* Regulatory Directives Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {directives.map((dir, idx) => (
            <div key={idx} className="p-5 bg-[#0F172A] border border-slate-800 rounded-xl space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded border border-amber-400/20">
                  {dir.code}
                </span>
                <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded border border-emerald-400/20">
                  {dir.status}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-100">{dir.title}</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{dir.description}</p>
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>CATEGORY: {dir.category}</span>
                <span className="text-slate-400 flex items-center gap-1">
                  Enforced <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Underwriter Statutory Checklist */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
            <BookOpen className="h-4 w-4 text-amber-400" />
            <h2 className="text-xs font-bold uppercase tracking-wider">
              Underwriter Statutory Due Diligence Checklist
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Mandatory KYC Verification</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Verify government identity card against national database prior to credit sanction.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Income & Debt-to-Income Audit</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Ensure fixed obligation to income ratio (FOIR) remains within institutional thresholds.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Conflict of Interest Clearance</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Strictly confirm that neither applicant nor close relatives are the evaluating officer.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Key Fact Statement (KFS) Issuance</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Approved offers must provide an itemized APR disclosure before customer acceptance.
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
