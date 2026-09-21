import React from "react";
import Link from "next/link";
import { Shield, Lock, FileCheck, ArrowRight, Activity } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary font-bold text-xl tracking-tight">
            <Shield className="h-6 w-6 text-blue-600" />
            PolicyPilot
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 border border-slate-300 bg-white hover:bg-slate-100 h-9 px-4 py-2 text-slate-700"
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <div className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm text-blue-800 mb-8 font-medium">
          <Activity className="mr-2 h-4 w-4" />
          Enterprise Compliance Infrastructure
        </div>
        
        <h1 className="max-w-4xl text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl md:text-6xl lg:text-7xl mb-6">
          Policy-driven compliance infrastructure for modern banking.
        </h1>
        
        <p className="max-w-2xl text-lg sm:text-xl text-slate-600 mb-10 leading-relaxed">
          Securely adapt to changing regulations, streamline document governance, and ensure real-time institutional compliance with enterprise-grade protection.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-24">
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring bg-blue-600 text-white hover:bg-blue-700 h-11 px-8 py-2 shadow-sm"
          >
            Access Platform
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
          <a
            href="#features"
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 h-11 px-8 py-2 shadow-sm"
          >
            Learn More
          </a>
        </div>

        {/* Feature Grid */}
        <div id="features" className="grid sm:grid-cols-3 gap-8 max-w-6xl w-full text-left">
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col">
            <div className="h-12 w-12 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-4 border border-blue-100">
              <Lock className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Secure by Default</h3>
            <p className="text-slate-600 text-sm leading-relaxed flex-1">
              Strict role-based access controls separate customer data from internal operational reviews. Employee access requires explicit authorization.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col">
            <div className="h-12 w-12 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4 border border-emerald-100">
              <FileCheck className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Regulatory Auditing</h3>
            <p className="text-slate-600 text-sm leading-relaxed flex-1">
              Maintains an immutable record of compliance checks and policy adaptations, ensuring readiness for internal and external audits.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col">
            <div className="h-12 w-12 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4 border border-indigo-100">
              <Activity className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Adaptive Workflows</h3>
            <p className="text-slate-600 text-sm leading-relaxed flex-1">
              PolicyPilot dynamically aligns application workflows with the latest institutional policies, reducing processing friction.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 mt-auto border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center gap-2 mb-4 md:mb-0">
            <Shield className="h-5 w-5 text-slate-500" />
            <span className="font-semibold text-slate-300">PolicyPilot</span>
          </div>
          <div className="text-sm">
            &copy; {new Date().getFullYear()} PolicyPilot Enterprise Systems. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
