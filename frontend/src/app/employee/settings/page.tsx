"use client";

import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  Settings, 
  Languages, 
  ShieldCheck, 
  Lock, 
  Bell, 
  Monitor, 
  CheckCircle2, 
  ChevronRight 
} from "lucide-react";

export default function EmployeeSettingsPage() {
  const { t, languageInfo } = useLanguage();

  return (
    <EmployeeLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white uppercase">
              Officer Console Preferences
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
              OPERATIONAL CONFIG
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Display language, security session policies, and underwriter workstation parameters
          </p>
        </div>

        {/* Navigation to Language */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Regional & Localization Settings
          </h2>

          <Link
            href="/employee/settings/language"
            className="flex items-center justify-between p-3.5 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg transition-colors group"
          >
            <div className="flex items-center gap-3">
              <Languages className="h-5 w-5 text-amber-400" />
              <div>
                <p className="text-xs font-bold text-slate-200">Display Language</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Select your preferred vernacular language for the operational console
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-amber-400 bg-amber-400/10 px-2.5 py-1 rounded border border-amber-400/20">
                {languageInfo.nativeName} ({languageInfo.name})
              </span>
              <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-white transition-colors" />
            </div>
          </Link>
        </div>

        {/* Security & Session Parameters */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-5 shadow-sm space-y-4 text-xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Institutional Session Security
          </h2>

          <div className="space-y-3">
            <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-200">Idle Session Timeout</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Automatic workstation lock after 15 minutes of inactivity (Mandatory RBI mandate)
                </p>
              </div>
              <span className="font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                15 MIN ENFORCED
              </span>
            </div>

            <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-200">Two-Factor Re-authentication</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Required when accessing sensitive KYC documents or approving high-value facilities
                </p>
              </div>
              <span className="font-mono text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                ACTIVE
              </span>
            </div>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
