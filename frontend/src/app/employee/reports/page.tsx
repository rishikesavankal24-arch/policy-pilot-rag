"use client";

import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  BarChart3, 
  TrendingUp, 
  FileText, 
  ShieldCheck, 
  Download, 
  Calendar, 
  Clock, 
  CheckCircle2, 
  Layers 
} from "lucide-react";

export default function EmployeeReportsPage() {
  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Operational & Audit Reports
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                AUDIT ARCHIVE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Underwriting throughput, turnaround metrics, and statutory audit records
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Export Audit Summary</span>
            </button>
          </div>
        </div>

        {/* Executive Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Average TAT</span>
            <p className="text-2xl font-bold text-white mt-1">2.4 Days</p>
            <p className="text-[11px] text-emerald-400 mt-0.5">Within 3-day statutory target</p>
          </div>

          <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Sanction Rate</span>
            <p className="text-2xl font-bold text-emerald-300 mt-1">78.5%</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Based on qualified credit profiles</p>
          </div>

          <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">KYC First-Pass</span>
            <p className="text-2xl font-bold text-amber-300 mt-1">91.2%</p>
            <p className="text-[11px] text-slate-500 mt-0.5">Accurate documentation submitted</p>
          </div>

          <div className="p-4 bg-[#0F172A] border border-slate-800 rounded-xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Audit Compliance</span>
            <p className="text-2xl font-bold text-blue-300 mt-1">100%</p>
            <p className="text-[11px] text-blue-400 mt-0.5">Zero unlogged supervisor actions</p>
          </div>
        </div>

        {/* Regulatory Audit Trail Certification */}
        <div className="p-5 bg-[#0F172A] border border-slate-800 rounded-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800 text-slate-200">
            <ShieldCheck className="h-5 w-5 text-amber-400" />
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider">
                Statutory Non-Repudiation Audit Certification
              </h2>
              <p className="text-[11px] text-slate-400">Indian Evidence Act Section 65B Electronic Record Compliance</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Cryptographic Hashes</span>
              <p className="font-semibold text-slate-200">SHA-256 Audit Signing</p>
              <p className="text-[11px] text-slate-500">All queue modifications signed with UTC timestamp</p>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Data Retention</span>
              <p className="font-semibold text-slate-200">8 Years Statutory</p>
              <p className="text-[11px] text-slate-500">Stored in encrypted primary Indian bank vault</p>
            </div>

            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
              <span className="text-[10px] font-mono text-slate-400 uppercase">Inspection Logs</span>
              <p className="font-semibold text-emerald-400">Continuous Logging</p>
              <p className="text-[11px] text-slate-500">Officer session IDs mapped to every case query</p>
            </div>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
