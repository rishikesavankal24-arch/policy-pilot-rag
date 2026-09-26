"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAdminAuth } from "@/contexts/AdminAuthContext";
import { 
  ShieldCheck, 
  LayoutDashboard, 
  UserCheck, 
  Users, 
  FileText, 
  ClipboardList, 
  Building2, 
  KeyRound, 
  Activity, 
  LogOut, 
  Menu, 
  X,
  Lock,
  ChevronRight,
  BookOpen,
  Landmark
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAdmin, isLoading, logout } = useAdminAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  // Auto redirect to login if unauthenticated and not loading
  React.useEffect(() => {
    if (!isLoading && !isAdmin) {
      router.push("/login");
    }
  }, [isLoading, isAdmin, router]);

  const navSections = [
    {
      title: "OVERVIEW",
      items: [
        { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      ]
    },
    {
      title: "POLICY MANAGEMENT",
      items: [
        { name: "Policies", href: "/policies", icon: BookOpen },
        { name: "Regulatory Authorities", href: "/regulatory-authorities", icon: Landmark },
      ]
    },
    {
      title: "USER MANAGEMENT",
      items: [
        { name: "Employee Verification", href: "/employee-verification", icon: UserCheck },
        { name: "Employees", href: "/employees", icon: Users },
        { name: "Customers", href: "/customers", icon: Users },
      ]
    },
    {
      title: "OPERATIONS",
      items: [
        { name: "Applications", href: "/applications", icon: FileText },
        { name: "Assignments", href: "/assignments", icon: ClipboardList },
        { name: "Institutions", href: "/institutions", icon: Building2 },
      ]
    },
    {
      title: "SECURITY",
      items: [
        { name: "Permissions", href: "/permissions", icon: KeyRound },
        { name: "Operational Monitoring", href: "/monitoring", icon: Activity },
        { name: "Audit", href: "/audit", icon: ShieldCheck },
      ]
    }
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070D1E] flex items-center justify-center text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs uppercase tracking-wider font-mono">Authenticating Administrative Console...</span>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null; // Will redirect via useEffect
  }

  return (
    <div className="min-h-screen bg-[#F1F5F9] text-slate-900 flex flex-col font-sans">
      {/* Top Administrative Banner */}
      <div className="bg-[#070D1E] text-slate-300 text-[11px] font-medium tracking-wider px-4 sm:px-6 py-1.5 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span className="uppercase font-semibold text-slate-200">PolicyPilot • Internal Administrative Console</span>
          <span className="hidden sm:inline-block text-slate-600">|</span>
          <span className="hidden sm:inline-block text-slate-400 font-mono text-[10px]">INTERNAL SUPERVISORY ACCESS</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-slate-400 uppercase tracking-wider font-mono">
          <span className="bg-slate-800 px-2 py-0.5 rounded text-amber-300 border border-amber-500/20">
            NODE: PP-ADMIN-01
          </span>
        </div>
      </div>

      {/* Main Administrative Header */}
      <header className="sticky top-0 z-30 bg-[#0F172A] border-b border-slate-800 text-white shadow-md">
        <div className="px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800"
              aria-label="Toggle Navigation"
            >
              {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <Link href="/dashboard" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center text-slate-950 font-bold">
                <ShieldCheck className="h-5 w-5 text-slate-950" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
                  PolicyPilot <span className="text-[10px] font-bold px-1.5 py-0.2 bg-amber-400/20 text-amber-300 border border-amber-400/40 rounded font-mono">ADMIN</span>
                </span>
                <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wide">
                  Central Governance & Supervisory Portal
                </span>
              </div>
            </Link>
          </div>

          {/* Admin User Info & Logout */}
          <div className="flex items-center gap-3 text-xs">
            <div className="hidden sm:flex flex-col text-right">
              <span className="font-semibold text-slate-200">{user?.full_name || "System Administrator"}</span>
              <span className="text-[10px] font-mono text-amber-400">{user?.email}</span>
            </div>

            <button
              onClick={async () => {
                await logout();
                router.push("/login");
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950 hover:text-rose-300 hover:border-rose-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Viewport: Sidebar + Content */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* Left Navigation Sidebar */}
        <aside className={cn(
          "w-full md:w-64 bg-[#0B132B] border-r border-slate-800 flex flex-col shrink-0 text-slate-300",
          isMobileMenuOpen ? "block" : "hidden md:block"
        )}>
          <div className="p-4 border-b border-slate-800">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
              ADMIN CONSOLE
            </p>
          </div>

          <nav className="flex-1 p-3 space-y-4 overflow-y-auto text-xs font-medium">
            {navSections.map((section) => (
              <div key={section.title} className="space-y-1">
                <div className="px-3 py-1 text-[10px] font-bold font-mono tracking-wider text-slate-500 uppercase">
                  {section.title}
                </div>
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                        isActive
                          ? "bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                      )}
                    >
                      <Icon className={cn("h-4 w-4", isActive ? "text-amber-400" : "text-slate-400")} />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </nav>

          <div className="p-4 border-t border-slate-800 text-[11px] text-slate-500 font-mono">
            <div>PORT: 3001</div>
            <div>ROLE: ROLE_ADMIN</div>
          </div>
        </aside>

        {/* Workspace Body */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Operational Footer */}
      <footer className="bg-[#070D1E] border-t border-slate-800 text-slate-500 text-[11px] py-3 px-4 sm:px-6 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>PolicyPilot Administrative Console v1.0 • Isolated Frontend (:3001)</span>
          <span>FastAPI Backend Connected (:8000)</span>
        </div>
      </footer>
    </div>
  );
}
