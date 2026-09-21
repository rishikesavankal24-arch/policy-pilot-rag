"use client";

import { useEffect, useState } from "react";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  User, 
  Building2, 
  ShieldCheck, 
  Mail, 
  Briefcase, 
  Calendar, 
  CheckCircle2, 
  RefreshCw 
} from "lucide-react";

interface EmployeeProfileData {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  onboarding_status: string;
  language: string;
  organization: string;
  department: string;
  designation: string;
  employee_id: string;
  work_email: string;
  verified_at: string | null;
}

export default function EmployeeProfilePage() {
  const [profile, setProfile] = useState<EmployeeProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/profile`, {
        credentials: "include"
      });
      if (res.ok) {
        const json = await res.json();
        setProfile(json);
      }
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  return (
    <EmployeeLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Officer Credential Profile
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                VERIFIED OFFICER
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Institutional credentials, departmental authority, and verified personnel identity
            </p>
          </div>

          <button
            onClick={fetchProfile}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Profile Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4 pb-6 border-b border-slate-800">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-700/20 border border-amber-500/40 text-amber-300 font-bold flex items-center justify-center text-xl shadow-inner">
              <User className="h-8 w-8 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg font-bold text-white">{profile?.full_name || "Authorized Officer"}</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-400/10 text-emerald-400 border border-emerald-400/30 uppercase">
                  {profile?.onboarding_status || "COMPLETED"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                {profile?.designation} • {profile?.department}
              </p>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-xs">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Institutional Organization</span>
              <span className="font-semibold text-slate-200 mt-0.5 block">{profile?.organization || "Central Operations"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Department Division</span>
              <span className="font-semibold text-slate-200 mt-0.5 block">{profile?.department || "Credit Operations"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Employee Personnel ID</span>
              <span className="font-mono font-semibold text-amber-400 mt-0.5 block">{profile?.employee_id || "EMP-VERIFIED"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">System Operational Role</span>
              <span className="font-mono font-semibold text-slate-200 mt-0.5 block">ROLE_EMPLOYEE (UNDERWRITER)</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Official Work Email</span>
              <span className="font-mono text-slate-300 mt-0.5 block">{profile?.work_email || profile?.email}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">System Primary Email</span>
              <span className="font-mono text-slate-300 mt-0.5 block">{profile?.email}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Console Display Language</span>
              <span className="text-slate-300 mt-0.5 block">{profile?.language || "English"}</span>
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Supervisory Approval Date</span>
              <span className="text-slate-300 font-mono mt-0.5 block">
                {profile?.verified_at ? new Date(profile.verified_at).toLocaleDateString() : "Verified on Account Ingestion"}
              </span>
            </div>
          </div>
        </div>

        {/* Security Clearance Notice */}
        <div className="p-4 bg-[#0A1224] border border-slate-800 rounded-xl flex items-center gap-3 text-xs text-slate-400">
          <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0" />
          <span>
            <strong>Level 2 Operations Clearance:</strong> Authorized for credit dossier review, applicant evidence inspection, and regulatory compliance verification under institutional oversight.
          </span>
        </div>

      </div>
    </EmployeeLayout>
  );
}
