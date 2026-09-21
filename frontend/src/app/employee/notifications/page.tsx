"use client";

import { useEffect, useState } from "react";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  Bell, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldCheck, 
  Info, 
  RefreshCw,
  MailCheck
} from "lucide-react";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  related_entity_id: string | null;
  created_at: string | null;
}

export default function EmployeeNotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/notifications`, {
        credentials: "include"
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
      }
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const getNotifIcon = (type: string) => {
    switch (type) {
      case "SUCCESS":
        return <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />;
      case "WARNING":
        return <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />;
      case "SECURITY":
        return <ShieldCheck className="h-5 w-5 text-blue-400 shrink-0" />;
      default:
        return <Info className="h-5 w-5 text-slate-400 shrink-0" />;
    }
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white uppercase">
                Official Operational Alerts
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30">
                AUDIT NOTIFICATIONS
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Supervisory dispatches, queue escalations, and system integrity notices
            </p>
          </div>

          <button
            onClick={fetchNotifications}
            disabled={loading}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Alerts</span>
          </button>
        </div>

        {/* Notifications List */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-xl overflow-hidden shadow-sm divide-y divide-slate-800">
          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              Loading operational dispatches...
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <MailCheck className="h-8 w-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs font-bold text-slate-300">All alerts cleared</p>
              <p className="text-[11px] text-slate-500 mt-0.5">No pending supervisory dispatches or queue warnings</p>
            </div>
          ) : (
            notifications.map((n) => (
              <div 
                key={n.id} 
                className={`p-4 flex items-start gap-3.5 hover:bg-slate-800/40 transition-colors ${
                  !n.is_read ? "bg-slate-800/20" : ""
                }`}
              >
                <div className="mt-0.5">{getNotifIcon(n.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-xs font-bold text-slate-100 truncate">{n.title}</h3>
                    <span className="text-[10px] text-slate-500 font-mono shrink-0">
                      {n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{n.message}</p>
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </EmployeeLayout>
  );
}
