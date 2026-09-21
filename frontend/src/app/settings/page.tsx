"use client";

import React from "react";
import Link from "next/link";
import { 
  Settings, 
  User, 
  Languages, 
  Bell, 
  Eye, 
  ShieldCheck, 
  ArrowRight,
  CheckCircle2,
  Lock
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";

export default function AccountSettingsPage() {
  const { user } = useAuth();
  const { language, supportedLanguages, t } = useLanguage();

  const currentLangObj = supportedLanguages.find((l) => l.code === language) || supportedLanguages[0];

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
            <Settings className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {t("settingsPage.title")}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {t("settingsPage.subtitle")}
            </p>
          </div>
        </div>
      </div>

      {/* 1. Statutory Account Information */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <User className="h-4 w-4 text-blue-600" />
            <h2>{t("settingsPage.accountDetailsTitle")}</h2>
          </div>
          <Link
            href="/profile"
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors inline-flex items-center gap-1"
          >
            <span>Edit Profile</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded bg-slate-50 border border-slate-200 space-y-1">
            <span className="text-slate-500 font-medium">{t("profile.fullName")}</span>
            <p className="font-bold text-slate-900 text-sm">{user?.full_name || "Not provided"}</p>
          </div>

          <div className="p-3.5 rounded bg-slate-50 border border-slate-200 space-y-1">
            <span className="text-slate-500 font-medium">{t("profile.emailAddress")}</span>
            <p className="font-mono text-slate-900 font-semibold">{user?.email}</p>
          </div>

          <div className="p-3.5 rounded bg-slate-50 border border-slate-200 space-y-1">
            <span className="text-slate-500 font-medium">Assigned System Role</span>
            <div className="flex items-center gap-1.5 pt-0.5">
              <span className="inline-flex items-center rounded px-2 py-0.5 text-[11px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                {user?.role || user?.requested_role || "CUSTOMER"}
              </span>
              <span className="text-[10px] text-slate-400">Statutory Verified</span>
            </div>
          </div>

          <div className="p-3.5 rounded bg-slate-50 border border-slate-200 space-y-1">
            <span className="text-slate-500 font-medium">Onboarding Status</span>
            <div className="flex items-center gap-1.5 pt-0.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span className="font-bold text-slate-800 uppercase tracking-wide text-[11px]">
                {user?.onboarding_status || "COMPLETED"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Preferred Language */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Languages className="h-4 w-4 text-blue-600" />
            <h2>{t("settingsPage.languageTitle")}</h2>
          </div>
          <Link
            href="/settings/language"
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors inline-flex items-center gap-1"
          >
            <span>Change Language</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded bg-slate-50 border border-slate-200">
          <div>
            <p className="text-sm font-bold text-slate-900">
              {currentLangObj.nativeName} ({currentLangObj.name})
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Active language for UI prompts, form descriptions, and account notifications.
            </p>
          </div>
          <Link
            href="/settings/language"
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-bold text-white bg-[#0B192C] hover:bg-slate-800 rounded transition-colors shrink-0"
          >
            Select Language
          </Link>
        </div>
      </div>

      {/* 3. Notification Channels (Informational) */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
          <Bell className="h-4 w-4 text-blue-600" />
          <h2>{t("settingsPage.notificationsTitle")}</h2>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {t("settingsPage.notifNotice")}
        </p>
        <div className="pt-2 flex flex-wrap gap-2 text-[11px]">
          <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
            ✓ In-App Notification Center (Active)
          </span>
          <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
            ✓ Operational Email Alerts (Active)
          </span>
        </div>
      </div>

      {/* 4. Accessibility Preferences (Informational) */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">
          <Eye className="h-4 w-4 text-blue-600" />
          <h2>{t("settingsPage.accessibilityTitle")}</h2>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed">
          {t("settingsPage.a11yNotice")}
        </p>
        <div className="pt-2 flex flex-wrap gap-2 text-[11px]">
          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
            Standard High-Contrast Theme
          </span>
          <span className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
            Full Keyboard Navigation (WCAG 2.1 AA)
          </span>
        </div>
      </div>

      {/* 5. Security & Authentication Isolation Notice */}
      <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2.5">
        <Lock className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-slate-800">Security Architecture Disclosure: </span>
          <span>{t("settingsPage.authNotice")}</span>
        </div>
      </div>
      </div>
    </AuthenticatedLayout>
  );
}
