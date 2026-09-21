"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  ClipboardList, 
  ArrowRight, 
  CheckCircle2, 
  Info, 
  Shield, 
  RefreshCw, 
  Building2 
} from "lucide-react";

interface AssignmentsResponse {
  assigned_applications: any[];
  queue_type: string;
  message: string;
}

export default function EmployeeAssignmentsPage() {
  const [data, setData] = useState<AssignmentsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAssignments = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/assignments`, {
        credentials: "include"
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch {
      // Handled
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
  }, []);

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Officer Assignment Allocation
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                ACTIVE QUEUE MODEL
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Directly assigned loan dossiers and underwriting desk allocations
            </p>
          </div>

          <button
            onClick={fetchAssignments}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Allocations</span>
          </button>
        </div>

        {/* Operational Allocation Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-8 shadow-sm space-y-6 text-center max-w-3xl mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center mx-auto">
            <ClipboardList className="h-7 w-7" />
          </div>

          <div className="space-y-2">
            <h2 className="text-base font-bold text-white uppercase tracking-wide">
              Shared Institutional Underwriting Queue Active
            </h2>
            <p className="text-xs text-slate-300 max-w-lg mx-auto leading-relaxed">
              {data?.message || "All applications are currently processed from the centralized operational pool. Individual underwriter assignment dispatches are not allocated."}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg mx-auto text-left">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs space-y-1">
              <span className="text-[10px] font-mono uppercase text-slate-400">Queue Model</span>
              <p className="font-semibold text-white">Centralized Institutional Queue</p>
            </div>
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg text-xs space-y-1">
              <span className="text-[10px] font-mono uppercase text-slate-400">Direct Assignments</span>
              <p className="font-semibold text-amber-400">0 Individual Tickets</p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/employee/applications"
              className="w-full sm:w-auto px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs flex items-center justify-center gap-2 transition-colors shadow-sm"
            >
              <span>Access Shared Operational Queue</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Operating Protocol Note */}
        <div className="p-4 bg-[#0A1224] border border-slate-800 rounded-xl text-slate-400 text-xs flex items-center gap-3 max-w-3xl mx-auto">
          <Info className="h-4 w-4 text-amber-400 shrink-0" />
          <span>
            Under the centralized model, verified officers inspect and process cases based on priority, loan type, and submission date from the shared application queue.
          </span>
        </div>

      </div>
    </EmployeeLayout>
  );
}
