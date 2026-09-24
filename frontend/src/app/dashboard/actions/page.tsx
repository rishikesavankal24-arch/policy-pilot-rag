"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight, 
  Clock, 
  RefreshCw,
  FileText,
  ShieldAlert,
  Info,
  Upload,
  HelpCircle
} from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { cn } from "@/lib/utils";

interface RequiredAction {
  id?: string;
  type?: string;
  title: string;
  description: string;
  link?: string;
  action_url?: string;
  action_label?: string;
  priority?: string;
  urgency?: "CRITICAL" | "HIGH" | "MEDIUM" | "ROUTINE" | string;
  application_id?: string;
}

export default function RequiredActionsPage() {
  const { t } = useLanguage();
  const [actions, setActions] = useState<RequiredAction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchActions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/customer/actions`, {
        credentials: "include",
      });

      if (!res.ok) {
        // Fallback to customer summary if actions endpoint responds with error
        const summaryRes = await fetch(`${apiUrl}/api/customer/dashboard/summary`, {
          credentials: "include",
        });
        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          setActions(summaryData.required_actions || []);
          return;
        }
        throw new Error("Unable to retrieve required actions from the server.");
      }

      const data = await res.json();
      const actionList = Array.isArray(data) ? data : (data.actions || []);
      setActions(actionList);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error connecting to server.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  const getWorkflowBadge = (type?: string, urgency?: string, priority?: string) => {
    if (type === "DOCUMENT_REPLACEMENT_REQUIRED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-950 border border-amber-300">
          <Upload className="h-3 w-3 text-amber-700" />
          <span>DOCUMENT REPLACEMENT REQUIRED</span>
        </span>
      );
    }
    if (type === "ADDITIONAL_INFORMATION_REQUIRED" || type === "INFORMATION_REQUEST") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-950 border border-blue-300">
          <HelpCircle className="h-3 w-3 text-blue-700" />
          <span>ADDITIONAL INFORMATION REQUIRED</span>
        </span>
      );
    }
    return getUrgencyBadge(urgency, priority);
  };

  const getUrgencyBadge = (urgency?: string, priority?: string) => {
    const val = (urgency || priority || "").toUpperCase();
    if (val === "HIGH" || val === "CRITICAL" || val === "ACTION_REQUIRED") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
          <AlertCircle className="h-3 w-3 text-amber-700" />
          {t("actionsPage.actionRequiredBadge")}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
        <Clock className="h-3 w-3 text-slate-500" />
        {t("actionsPage.routineBadge")}
      </span>
    );
  };

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded bg-amber-50 text-amber-800 border border-amber-200">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  {t("actionsPage.title")}
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  {t("actionsPage.subtitle")}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-slate-100 text-slate-800 border border-slate-200">
              {t("actionsPage.pendingCount")}: <span className="text-blue-700 font-bold">{actions.length}</span>
            </span>
            <button
              type="button"
              onClick={fetchActions}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors disabled:opacity-50"
              title="Refresh actions"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isLoading && "animate-spin")} />
              <span>{t("common.retry")}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
          <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mx-auto mb-3" />
          <p className="text-xs font-semibold text-slate-600">{t("common.loading")}</p>
        </div>
      ) : actions.length === 0 ? (
        /* Empty State */
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center max-w-2xl mx-auto shadow-sm">
          <div className="h-12 w-12 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h2 className="text-base font-bold text-slate-900 mb-1">
            {t("actionsPage.noActionsTitle")}
          </h2>
          <p className="text-xs text-slate-500 leading-relaxed max-w-md mx-auto mb-6">
            {t("actionsPage.noActionsSubtitle")}
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/dashboard/applications"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-[#0B192C] hover:bg-slate-800 rounded transition-colors"
            >
              <FileText className="h-4 w-4" />
              <span>{t("nav.myApplications")}</span>
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded transition-colors"
            >
              <span>{t("nav.dashboard")}</span>
            </Link>
          </div>
        </div>
      ) : (
        /* Action Items List */
        <div className="space-y-3">
          {actions.map((act, index) => {
            const destinationHref = act.action_url || act.link;
            const hasValidDestination = typeof destinationHref === "string" && destinationHref.trim().length > 0;

            const isReplacement = act.type === "DOCUMENT_REPLACEMENT_REQUIRED";
            const isInfoReq = act.type === "ADDITIONAL_INFORMATION_REQUIRED" || act.type === "INFORMATION_REQUEST";

            return (
              <div
                key={act.id || `action-${index}`}
                className={cn(
                  "rounded-lg p-5 shadow-sm transition-colors flex flex-col md:flex-row md:items-center md:justify-between gap-4",
                  isReplacement
                    ? "bg-amber-50/50 border-2 border-amber-300 hover:border-amber-400"
                    : isInfoReq
                    ? "bg-blue-50/40 border-2 border-blue-200 hover:border-blue-300"
                    : "bg-white border border-slate-200 hover:border-slate-300"
                )}
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {getWorkflowBadge(act.type, act.urgency, act.priority)}
                    {act.application_id && (
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {t("actionsPage.refLabel")}: {act.application_id.slice(0, 8)}
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {act.title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {act.description}
                  </p>
                </div>

                <div className="pt-2 md:pt-0 shrink-0">
                  {hasValidDestination ? (
                    <Link
                      href={destinationHref}
                      className={cn(
                        "inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-bold text-white rounded transition-colors w-full md:w-auto text-center shadow-sm",
                        isReplacement
                          ? "bg-amber-600 hover:bg-amber-700"
                          : isInfoReq
                          ? "bg-blue-600 hover:bg-blue-700"
                          : "bg-[#0B192C] hover:bg-blue-900"
                      )}
                    >
                      <span>{act.action_label || "Proceed"}</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  ) : (
                    <div className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-50 px-3 py-1.5 rounded border border-slate-200">
                      <Info className="h-3.5 w-3.5 text-slate-400" />
                      <span>Action in Progress</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      </div>
    </AuthenticatedLayout>
  );
}
