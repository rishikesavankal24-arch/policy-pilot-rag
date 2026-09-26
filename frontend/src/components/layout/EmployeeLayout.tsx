"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { 
  Shield, 
  FileText, 
  Bell, 
  LayoutDashboard, 
  User, 
  LogOut, 
  AlertTriangle,
  Menu, 
  X, 
  CheckCircle, 
  Info, 
  ShieldCheck, 
  Check, 
  ChevronDown, 
  Settings, 
  Languages,
  Building2,
  ClipboardList,
  Users,
  BarChart3,
  Search,
  Lock,
  ArrowRight,
  BookOpen
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/i18n/LanguageContext";

interface EmployeeLayoutProps {
  children: React.ReactNode;
}

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

export function EmployeeLayout({ children }: EmployeeLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, isLoading: authLoading } = useAuth();
  const { t, language, languageInfo, setLanguage, supportedLanguages, isUpdatingLang } = useLanguage();
  
  // Navigation drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Notification popover state
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoadingNotifs, setIsLoadingNotifs] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Employee profile popover state
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  // Language selector modal state
  const [isLanguageModalOpen, setIsLanguageModalOpen] = useState(false);

  // Generate initials for avatar badge
  const getInitials = (name?: string | null, email?: string | null) => {
    if (name) {
      const parts = name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
      }
      return name.slice(0, 2).toUpperCase();
    }
    if (email) {
      return email.slice(0, 2).toUpperCase();
    }
    return "EO";
  };

  // Fetch real employee notifications from API
  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    try {
      setIsLoadingNotifs(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/employee/notifications`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      }
    } catch {
      // Silently catch in polling
    } finally {
      setIsLoadingNotifs(false);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Close drawer, notification, profile popover, and language modal on route change
  useEffect(() => {
    setIsDrawerOpen(false);
    setIsNotifOpen(false);
    setIsProfileOpen(false);
    setIsLanguageModalOpen(false);
  }, [pathname]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsDrawerOpen(false);
        setIsNotifOpen(false);
        setIsProfileOpen(false);
        setIsLanguageModalOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close notification and profile dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileOpen(false);
      }
    };
    if (isNotifOpen || isProfileOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isNotifOpen, isProfileOpen]);

  const isVerifiedEmployee = user?.role === "EMPLOYEE" && user?.onboarding_status === "COMPLETED";
  const isPendingVerification = user?.onboarding_status === "PENDING_VERIFICATION";
  const isCustomer = user?.role === "CUSTOMER";

  // Active route checking
  const isItemActive = (href: string) => {
    if (href === "/employee/dashboard") {
      return pathname === "/employee/dashboard";
    }
    if (href === "/employee/applications") {
      return pathname === "/employee/applications" || (pathname?.startsWith("/employee/applications/") && !pathname?.includes("queue"));
    }
    if (href === "/employee/policies") {
      return pathname === "/employee/policies" || pathname?.startsWith("/employee/policies/");
    }
    return pathname === href || pathname?.startsWith(`${href}/`);
  };

  // Structured Employee Navigation Groups
  const employeeNavGroups = [
    {
      label: t("employeeNav.main"),
      items: [
        { name: t("employeeNav.dashboard"), href: "/employee/dashboard", icon: LayoutDashboard },
        { name: t("employeeNav.applicationQueue"), href: "/employee/applications", icon: FileText },
        { name: t("employeeNav.myAssignments"), href: "/employee/assignments", icon: ClipboardList },
        { name: t("employeeNav.documents"), href: "/employee/documents", icon: FileText },
        { name: t("employeeNav.compliance"), href: "/employee/compliance", icon: Shield },
        { name: t("employeeNav.notifications"), href: "/employee/notifications", icon: Bell },
      ]
    },
    {
      label: "POLICIES",
      items: [
        { name: "Policy Catalog", href: "/employee/policies", icon: BookOpen },
      ]
    },
    {
      label: t("employeeNav.workspace"),
      items: [
        { name: t("employeeNav.applicationReview"), href: "/employee/applications", icon: ClipboardList },
        { name: t("employeeNav.customerInfo"), href: "/employee/applications", icon: Users },
        { name: t("employeeNav.complianceWorkspace"), href: "/employee/compliance", icon: ShieldCheck },
        { name: t("employeeNav.reports"), href: "/employee/reports", icon: BarChart3 },
      ]
    },
    {
      label: t("employeeNav.account"),
      items: [
        { name: t("employeeNav.myProfile"), href: "/employee/profile", icon: User },
        { name: t("employeeNav.organization"), href: "/employee/organization", icon: Building2 },
        { name: t("employeeNav.language"), href: "/employee/settings/language", icon: Languages },
        { name: t("employeeNav.accountSettings"), href: "/employee/settings", icon: Settings },
      ]
    }
  ];

  const getNotifIcon = (type: string) => {
    switch (type) {
      case 'SUCCESS':
        return <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />;
      case 'WARNING':
        return <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />;
      case 'SECURITY':
        return <ShieldCheck className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />;
      default:
        return <Info className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />;
    }
  };

  // Loading state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs uppercase tracking-wider font-mono">Authenticating Institutional Console...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B132B] text-slate-100 flex flex-col font-sans">
      {/* Enterprise Compliance Workflow Utility Strip */}
      <div className="bg-[#070D1E] text-slate-400 text-[11px] font-medium tracking-wider px-4 sm:px-6 py-1.5 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="uppercase font-semibold text-slate-200">PolicyPilot Enterprise • Policy & Underwriting Console</span>
          <span className="hidden md:inline-block text-slate-500">|</span>
          <span className="hidden md:inline-block text-slate-400 font-mono text-[10px]">POLICY REVIEW WORKSPACE</span>
        </div>
        <div className="flex items-center gap-4 text-[10px] text-slate-400 uppercase tracking-wider">
          <span className="hidden sm:inline-block bg-slate-800/80 px-2 py-0.5 rounded text-amber-300 border border-amber-500/20 font-mono">
            INTERNAL AUDIT TRAIL
          </span>
          <span className="font-mono text-slate-400">NODE: DL-014-OPS</span>
        </div>
      </div>

      {/* Main Enterprise Header */}
      <header className="sticky top-0 z-40 bg-[#0F172A]/95 backdrop-blur-md border-b border-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          
          {/* Left: Hamburger & Institutional Brand */}
          <div className="flex items-center gap-3">
            <button
              id="employee-nav-hamburger-btn"
              onClick={() => setIsDrawerOpen(true)}
              className="p-2 -ml-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400/40"
              aria-label="Toggle Enterprise Navigation"
            >
              <Menu className="h-5 w-5" />
            </button>

            <Link href="/employee/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 font-bold shadow-md group-hover:scale-105 transition-transform">
                <Shield className="h-5 w-5 text-slate-950" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                  PolicyPilot <span className="text-[11px] font-semibold px-1.5 py-0.2 bg-amber-400/10 text-amber-400 border border-amber-400/30 rounded">OPS</span>
                </span>
                <span className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">
                  Institutional Underwriting Desk
                </span>
              </div>
            </Link>

            {/* Desktop Navigation Links */}
            <nav className="hidden lg:flex items-center gap-1 ml-6 border-l border-slate-800 pl-6">
              <Link
                href="/employee/dashboard"
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  pathname === "/employee/dashboard"
                    ? "bg-amber-400/10 text-amber-300 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                )}
              >
                Dashboard
              </Link>
              <Link
                href="/employee/applications"
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  pathname?.startsWith("/employee/applications")
                    ? "bg-amber-400/10 text-amber-300 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                )}
              >
                Applications
              </Link>
              <Link
                href="/employee/policies"
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5",
                  pathname?.startsWith("/employee/policies")
                    ? "bg-amber-400/15 text-amber-300 border border-amber-400/30 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                )}
              >
                <BookOpen className="h-3.5 w-3.5 text-amber-400" />
                <span>Policy Catalog</span>
              </Link>
              <Link
                href="/employee/compliance"
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  pathname === "/employee/compliance"
                    ? "bg-amber-400/10 text-amber-300 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                )}
              >
                Compliance
              </Link>
            </nav>
          </div>

          {/* Right: Notification Bell & Officer Profile Area */}
          <div className="flex items-center gap-3">
            
            {/* Notification Bell */}
            <div className="relative" ref={notifRef}>
              <button
                id="employee-notification-bell-btn"
                onClick={() => setIsNotifOpen((prev) => !prev)}
                className="relative p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400/40"
                aria-label="Official Alerts"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-bold text-slate-950 ring-2 ring-slate-900">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown */}
              {isNotifOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-[#1E293B] border border-slate-700 shadow-2xl z-50 overflow-hidden text-slate-100">
                  <div className="px-4 py-3 bg-[#0F172A] border-b border-slate-700 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-200">Official Operational Alerts</span>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.5 text-[10px] font-bold bg-amber-400/20 text-amber-300 rounded border border-amber-400/30">
                          {unreadCount} NEW
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-800">
                    {isLoadingNotifs ? (
                      <div className="p-6 text-center text-xs text-slate-400">Loading alerts...</div>
                    ) : notifications.length === 0 ? (
                      <div className="p-8 text-center">
                        <CheckCircle className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                        <p className="text-xs font-medium text-slate-300">All queues monitored</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">No pending regulatory or operational alerts</p>
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div 
                          key={n.id} 
                          className={cn(
                            "p-3.5 hover:bg-slate-800/50 transition-colors flex items-start gap-3",
                            !n.is_read && "bg-slate-800/30"
                          )}
                        >
                          {getNotifIcon(n.type)}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-slate-200 truncate">{n.title}</p>
                            <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{n.message}</p>
                            <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                              {n.created_at ? new Date(n.created_at).toLocaleDateString() : ""}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="p-2 bg-[#0F172A] border-t border-slate-700 text-center">
                    <Link
                      href="/employee/notifications"
                      className="text-xs text-amber-400 hover:text-amber-300 font-medium tracking-wide transition-colors"
                      onClick={() => setIsNotifOpen(false)}
                    >
                      View All Operational Alerts →
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Officer Profile Dropdown Trigger */}
            <div className="relative" ref={profileRef}>
              <button
                id="employee-profile-popover-btn"
                onClick={() => setIsProfileOpen((prev) => !prev)}
                className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400/40"
                aria-label="Officer Profile Menu"
              >
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 flex items-center justify-center text-xs">
                  {getInitials(user?.full_name, user?.email)}
                </div>
                <div className="hidden sm:flex flex-col text-left">
                  <span className="text-xs font-semibold text-slate-200 truncate max-w-[140px]">
                    {user?.full_name || "Authorized Officer"}
                  </span>
                  <span className="text-[10px] text-amber-400 font-mono font-medium">
                    OPERATIONS OFFICER
                  </span>
                </div>
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </button>

              {/* Profile Dropdown */}
              {isProfileOpen && (
                <div className="absolute right-0 mt-2 w-72 rounded-xl bg-[#1E293B] border border-slate-700 shadow-2xl z-50 overflow-hidden text-slate-100">
                  <div className="p-4 bg-[#0F172A] border-b border-slate-700">
                    <p className="text-sm font-bold text-white truncate">{user?.full_name || "Authorized Officer"}</p>
                    <p className="text-xs text-slate-400 truncate font-mono mt-0.5">{user?.email}</p>
                    <div className="mt-2.5 flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-400/10 text-amber-400 border border-amber-400/30 uppercase tracking-wider">
                        {t("employeePortal.badge")}
                      </span>
                      {isVerifiedEmployee && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-400/10 text-emerald-400 border border-emerald-400/30 uppercase tracking-wider">
                          VERIFIED
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="p-2 space-y-1 text-xs">
                    <Link
                      href="/employee/profile"
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                      onClick={() => setIsProfileOpen(false)}
                    >
                      <User className="h-4 w-4 text-slate-400" />
                      <span>{t("employeeNav.myProfile")}</span>
                    </Link>

                    <Link
                      href="/employee/organization"
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                      onClick={() => setIsProfileOpen(false)}
                    >
                      <Building2 className="h-4 w-4 text-slate-400" />
                      <span>{t("employeeNav.organization")}</span>
                    </Link>

                    <button
                      onClick={() => {
                        setIsProfileOpen(false);
                        setIsLanguageModalOpen(true);
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors text-left"
                    >
                      <div className="flex items-center gap-2.5">
                        <Languages className="h-4 w-4 text-slate-400" />
                        <span>{t("employeeNav.language")}</span>
                      </div>
                      <span className="text-[11px] font-medium text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded">
                        {languageInfo.nativeName}
                      </span>
                    </button>

                    <Link
                      href="/employee/settings"
                      className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                      onClick={() => setIsProfileOpen(false)}
                    >
                      <Settings className="h-4 w-4 text-slate-400" />
                      <span>{t("employeeNav.accountSettings")}</span>
                    </Link>

                    <div className="my-1 border-t border-slate-800"></div>

                    <button
                      onClick={async () => {
                        setIsProfileOpen(false);
                        await logout();
                        router.push("/login");
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-rose-400 hover:bg-rose-950/40 hover:text-rose-300 transition-colors"
                    >
                      <LogOut className="h-4 w-4" />
                      <span>{t("employeeNav.signOut")}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </header>

      {/* Verification Pending Alert for Unapproved Employees */}
      {isPendingVerification && (
        <div className="bg-amber-950/80 border-b border-amber-600/40 px-4 py-2.5 text-amber-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-5xl mx-auto w-full">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>Officer Verification Pending:</strong> Your institutional onboarding request is awaiting supervisor approval. Application queues and underwriter actions remain restricted until verification is complete.
            </span>
          </div>
        </div>
      )}

      {/* Customer Attempting Access to Employee Portal Notice */}
      {isCustomer && (
        <div className="bg-rose-950/80 border-b border-rose-600/40 px-4 py-2.5 text-rose-200 text-xs flex items-center justify-between">
          <div className="flex items-center justify-between max-w-5xl mx-auto w-full">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-rose-400 shrink-0" />
              <span>
                <strong>Restricted Area:</strong> This console is reserved for authorized institutional employees and bank officers.
              </span>
            </div>
            <Link
              href="/dashboard"
              className="px-2.5 py-1 bg-rose-900/60 hover:bg-rose-800 text-white rounded font-medium text-xs flex items-center gap-1 transition-colors"
            >
              Customer Portal <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      )}

      {/* Side Navigation Drawer */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setIsDrawerOpen(false)}
          ></div>

          {/* Drawer Content */}
          <div className="relative w-72 sm:w-80 bg-[#0F172A] border-r border-slate-800 flex flex-col h-full shadow-2xl z-10">
            {/* Drawer Header */}
            <div className="p-4 bg-[#070D1E] border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center text-slate-950 font-bold">
                  <Shield className="h-4 w-4 text-slate-950" />
                </div>
                <div>
                  <p className="font-bold text-sm text-white">PolicyPilot OPS</p>
                  <p className="text-[10px] text-amber-400 font-mono uppercase">Banking Operations</p>
                </div>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Officer Badge Strip in Drawer */}
            <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800 flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-slate-800 text-amber-400 font-bold flex items-center justify-center text-xs border border-amber-500/20">
                {getInitials(user?.full_name, user?.email)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || "Authorized Officer"}</p>
                <p className="text-[10px] text-slate-400 font-mono truncate">{user?.email}</p>
              </div>
            </div>

            {/* Navigation Groups */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {employeeNavGroups.map((group, idx) => (
                <div key={idx} className="space-y-1">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 mb-2 font-mono">
                    {group.label}
                  </p>
                  {group.items.map((item, itemIdx) => {
                    const Icon = item.icon;
                    const active = isItemActive(item.href);
                    return (
                      <Link
                        key={itemIdx}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all",
                          active
                            ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold"
                            : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                        )}
                        onClick={() => setIsDrawerOpen(false)}
                      >
                        <Icon className={cn("h-4 w-4", active ? "text-amber-400" : "text-slate-400")} />
                        <span>{item.name}</span>
                      </Link>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Drawer Footer / Sign Out */}
            <div className="p-4 border-t border-slate-800 bg-[#070D1E] space-y-2">
              <button
                onClick={async () => {
                  setIsDrawerOpen(false);
                  await logout();
                  router.push("/login");
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-rose-400 hover:bg-rose-950/30 hover:text-rose-300 text-xs font-medium transition-colors"
              >
                <LogOut className="h-4 w-4" />
                <span>{t("employeeNav.signOut")}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Language Selector Modal */}
      {isLanguageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setIsLanguageModalOpen(false)}
          ></div>

          <div className="relative w-full max-w-md rounded-2xl bg-[#1E293B] border border-slate-700 p-6 shadow-2xl z-10 text-slate-100">
            <div className="flex items-center justify-between pb-4 border-b border-slate-700">
              <div>
                <h3 className="text-base font-bold text-white">{t("languageModal.title")}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{t("languageModal.subtitle")}</p>
              </div>
              <button
                onClick={() => setIsLanguageModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="py-4 space-y-2">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 font-mono">
                {t("languageModal.suggestedLanguages")}
              </p>
              <div className="grid grid-cols-2 gap-2">
                {supportedLanguages.map((lang) => {
                  const isSelected = language === lang.code;
                  return (
                    <button
                      key={lang.code}
                      onClick={() => {
                        setLanguage(lang.code);
                        setIsLanguageModalOpen(false);
                      }}
                      disabled={isUpdatingLang}
                      className={cn(
                        "p-3 rounded-xl border text-left transition-all flex flex-col justify-between",
                        isSelected
                          ? "border-amber-400/60 bg-amber-500/15 text-white"
                          : "border-slate-700 bg-slate-800/40 text-slate-300 hover:bg-slate-800 hover:border-slate-600"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold">{lang.nativeName}</span>
                        {isSelected && <Check className="h-4 w-4 text-amber-400" />}
                      </div>
                      <span className="text-xs text-slate-400 mt-1">{lang.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-700 text-right">
              <button
                onClick={() => setIsLanguageModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                {t("languageModal.close")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {children}
      </main>

      {/* Compliance Operations Footer */}
      <footer className="bg-[#070D1E] border-t border-slate-800 text-slate-500 text-[11px] py-4 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">PolicyPilot Enterprise Core</span>
            <span>•</span>
            <span>Version 1.4-LTS</span>
            <span>•</span>
            <span>Prototype Compliance Workflow</span>
          </div>
          <div className="flex items-center gap-4 text-slate-500">
            <span>Policy Review Workspace</span>
            <span>•</span>
            <span>Internal Audit Trail Enabled</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
