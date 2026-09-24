"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect } from "react";
import { Bell, CheckCircle, Info, AlertTriangle, ShieldCheck, Check, FolderOpen } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";

export default function NotificationsPage() {
  const { t } = useLanguage();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/notifications`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data || []);
      } else {
        setError(t("notificationsPage.failedLoad"));
      }
    } catch {
      setError(t("notificationsPage.failedLoad"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const markAsRead = async (id: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/notifications/${id}/read`, {
        method: 'PATCH',
        credentials: 'include'
      });
      if (res.ok) {
        setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
      }
    } catch (err) {
      console.error("Failed to mark notification as read", err);
    }
  };

  const markAllAsRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    for (const notif of unread) {
      await markAsRead(notif.id);
    }
  };

  const getNotificationCategory = (type: string) => {
    switch(type) {
      case 'SUCCESS':
        return {
          label: "COMPLIANCE APPROVAL",
          badge: "bg-emerald-50 text-emerald-800 border-emerald-300",
          icon: <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
        };
      case 'WARNING':
        return {
          label: "ACTION REQUIRED",
          badge: "bg-amber-50 text-amber-800 border-amber-300",
          icon: <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
        };
      case 'SECURITY':
        return {
          label: "SECURITY NOTICE",
          badge: "bg-blue-50 text-blue-800 border-blue-300",
          icon: <ShieldCheck className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        };
      case 'STATUS_UPDATE':
        return {
          label: "APPLICATION STATUS",
          badge: "bg-blue-50 text-blue-800 border-blue-300",
          icon: <CheckCircle className="h-4 w-4 text-blue-600 shrink-0 mt-0.5" />
        };
      default:
        return {
          label: "OFFICIAL BULLETIN",
          badge: "bg-slate-100 text-slate-700 border-slate-300",
          icon: <Info className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
        };
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <AuthenticatedLayout>
      <div className="max-w-4xl mx-auto space-y-6 text-slate-900">
        
        {/* Header Strip */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold uppercase tracking-tight text-slate-950">
                {t("notificationsPage.title")}
              </h1>
              {unreadCount > 0 && (
                <span className="text-xs font-semibold bg-blue-100 text-blue-900 px-2 py-0.5 rounded border border-blue-200 font-mono">
                  {unreadCount} Unread
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{t("notificationsPage.subtitle")}</p>
          </div>

          {unreadCount > 0 && (
            <button 
              onClick={markAllAsRead}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 text-slate-700 rounded text-xs font-semibold hover:bg-slate-50 transition-colors shadow-xs"
            >
              <Check className="h-3.5 w-3.5" />
              <span>{t("notificationsPage.markAllRead")}</span>
            </button>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 text-xs text-red-800 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Notices Container */}
        <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
          {isLoading ? (
            <div className="flex flex-col h-48 items-center justify-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{t("common.loading")}</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-16 px-4">
              <Bell className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-slate-800">{t("notificationsPage.emptyTitle")}</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">{t("notificationsPage.emptySubtitle")}</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {notifications.map((notif) => {
                const cat = getNotificationCategory(notif.type);
                return (
                  <div 
                    key={notif.id} 
                    className={`p-4 sm:p-5 flex items-start gap-3.5 transition-colors ${
                      notif.is_read ? 'bg-white hover:bg-slate-50/50' : 'bg-blue-50/20 hover:bg-blue-50/30'
                    }`}
                  >
                    {cat.icon}
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded border ${cat.badge}`}>
                            {cat.label}
                          </span>
                          <h4 className={`text-xs ${notif.is_read ? 'font-medium text-slate-800' : 'font-bold text-slate-950'}`}>
                            {notif.title}
                          </h4>
                        </div>
                        <span className="text-[11px] text-slate-400 font-mono">
                          {new Date(notif.created_at).toLocaleString('en-IN', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>

                      <p className="mt-1 text-xs text-slate-600 leading-relaxed">
                        {notif.message}
                      </p>
                      
                      {!notif.is_read && (
                        <div className="mt-2.5">
                          <button 
                            onClick={() => markAsRead(notif.id)}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-blue-700 hover:text-blue-900 hover:underline"
                          >
                            <Check className="h-3 w-3" />
                            <span>Mark as read</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </AuthenticatedLayout>
  );
}
