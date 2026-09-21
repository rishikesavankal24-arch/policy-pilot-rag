"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  Globe,
  Sparkles,
  AlertCircle,
  BookOpen,
  HelpCircle,
  Folder,
  Languages
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/i18n/LanguageContext";

interface AuthenticatedLayoutProps {
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

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t, language, languageInfo, setLanguage, supportedLanguages, isUpdatingLang } = useLanguage();
  
  // Navigation drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  
  // Notification popover state
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoadingNotifs, setIsLoadingNotifs] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Customer profile popover state
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
    return "CP";
  };

  // Fetch real notifications from API
  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    try {
      setIsLoadingNotifs(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/notifications`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data || []);
      }
    } catch {
      // Silently handle network errors for header polling
    } finally {
      setIsLoadingNotifs(false);
    }
  }, [user]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Mark a single notification as read
  const markAsRead = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/notifications/${id}/read`, {
        method: 'PATCH',
        credentials: 'include'
      });
      if (res.ok) {
        setNotifications((prev) => 
          prev.map((n) => n.id === id ? { ...n, is_read: true } : n)
        );
      }
    } catch {
      // Ignore
    }
  };

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

  const isEmployee = user?.requested_role === "EMPLOYEE";
  const isPending = user?.onboarding_status === "PENDING_VERIFICATION";

  // Active route checking
  const isItemActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    if (href === "/settings") {
      return pathname === "/settings";
    }
    return pathname === href || pathname?.startsWith(`${href}/`);
  };

  // Structured Navigation Groups
  const customerNavGroups = [
    {
      label: t("nav.main"),
      items: [
        { name: t("nav.dashboard"), href: "/dashboard", icon: LayoutDashboard },
        { name: t("nav.myApplications"), href: "/dashboard/applications", icon: FileText },
        { name: t("nav.documents"), href: "/dashboard/documents", icon: Folder },
        { name: t("nav.requiredActions"), href: "/dashboard/actions", icon: AlertCircle },
        { name: t("nav.notifications"), href: "/dashboard/notifications", icon: Bell },
      ]
    },
    {
      label: t("nav.services"),
      items: [
        { name: t("nav.aiAssistant"), href: "/dashboard/ai", icon: Sparkles },
        { name: t("nav.guidelines"), href: "/dashboard/guidelines", icon: BookOpen },
        { name: t("nav.helpSupport"), href: "/dashboard/help", icon: HelpCircle },
      ]
    },
    {
      label: t("nav.account"),
      items: [
        { name: t("nav.profile"), href: "/profile", icon: User },
        { name: t("nav.language"), href: "/settings/language", icon: Languages },
        { name: t("nav.settings"), href: "/settings", icon: Settings },
      ]
    }
  ];

  const employeeNavGroups = [
    {
      label: "MAIN",
      items: [
        { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
        { name: "Application Queue", href: "/dashboard/queue", icon: FileText },
        { name: "Compliance", href: "/dashboard/compliance", icon: Shield },
        { name: "Reports", href: "/dashboard/reports", icon: FileText },
      ]
    },
    {
      label: "ACCOUNT",
      items: [
        { name: "Profile", href: "/profile", icon: User },
      ]
    }
  ];

  const navGroups = isEmployee ? employeeNavGroups : customerNavGroups;
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const getNotifIcon = (type: string) => {
    switch (type) {
      case 'SUCCESS':
        return <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />;
      case 'WARNING':
        return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />;
      case 'SECURITY':
        return <ShieldCheck className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />;
      default:
        return <Info className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />;
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col font-sans">
      {/* Official Regulated Banking / Government Portal Utility Strip */}
      <div className="bg-[#0B192C] text-slate-300 text-[11px] font-medium tracking-wider px-4 sm:px-6 py-1.5 flex items-center justify-between border-b border-[#1E293B]">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
          <span className="uppercase font-semibold text-slate-200">PolicyPilot • Banking Compliance Portal</span>
        </div>
        <div className="hidden md:flex items-center gap-4 text-[10px] text-slate-400 uppercase tracking-wider">
          <span>Customer Portal</span>
          <span>•</span>
          <span>Compliance & Lending Sandbox</span>
        </div>
      </div>

      {/* Top Navigation Bar with Hamburger Control & Notification Bell */}
      <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
        <div className="px-4 sm:px-6 h-16 flex items-center justify-between">
          
          {/* Left: Hamburger Button & Brand */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setIsDrawerOpen(true);
                setIsNotifOpen(false);
                setIsProfileOpen(false);
              }}
              className="p-2 -ml-2 rounded-md text-slate-700 hover:text-slate-950 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-[#0B192C] transition-colors"
              aria-label="Open navigation menu"
              aria-expanded={isDrawerOpen}
            >
              <Menu className="h-6 w-6" />
            </button>

            <Link href="/dashboard" className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded bg-[#0B192C] flex items-center justify-center text-white shadow-sm">
                <Shield className="h-5 w-5 text-amber-400" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-base text-slate-900 tracking-tight leading-tight">PolicyPilot</span>
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">Customer Portal</span>
              </div>
            </Link>
          </div>

          {/* Right: Notification Bell + Customer Identity + Sign Out */}
          <div className="flex items-center gap-2 sm:gap-3">
            
            {/* Dedicated Notification Bell with Popover Dropdown */}
            <div className="relative" ref={notifRef}>
              <button
                type="button"
                onClick={() => {
                  if (!isNotifOpen) {
                    fetchNotifications();
                  }
                  setIsNotifOpen(!isNotifOpen);
                  setIsDrawerOpen(false);
                  setIsProfileOpen(false);
                }}
                className={cn(
                  "relative p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors",
                  isNotifOpen && "bg-slate-100 text-slate-900"
                )}
                aria-label="Notifications"
                aria-expanded={isNotifOpen}
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white leading-none">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* Compact Notification Popover */}
              {isNotifOpen && (
                <div 
                  className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden animate-in fade-in-50 duration-100"
                  role="region"
                  aria-label={t("header.notifications")}
                >
                  {/* Popover Header */}
                  <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">{t("header.notifications")}</span>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-[10px] font-semibold">
                          {unreadCount} {t("header.newBadge")}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsNotifOpen(false)}
                      className="text-slate-400 hover:text-slate-600 p-0.5 rounded"
                      aria-label="Close"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Popover Notification List */}
                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                    {isLoadingNotifs && notifications.length === 0 ? (
                      <div className="p-6 text-center text-xs text-slate-500">
                        {t("common.loading")}
                      </div>
                    ) : notifications.length === 0 ? (
                      <div className="p-6 text-center">
                        <Bell className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                        <p className="text-xs font-semibold text-slate-700">{t("header.noNotifications")}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">{t("header.caughtUp")}</p>
                      </div>
                    ) : (
                      notifications.slice(0, 5).map((notif) => (
                        <div
                          key={notif.id}
                          onClick={() => {
                            if (!notif.is_read) {
                              markAsRead(notif.id);
                            }
                          }}
                          className={cn(
                            "p-3 text-left transition-colors cursor-pointer hover:bg-slate-50 flex items-start gap-2.5",
                            !notif.is_read ? "bg-blue-50/30" : "bg-white"
                          )}
                        >
                          {getNotifIcon(notif.type)}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <p className={cn(
                                "text-xs truncate",
                                !notif.is_read ? "font-semibold text-slate-900" : "font-medium text-slate-700"
                              )}>
                                {notif.title}
                              </p>
                              {!notif.is_read && (
                                <span className="h-1.5 w-1.5 rounded-full bg-blue-600 shrink-0" />
                              )}
                            </div>
                            <p className="text-[11px] text-slate-600 line-clamp-2 mt-0.5">
                              {notif.message}
                            </p>
                            <p className="text-[10px] text-slate-400 mt-1">
                              {new Date(notif.created_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Popover Footer */}
                  <div className="border-t border-slate-100 bg-slate-50/50">
                    <Link
                      href="/dashboard/notifications"
                      onClick={() => setIsNotifOpen(false)}
                      className="block py-2.5 px-4 text-center text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-slate-100 transition-colors"
                    >
                      {t("header.viewAllNotifications")}
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Customer Profile Trigger with Instagram-style Popover */}
            <div className="relative pl-1 sm:pl-2 border-l border-slate-200" ref={profileRef}>
              <button
                type="button"
                id="customer-profile-button"
                onClick={() => {
                  setIsProfileOpen(!isProfileOpen);
                  setIsNotifOpen(false);
                  setIsDrawerOpen(false);
                }}
                className={cn(
                  "flex items-center gap-2 p-1 sm:px-2 sm:py-1 rounded-lg border border-transparent hover:border-slate-200 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors text-left",
                  isProfileOpen && "bg-slate-50 border-slate-200"
                )}
                aria-label={t("header.profileMenu")}
                aria-expanded={isProfileOpen}
                aria-haspopup="true"
              >
                {/* Circular Avatar / Initials */}
                <div className="h-8 w-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-sm">
                  {getInitials(user?.full_name, user?.email)}
                </div>

                {/* Identity details (compact name + role on desktop) */}
                <div className="hidden sm:flex flex-col text-left">
                  <span className="text-xs font-semibold text-slate-900 leading-tight max-w-[130px] truncate">
                    {user?.full_name || user?.email}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium">
                    {isEmployee ? (isPending ? t("nav.verificationPending") : t("nav.employee")) : t("nav.customer")}
                  </span>
                </div>

                <ChevronDown className={cn(
                  "h-3.5 w-3.5 text-slate-400 transition-transform duration-150 hidden sm:block",
                  isProfileOpen && "rotate-180 text-slate-600"
                )} />
              </button>

              {/* Compact Instagram-style Profile Popover Dropdown */}
              {isProfileOpen && (
                <div
                  className="absolute right-0 mt-2 w-64 sm:w-72 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden animate-in fade-in-50 duration-100"
                  role="menu"
                  aria-orientation="vertical"
                  aria-labelledby="customer-profile-button"
                >
                  {/* 1, 2, 3: Customer Information & Role Badge Header */}
                  <div className="px-4 py-3 bg-slate-50/70 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900 truncate">
                      {user?.full_name || t("nav.customer")}
                    </p>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">
                      {user?.email}
                    </p>
                    <div className="mt-2">
                      {isEmployee ? (
                        <span className={cn(
                          "inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium",
                          isPending ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
                        )}>
                          {isPending ? t("nav.verificationPending") : t("nav.employee")}
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          {t("nav.customer")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 4. Divider is the border-b above */}

                  {/* Actions & Navigation Section */}
                  <div className="py-1">
                    {/* 5. My Profile */}
                    <Link
                      href="/profile"
                      onClick={() => setIsProfileOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      role="menuitem"
                    >
                      <User className="h-4 w-4 text-slate-500 shrink-0" />
                      <span>{t("header.myProfile")}</span>
                    </Link>

                    {/* 6. Account Settings */}
                    <Link
                      href="/settings"
                      onClick={() => setIsProfileOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      role="menuitem"
                    >
                      <Settings className="h-4 w-4 text-slate-500 shrink-0" />
                      <span>{t("header.accountSettings")}</span>
                    </Link>

                    {/* 7. Language (opens centered language-selection modal) */}
                    <button
                      type="button"
                      onClick={() => {
                        setIsProfileOpen(false);
                        setIsLanguageModalOpen(true);
                      }}
                      className="w-full flex items-center justify-between px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors text-left"
                      role="menuitem"
                      title={t("languageModal.title")}
                    >
                      <div className="flex items-center gap-2.5">
                        <Globe className="h-4 w-4 text-slate-500 shrink-0" />
                        <span>{t("header.language")}</span>
                      </div>
                      <span className="text-[11px] text-slate-500 font-medium">
                        {languageInfo.nativeName} ({language})
                      </span>
                    </button>
                  </div>

                  {/* 8. Divider */}
                  <div className="border-t border-slate-100" />

                  {/* 9. Sign Out */}
                  <div className="p-1">
                    <button
                      type="button"
                      onClick={() => {
                        setIsProfileOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors text-left"
                      role="menuitem"
                    >
                      <LogOut className="h-4 w-4 text-red-500 shrink-0" />
                      <span>{t("header.signOut")}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Direct Header Sign Out Action */}
            <button
              type="button"
              onClick={logout}
              className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>

        </div>
      </header>

      {/* Backdrop Overlay for Drawer */}
      <div 
        className={cn(
          "fixed inset-0 bg-slate-900/50 z-40 transition-opacity duration-200",
          isDrawerOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={() => setIsDrawerOpen(false)}
        aria-hidden="true"
      />

      {/* Sliding Navigation Drawer */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 w-72 bg-slate-900 text-slate-300 z-50 shadow-2xl flex flex-col transition-transform duration-200 ease-in-out",
          isDrawerOpen ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Sidebar navigation drawer"
      >
        {/* Drawer Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800 bg-slate-900">
          <div className="flex items-center gap-2 font-bold text-lg text-white tracking-tight">
            <Shield className="h-6 w-6 text-blue-400" />
            <span>PolicyPilot</span>
          </div>

          <button
            type="button"
            onClick={() => setIsDrawerOpen(false)}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Customer Identity Section */}
        <div className="px-5 py-4 border-b border-slate-800 bg-slate-950/40">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            {t("nav.signedInAs")}
          </p>
          <p className="text-sm font-medium text-white truncate">
            {user?.full_name || user?.email}
          </p>
          <div className="mt-1.5">
            {isEmployee ? (
              <span className={cn(
                "inline-flex items-center rounded px-2 py-0.5 text-xs font-medium",
                isPending ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
              )}>
                {isPending ? t("nav.verificationPending") : t("nav.employee")}
              </span>
            ) : (
              <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-blue-900/60 text-blue-200 border border-blue-700/50">
                {t("nav.customer")}
              </span>
            )}
          </div>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto py-3 px-3 space-y-5">
          <nav className="space-y-5">
            {navGroups.map((group) => (
              <div key={group.label} className="space-y-1">
                <div className="px-3 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider select-none">
                  {group.label}
                </div>
                {group.items.map((item) => {
                  const isActive = isItemActive(item.href);
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      onClick={() => setIsDrawerOpen(false)}
                      className={cn(
                        "group flex items-center px-3 py-2 text-xs font-medium rounded-md transition-colors",
                        isActive
                          ? "bg-slate-800 text-white font-semibold border-l-2 border-blue-500"
                          : "text-slate-300 hover:bg-slate-800 hover:text-white"
                      )}
                    >
                      <item.icon
                        className={cn(
                          "flex-shrink-0 -ml-0.5 mr-3 h-4 w-4",
                          isActive ? "text-blue-400" : "text-slate-400 group-hover:text-slate-300"
                        )}
                        aria-hidden="true"
                      />
                      <span className="truncate">{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>
        </div>

        {/* Drawer Footer / Sign Out */}
        <div className="p-4 border-t border-slate-800 bg-slate-900">
          <button
            type="button"
            onClick={() => {
              setIsDrawerOpen(false);
              logout();
            }}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
          >
            <LogOut className="h-5 w-5 text-slate-400" />
            <span>{t("nav.signOut")}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Warning Banner if pending */}
        {isEmployee && isPending && (
          <div className="bg-amber-50 border-b border-amber-200 p-4">
            <div className="flex max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-amber-500" aria-hidden="true" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-amber-800">Verification Pending</h3>
                <div className="mt-1 text-sm text-amber-700">
                  <p>
                    Your employee access request is currently under review. Full operational functionality will be available once authorized.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <main className="flex-1 relative z-0 focus:outline-none">
          <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>

      {/* Centered Language Selection Modal (Facebook-inspired) */}
      {isLanguageModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="language-modal-title"
        >
          {/* Backdrop Dark Overlay */}
          <div 
            className="fixed inset-0 bg-slate-900/60 transition-opacity animate-in fade-in-50 duration-150"
            onClick={() => {
              if (!isUpdatingLang) setIsLanguageModalOpen(false);
            }}
            aria-hidden="true"
          />

          {/* Modal Container */}
          <div className="relative bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden z-10 animate-in fade-in-50 zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                  <Globe className="h-5 w-5" />
                </div>
                <div>
                  <h2 id="language-modal-title" className="text-sm font-bold text-slate-900 leading-tight">
                    {t("languageModal.title")}
                  </h2>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {t("languageModal.subtitle")}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsLanguageModalOpen(false)}
                disabled={isUpdatingLang}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body: Suggested Languages */}
            <div className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  {t("languageModal.suggestedLanguages")}
                </span>
                <span className="text-[10px] text-slate-400 font-medium">
                  {t("languageModal.supportedNotice")}
                </span>
              </div>

              {/* Language Selection Grid (Responsive 2-column Facebook-style grid) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {supportedLanguages.map((lang) => {
                  const selected = lang.code === language;
                  return (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={async () => {
                        await setLanguage(lang.code);
                        setIsLanguageModalOpen(false);
                      }}
                      disabled={isUpdatingLang}
                      className={cn(
                        "flex items-center justify-between px-3.5 py-2.5 rounded-lg border text-left transition-all",
                        selected
                          ? "bg-blue-50/80 border-blue-500 ring-1 ring-blue-500 shadow-sm"
                          : "border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-800"
                      )}
                    >
                      <div className="flex flex-col">
                        <span className={cn(
                          "text-sm leading-tight",
                          selected ? "font-bold text-slate-900" : "font-medium text-slate-800"
                        )}>
                          {lang.nativeName}
                        </span>
                        <span className="text-[11px] text-slate-500">
                          {lang.name} ({lang.code})
                        </span>
                      </div>

                      {selected && (
                        <div className="h-5 w-5 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-sm">
                          <Check className="h-3 w-3 stroke-[3]" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Notice */}
              <div className="mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-600 text-[11px] leading-relaxed">
                <p>
                  <span className="font-semibold text-slate-800">PolicyPilot: </span>
                  {t("languageModal.note")}
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 bg-slate-50/70 border-t border-slate-100 flex items-center justify-end">
              <button
                type="button"
                onClick={() => setIsLanguageModalOpen(false)}
                disabled={isUpdatingLang}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 rounded-md transition-colors"
              >
                {t("languageModal.close")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
