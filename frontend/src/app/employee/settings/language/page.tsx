"use client";

import React from "react";
import Link from "next/link";
import { 
  Languages, 
  Check, 
  ArrowLeft, 
  CheckCircle2,
  Globe
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { SupportedLanguage } from "@/i18n/types";
import { cn } from "@/lib/utils";

export default function EmployeeLanguageSettingsPage() {
  const { language, setLanguage, supportedLanguages, isUpdatingLang, t } = useLanguage();

  const handleSelectLanguage = async (code: SupportedLanguage) => {
    await setLanguage(code);
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6 max-w-3xl mx-auto">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-3">
          <Link
            href="/employee/settings"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold border border-slate-700 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to System Preferences</span>
          </Link>
        </div>

        {/* Header Banner */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center">
              <Languages className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                {t("languageModal.title")}
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                {t("languageModal.subtitle")}
              </p>
            </div>
          </div>
        </div>

        {/* Language Selection Card */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
              {t("languageModal.suggestedLanguages")}
            </span>
            <span className="text-[11px] font-semibold text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded font-mono">
              6 VERNACULAR LANGUAGES ACTIVE
            </span>
          </div>

          {/* 6 Languages Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            {supportedLanguages.map((lang) => {
              const isSelected = lang.code === language;
              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => handleSelectLanguage(lang.code)}
                  disabled={isUpdatingLang}
                  className={cn(
                    "flex items-center justify-between p-4 rounded-xl border text-left transition-all",
                    isSelected
                      ? "border-amber-400/60 bg-amber-500/15 text-white ring-1 ring-amber-400/40"
                      : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700 hover:bg-slate-800/80"
                  )}
                >
                  <div className="space-y-0.5">
                    <p className="text-sm font-bold tracking-tight">
                      {lang.nativeName}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">
                      {lang.name}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {isSelected ? (
                      <span className="flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-400/20 px-2 py-0.5 rounded border border-amber-400/30">
                        <Check className="h-3.5 w-3.5" />
                        Selected
                      </span>
                    ) : (
                      <span className="text-xs text-slate-600 font-mono">
                        {lang.code.toUpperCase()}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {isUpdatingLang && (
            <p className="text-xs text-amber-400 font-mono text-center pt-2 animate-pulse">
              Persisting language preference to institutional profile...
            </p>
          )}
        </div>

        {/* Informational Box */}
        <div className="bg-[#0A1224] border border-slate-800 rounded-xl p-4 flex items-start gap-3 text-xs text-slate-400">
          <Globe className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-slate-300">Official Multilingual Banking Framework</p>
            <p className="mt-0.5 text-slate-400 leading-relaxed">
              In accordance with Indian financial accessibility mandates, the employee operational workstation translates navigation commands, status badges, and workflow directions into your chosen official language.
            </p>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
