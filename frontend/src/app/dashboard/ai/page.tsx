"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  Send, 
  Lock, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle, 
  Building2, 
  Sparkles 
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";

interface ApplicationOption {
  id: string;
  loan_type: string;
  status: string;
  requested_amount: number;
  tenure: number;
}

interface AIQueryResponse {
  status: string;
  query: string;
  application_id?: string;
  application_context?: {
    reference: string;
    type: string;
    status: string;
    requested_amount: number;
    tenure: number;
  };
  customer_safe_response: string;
  engine_status: string;
  disclaimer: string;
}

export default function AIAssistantPage() {
  const { t, tStatus, tLoanType } = useLanguage();
  const [applications, setApplications] = useState<ApplicationOption[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [queryText, setQueryText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState<AIQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadApps() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiUrl}/api/applications`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setApplications(data || []);
          if (data && data.length > 0) {
            setSelectedAppId(data[0].id);
          }
        }
      } catch {
        // Silently handle
      }
    }
    loadApps();
  }, []);

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) return;

    setIsProcessing(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const payload: { query: string; application_id?: string } = {
        query: queryText.trim()
      };
      if (selectedAppId) {
        payload.application_id = selectedAppId;
      }

      const res = await fetch(`${apiUrl}/api/customer/ai/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || "Failed to process query through AI service boundary.");
      }

      const data = await res.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || "An error occurred while contacting the AI service boundary.");
    } finally {
      setIsProcessing(false);
    }
  };

  const selectedApp = applications.find(a => a.id === selectedAppId);

  return (
    <AuthenticatedLayout>
      <div className="max-w-4xl mx-auto space-y-6 text-slate-900 pb-12">
        
        {/* Header Strip */}
        <div className="border-b border-slate-200 pb-5">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold uppercase tracking-tight text-slate-950">
              {t("aiAssistant.title")}
            </h1>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-800 px-2 py-0.5 rounded border border-blue-200">
              Integration Boundary Active (M10/M11 Ready)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {t("aiAssistant.subtitle")}
          </p>
        </div>

        {/* Official Architecture & Customer Safety Notice */}
        <div className="bg-slate-50 border border-slate-200 rounded p-4 text-xs space-y-2">
          <div className="flex items-center gap-2 text-slate-900 font-semibold uppercase tracking-wider text-[11px]">
            <Lock className="h-4 w-4 text-blue-700" />
            <span>{t("aiAssistant.statusTitle")}</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            {t("aiAssistant.statusDescription")}
          </p>
          <div className="flex flex-wrap items-center gap-4 pt-1 text-[11px] text-slate-500 font-medium">
            <span className="flex items-center gap-1 text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Real Application Context
            </span>
            <span className="flex items-center gap-1 text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Customer-Safe Boundary Enforced
            </span>
            <span className="flex items-center gap-1 text-slate-500">
              <Lock className="h-3.5 w-3.5 text-slate-400" /> Internal Notes Isolated
            </span>
          </div>
        </div>

        {/* Main Advisory Query Workspace */}
        <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {t("aiAssistant.workspaceTitle")}
            </h3>
            <span className="text-[11px] text-slate-500">
              Policy & Dossier Inquiries
            </span>
          </div>

          <form onSubmit={handleQuerySubmit} className="p-5 space-y-4 text-xs">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-red-800 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-600 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Dossier Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-800">
                {t("aiAssistant.selectApp")}
              </label>
              <select
                value={selectedAppId}
                onChange={(e) => setSelectedAppId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs font-mono"
              >
                <option value="">{t("aiAssistant.generalInquiry")}</option>
                {applications.map((app) => (
                  <option key={app.id} value={app.id}>
                    {tLoanType(app.loan_type)} — {app.id} [{tStatus(app.status)}]
                  </option>
                ))}
              </select>
            </div>

            {/* Selected Dossier Parameter Summary (Real DB Context) */}
            {selectedApp && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-1 font-mono text-[11px]">
                <div className="flex justify-between text-slate-600">
                  <span>Dossier Reference:</span>
                  <span className="font-bold text-slate-900">{selectedApp.id}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Facility Category:</span>
                  <span className="font-semibold text-slate-900">{tLoanType(selectedApp.loan_type)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Registered Status:</span>
                  <span className="font-semibold text-slate-900">{tStatus(selectedApp.status)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Requested Amount:</span>
                  <span className="font-semibold text-slate-900">₹{Number(selectedApp.requested_amount).toLocaleString('en-IN')}</span>
                </div>
              </div>
            )}

            {/* Query Input */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-800">
                Regulatory / Application Inquiry
              </label>
              <textarea
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                rows={3}
                placeholder={t("aiAssistant.askPlaceholder")}
                className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs leading-relaxed"
                required
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={isProcessing || !queryText.trim()}
                className="px-5 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
              >
                <Send className="h-3.5 w-3.5" />
                <span>{isProcessing ? t("aiAssistant.processing") : t("aiAssistant.submitQuery")}</span>
              </button>
            </div>
          </form>

          {/* Response Container */}
          {response && (
            <div className="border-t border-slate-200 p-5 bg-slate-50/70 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  {t("aiAssistant.responseHeader")}
                </span>
                <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  {t("aiAssistant.safeNotice")}
                </span>
              </div>

              {/* Inquiry repeat */}
              <div className="text-xs text-slate-500 italic">
                Query: &quot;{response.query}&quot;
              </div>

              {/* Truthful structured response */}
              <div className="p-3.5 bg-white border border-slate-200 rounded text-xs text-slate-800 leading-relaxed font-sans shadow-xs">
                {response.customer_safe_response}
              </div>

              {/* Context metadata badge */}
              {response.application_context && (
                <div className="p-2.5 bg-blue-50/50 border border-blue-200 rounded text-[11px] text-blue-900 space-y-0.5">
                  <span className="font-semibold">Associated Application:</span> {response.application_context.reference} ({response.application_context.type}, Status: {response.application_context.status})
                </div>
              )}

              <p className="text-[10px] text-slate-400">
                {response.disclaimer}
              </p>
            </div>
          )}
        </div>

        {/* 3 Safety & Architecture Pillar Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-white border border-slate-200 rounded shadow-xs space-y-1.5">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-600" />
              <h4 className="text-xs font-bold text-slate-900">{t("aiAssistant.card1Title")}</h4>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {t("aiAssistant.card1Desc")}
            </p>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded shadow-xs space-y-1.5">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-blue-600" />
              <h4 className="text-xs font-bold text-slate-900">{t("aiAssistant.card2Title")}</h4>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {t("aiAssistant.card2Desc")}
            </p>
          </div>

          <div className="p-4 bg-white border border-slate-200 rounded shadow-xs space-y-1.5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-600" />
              <h4 className="text-xs font-bold text-slate-900">{t("aiAssistant.card3Title")}</h4>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              {t("aiAssistant.card3Desc")}
            </p>
          </div>
        </div>

      </div>
    </AuthenticatedLayout>
  );
}
