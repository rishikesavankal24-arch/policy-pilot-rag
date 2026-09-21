"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  HelpCircle, 
  ChevronDown, 
  FileText, 
  UploadCloud, 
  UserCheck, 
  Headphones, 
  ShieldCheck,
  Info
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { cn } from "@/lib/utils";

interface FaqItem {
  question: string;
  answer: string;
  category: string;
}

export default function HelpSupportPage() {
  const { t } = useLanguage();
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs: FaqItem[] = [
    {
      question: "How do I start a new credit facility application?",
      answer: "Navigate to 'My Applications' from the main menu and click 'New Loan Application'. Follow the 5-step form to declare loan parameters, employment details, and financial obligations. You may save your progress as a draft at any stage before final submission.",
      category: "Applications"
    },
    {
      question: "What document formats and sizes are supported?",
      answer: "PolicyPilot supports PDF, JPG, and PNG files up to 10 MB each. Ensure scanned copies are clear, uncropped, and show all four corners of the statutory ID or bank statement. Documents uploaded are immediately indexed and linked to your customer profile.",
      category: "Documents"
    },
    {
      question: "Can I modify my application after it has been submitted?",
      answer: "Once an application moves to 'SUBMITTED' or 'UNDER_REVIEW' status, core financial terms cannot be directly edited to preserve underwriting audit integrity. If additional clarifications or documents are needed, an action item will appear in 'Required Actions'.",
      category: "Workflow"
    },
    {
      question: "Where can I view pending requirements or missing papers?",
      answer: "Check the 'Required Actions' page in the main navigation. Any incomplete drafts, document requests, or credit desk notifications requiring customer response will be prominently listed there with direct links to proceed.",
      category: "Actions"
    },
    {
      question: "How do I switch the portal language?",
      answer: "Click your profile name in the top-right header or select 'Language' from the main menu. PolicyPilot supports 6 Indian languages (English, தமிழ், हिन्दी, తెలుగు, ಕನ್ನಡ, മലയാളം) with immediate UI translation and persistent profile storage.",
      category: "Language & Account"
    },
    {
      question: "How is my personal financial data protected?",
      answer: "All communication is encrypted via TLS 1.3, and underlying data stores use strict customer ownership isolation with PostgreSQL row-level security. Employees access records solely based on authorized verification roles.",
      category: "Security"
    }
  ];

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
            <HelpCircle className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              {t("helpPage.title")}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {t("helpPage.subtitle")}
            </p>
          </div>
        </div>
      </div>

      {/* Support Pillars Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Pillar 1 */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-2.5">
          <div className="h-9 w-9 rounded-lg bg-blue-50 text-blue-600 border border-blue-200 flex items-center justify-center">
            <FileText className="h-5 w-5" />
          </div>
          <h2 className="text-sm font-bold text-slate-900">
            {t("helpPage.portalHelpTitle")}
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("helpPage.portalHelpDesc")}
          </p>
          <div className="pt-2">
            <Link
              href="/dashboard/guidelines"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
            >
              View step-by-step guidelines →
            </Link>
          </div>
        </div>

        {/* Pillar 2 */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-2.5">
          <div className="h-9 w-9 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center">
            <UploadCloud className="h-5 w-5" />
          </div>
          <h2 className="text-sm font-bold text-slate-900">
            {t("helpPage.docHelpTitle")}
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("helpPage.docHelpDesc")}
          </p>
          <div className="pt-2">
            <Link
              href="/dashboard/documents"
              className="text-xs font-semibold text-emerald-600 hover:text-emerald-800 transition-colors"
            >
              Open documents repository →
            </Link>
          </div>
        </div>

        {/* Pillar 3 */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-2.5">
          <div className="h-9 w-9 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200 flex items-center justify-center">
            <UserCheck className="h-5 w-5" />
          </div>
          <h2 className="text-sm font-bold text-slate-900">
            {t("helpPage.accountHelpTitle")}
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("helpPage.accountHelpDesc")}
          </p>
          <div className="pt-2">
            <Link
              href="/profile"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              Manage profile details →
            </Link>
          </div>
        </div>
      </div>

      {/* Expandable FAQs Section */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">
            {t("helpPage.faqTitle")}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {t("helpPage.faqSubtitle")}
          </p>
        </div>

        <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div key={idx} className="bg-white">
                <button
                  type="button"
                  onClick={() => setOpenIndex(isOpen ? null : idx)}
                  className="w-full text-left px-5 py-3.5 flex items-center justify-between gap-3 hover:bg-slate-50 transition-colors"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                      {faq.category}
                    </span>
                    <span className="text-xs font-bold text-slate-900">
                      {faq.question}
                    </span>
                  </div>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-slate-400 transition-transform duration-200 shrink-0",
                      isOpen && "rotate-180 text-blue-600"
                    )}
                  />
                </button>
                {isOpen && (
                  <div className="px-5 pb-4 pt-1 text-xs text-slate-600 leading-relaxed bg-slate-50/50 border-t border-slate-100">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Support Desk Transparent Placeholder */}
      <div className="p-5 rounded-lg bg-slate-900 text-white shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-slate-800 text-blue-400 border border-slate-700 shrink-0">
            <Headphones className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">
              {t("helpPage.supportChannelNoticeTitle")}
            </h3>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              {t("helpPage.supportChannelNoticeDesc")}
            </p>
          </div>
        </div>
        <div className="shrink-0">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Operational Notice</span>
          </span>
        </div>
      </div>
      </div>
    </AuthenticatedLayout>
  );
}
