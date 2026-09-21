"use client";

import React from "react";
import Link from "next/link";
import { 
  BookOpen, 
  ShieldCheck, 
  FileCheck, 
  ListOrdered, 
  AlertTriangle, 
  Lock,
  ArrowRight,
  Info
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";

export default function ApplicationGuidelinesPage() {
  const { t } = useLanguage();

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
            <BookOpen className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                Official Guidance
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight mt-1">
              {t("guidelinesPage.title")}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {t("guidelinesPage.subtitle")}
            </p>
          </div>
        </div>
      </div>

      {/* Information Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Section 1: Process */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <ListOrdered className="h-4 w-4 text-blue-600" />
            <h2>{t("guidelinesPage.sec1Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec1Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Standard lifecycle</span>
            <span className="font-semibold text-blue-600">5 Operational Steps</span>
          </div>
        </div>

        {/* Section 2: Documentation Standards */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <FileCheck className="h-4 w-4 text-blue-600" />
            <h2>{t("guidelinesPage.sec2Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec2Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Accepted formats: PDF, JPG, PNG</span>
            <span className="font-semibold text-slate-700">Max 10 MB per file</span>
          </div>
        </div>

        {/* Section 3: Status Definitions */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Info className="h-4 w-4 text-blue-600" />
            <h2>{t("guidelinesPage.sec3Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec3Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Status audit history</span>
            <span className="font-semibold text-slate-700">Logged in real time</span>
          </div>
        </div>

        {/* Section 4: Important Borrower Instructions */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <h2>{t("guidelinesPage.sec4Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec4Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Statutory compliance</span>
            <span className="font-semibold text-amber-700">Strict Enforcement</span>
          </div>
        </div>

        {/* Section 5: Compliance Responsibilities */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <ShieldCheck className="h-4 w-4 text-blue-600" />
            <h2>{t("guidelinesPage.sec5Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec5Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Response turnaround</span>
            <span className="font-semibold text-slate-700">Within 7 business days</span>
          </div>
        </div>

        {/* Section 6: Data Governance */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Lock className="h-4 w-4 text-blue-600" />
            <h2>{t("guidelinesPage.sec6Title")}</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("guidelinesPage.sec6Desc")}
          </p>
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Encryption standards</span>
            <span className="font-semibold text-emerald-700">AES-256 / TLS 1.3</span>
          </div>
        </div>
      </div>

      {/* Regulatory Future Scope Notice */}
      <div className="p-4 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-900 text-xs leading-relaxed flex items-start gap-2.5">
        <Info className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Notice of Regulatory Scope: </span>
          <span>{t("guidelinesPage.notice")}</span>
        </div>
      </div>

      {/* Quick Navigation Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <Link
          href="/dashboard"
          className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          ← {t("common.back")} to {t("nav.dashboard")}
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/applications/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-[#0B192C] hover:bg-slate-800 rounded transition-colors"
          >
            <span>Start Loan Application</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
      </div>
    </AuthenticatedLayout>
  );
}
