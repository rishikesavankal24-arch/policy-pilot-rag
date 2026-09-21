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
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { SupportedLanguage } from "@/i18n/types";
import { cn } from "@/lib/utils";

export default function LanguageSettingsPage() {
  const { language, setLanguage, supportedLanguages, isUpdatingLang, t } = useLanguage();

  const handleSelectLanguage = async (code: SupportedLanguage) => {
    await setLanguage(code);
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
            <Languages className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {t("languageModal.title")}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {t("languageModal.subtitle")}
            </p>
          </div>
        </div>
      </div>

      {/* Language Selection Card */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            {t("languageModal.suggestedLanguages")}
          </span>
          <span className="text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
            {t("languageModal.supportedNotice")}
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
                  "flex items-center justify-between p-4 rounded-lg border text-left transition-all",
                  isSelected
                    ? "bg-blue-50/90 border-blue-600 ring-2 ring-blue-600 shadow-sm"
                    : "border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-800"
                )}
              >
                <div className="flex flex-col">
                  <span className={cn(
                    "text-base leading-tight",
                    isSelected ? "font-bold text-slate-900" : "font-medium text-slate-800"
                  )}>
                    {lang.nativeName}
                  </span>
                  <span className="text-xs text-slate-500 mt-0.5">
                    {lang.name} ({lang.code.toUpperCase()})
                  </span>
                </div>

                {isSelected ? (
                  <div className="h-6 w-6 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                    <Check className="h-3.5 w-3.5 stroke-[3]" />
                  </div>
                ) : (
                  <div className="h-6 w-6 rounded-full border border-slate-200 shrink-0" />
                )}
              </button>
            );
          })}
        </div>

        {/* Informational Note */}
        <div className="mt-4 p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 text-xs leading-relaxed flex items-start gap-2">
          <Globe className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
          <p>
            <span className="font-semibold text-slate-800">PolicyPilot: </span>
            {t("languageModal.note")}
          </p>
        </div>
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-2">
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>{t("common.back")} to {t("settingsPage.title")}</span>
        </Link>
        <Link
          href="/dashboard"
          className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
        >
          {t("common.back")} to {t("nav.dashboard")} →
        </Link>
      </div>
      </div>
    </AuthenticatedLayout>
  );
}
