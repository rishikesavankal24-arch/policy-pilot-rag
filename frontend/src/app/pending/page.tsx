"use client";

import { useAuth } from "@/contexts/AuthContext";
import { Clock, Shield } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function PendingPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      <div className="flex flex-1 flex-col justify-center py-12 px-4 sm:px-6 lg:flex-none lg:px-20 xl:px-24">
        <div className="mx-auto w-full max-w-sm lg:w-96 text-center">
          <div className="mb-10 flex flex-col items-center">
            <Link href="/" className="flex items-center gap-2 text-primary font-bold text-2xl tracking-tight mb-8">
              <Shield className="h-8 w-8 text-blue-600" />
              PolicyPilot
            </Link>
            <Clock className="h-16 w-16 text-amber-500 mb-6" />
            <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Account Pending</h2>
            <p className="mt-4 text-sm text-slate-600 leading-relaxed">
              Your request for employee access has been successfully submitted. It is currently awaiting administrative authorization. 
              <br/><br/>
              You will receive an email once your request has been reviewed.
            </p>
          </div>

          <button
            onClick={logout}
            className="w-full flex justify-center py-3 px-4 border border-slate-300 rounded-md shadow-sm text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Sign out
          </button>
        </div>
      </div>
      <div className="hidden lg:block relative w-0 flex-1 bg-slate-900">
        <div className="absolute inset-0 h-full w-full bg-slate-900 flex flex-col items-center justify-center p-12">
          <div className="max-w-lg text-center">
            <Shield className="h-20 w-20 text-slate-700 mx-auto mb-8" />
            <h2 className="text-2xl font-bold text-white mb-4">Strict Access Control</h2>
            <p className="text-slate-400 text-lg leading-relaxed">
              All employee access requests must be manually verified to ensure compliance and security.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
