"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Shield, Building, User, AlertCircle, CheckCircle2 } from "lucide-react";

export default function OnboardingPage() {
  const { user, checkAuth } = useAuth();
  const router = useRouter();
  
  const [role, setRole] = useState<"customer" | "employee">("customer");

  // IsMounted to strictly prevent any hydration mismatch
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => {
    setIsMounted(true);
    const savedRole = localStorage.getItem("selectedRole");
    if (savedRole && (savedRole.toLowerCase() === "customer" || savedRole.toLowerCase() === "employee")) {
      setRole(savedRole.toLowerCase() as "customer" | "employee");
    }
  }, []);
  
  // Base Form
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [language, setLanguage] = useState("en");
  const [consent, setConsent] = useState(false);
  
  useEffect(() => {
    if (user) {
      if (user.full_name && user.full_name !== "Mobile User" && user.full_name !== "Local User") {
        setFullName(user.full_name);
      }
      if (user.email && !user.email.endsWith("@mobile.policypilot.internal")) {
        setEmail(user.email);
      }
      if (user.phone_number) {
        setPhone(user.phone_number);
      }
    }
  }, [user]);
  
  // Employee Form
  const [org, setOrg] = useState("");
  const [dept, setDept] = useState("");
  const [empId, setEmpId] = useState("");
  const [designation, setDesignation] = useState("");
  const [workEmail, setWorkEmail] = useState("");
  const [reason, setReason] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setError("");

    if (!consent) {
      setError("Please accept the Terms and Conditions to continue.");
      return;
    }

    setIsSubmitting(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const endpoint = role === "customer" ? "/onboarding/customer" : "/onboarding/employee";
      const payload = role === "customer" 
        ? { full_name: fullName, email, phone_number: phone, language, consent_accepted: consent }
        : { full_name: fullName, email, phone_number: phone, language, consent_accepted: consent, organization: org, department: dept, employee_id: empId, designation, work_email: workEmail, reason };

      // Make API call sending cookies for session
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errorMessage = "Failed to submit onboarding data";
        const errorData = await res.json().catch(() => null);
        if (errorData && errorData.detail) {
          if (typeof errorData.detail === "string") {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // Handle FastAPI validation array
            errorMessage = errorData.detail.map((e: any) => `${e.loc?.join(".")}: ${e.msg}`).join(", ");
          }
        }
        throw new Error(errorMessage);
      }

      await checkAuth(); // Update local session
      setIsSuccess(true);
      
      // Delay navigation slightly for UX
      setTimeout(() => {
        if (role === "employee") {
          router.push("/pending");
        } else {
          router.push("/dashboard");
        }
      }, 1500);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
      setIsSubmitting(false); // Only set false on error so success state persists
    }
  };

  if (!isMounted) return null; // Avoid hydration mismatch completely

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary font-bold text-xl tracking-tight">
            <Shield className="h-6 w-6 text-blue-600" />
            PolicyPilot
          </div>
          <div className="text-sm font-medium text-slate-500">
            Account Registration
          </div>
        </div>
      </header>

      <main className="flex-1 py-12 px-4 sm:px-6 lg:px-8 max-w-3xl mx-auto w-full">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Complete Your Profile</h1>
          <p className="mt-2 text-sm text-slate-600">
            Welcome, <span className="font-medium text-slate-900">{user?.full_name || "User"}</span>. Please provide the required information below to securely access the platform.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
          <form onSubmit={handleSubmit}>

            <div className="p-6 space-y-6">
                {error && (
                  <div className="bg-red-50 border border-red-200 p-4 rounded-md flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                    <div className="text-sm text-red-700 font-medium">{error}</div>
                  </div>
                )}

                {isSuccess && (
                  <div className="bg-green-50 border border-green-200 p-4 rounded-md flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                    <div className="text-sm text-green-700 font-medium">Registration successful! Redirecting...</div>
                  </div>
                )}

                <div className="space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                      <label htmlFor="fullName" className="block text-sm font-medium text-slate-700">Full Name</label>
                      <input
                        id="fullName"
                        type="text"
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                        placeholder="John Doe"
                      />
                    </div>
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-slate-700">Email Address</label>
                      <input
                        id="email"
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                        placeholder="john@example.com"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                      <label htmlFor="phone" className="block text-sm font-medium text-slate-700">Phone Number</label>
                      <div className="mt-1 flex rounded-md shadow-sm">
                        <span className="inline-flex items-center rounded-l-md border border-r-0 border-slate-300 bg-slate-50 px-3 text-slate-500 sm:text-sm font-medium">
                          +91
                        </span>
                        <input
                          id="phone"
                          type="tel"
                          required
                          pattern="[0-9]{10}"
                          title="Please enter a valid 10-digit mobile number"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                          className="block w-full min-w-0 flex-1 rounded-none rounded-r-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                          placeholder="9876543210"
                        />
                      </div>
                    </div>
                    <div>
                      <label htmlFor="language" className="block text-sm font-medium text-slate-700">Preferred Language</label>
                      <select
                        id="language"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm bg-white"
                      >
                        <option value="en">English</option>
                        <option value="ta">தமிழ்</option>
                        <option value="hi">हिंदी</option>
                      </select>
                    </div>
                  </div>
                </div>

                {role === "employee" && (
                  <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                      <div>
                        <label htmlFor="org" className="block text-sm font-medium text-slate-700">Organization / Institution</label>
                        <input id="org" type="text" required value={org} onChange={e => setOrg(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" />
                      </div>
                      <div>
                        <label htmlFor="dept" className="block text-sm font-medium text-slate-700">Department</label>
                        <input id="dept" type="text" required value={dept} onChange={e => setDept(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" />
                      </div>
                      <div>
                        <label htmlFor="empId" className="block text-sm font-medium text-slate-700">Employee ID</label>
                        <input id="empId" type="text" required value={empId} onChange={e => setEmpId(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" />
                      </div>
                      <div>
                        <label htmlFor="designation" className="block text-sm font-medium text-slate-700">Designation / Title</label>
                        <input id="designation" type="text" required value={designation} onChange={e => setDesignation(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="workEmail" className="block text-sm font-medium text-slate-700">Corporate Email Address</label>
                      <input id="workEmail" type="email" required value={workEmail} onChange={e => setWorkEmail(e.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" placeholder="name@institution.com" />
                    </div>

                    <div>
                      <label htmlFor="reason" className="block text-sm font-medium text-slate-700">Business Justification</label>
                      <textarea id="reason" required value={reason} onChange={e => setReason(e.target.value)} rows={3} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm" placeholder="Reason for requiring platform access..."></textarea>
                    </div>

                    <div className="bg-blue-50 border border-blue-200 rounded-md p-4 flex gap-3">
                      <Shield className="h-5 w-5 text-blue-600 flex-shrink-0" />
                      <div>
                        <h4 className="text-sm font-medium text-blue-900">Verification Required</h4>
                        <p className="text-xs text-blue-700 mt-1">
                          Employee access requests are subject to strict administrative review. Submitting this form will place your account in a pending state until identity and authorization are confirmed.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-start">
                    <div className="flex items-center h-5">
                      <input
                        id="consent"
                        type="checkbox"
                        required
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                    </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="consent" className="font-medium text-slate-700">Terms and Conditions</label>
                      <p className="text-slate-500">I agree to the processing of my data in accordance with the corporate Privacy Policy.</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200 flex justify-end">
                  <button
                    type="submit"
                    disabled={isSubmitting || isSuccess}
                    className="inline-flex justify-center py-2 px-6 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSubmitting ? "Submitting..." : isSuccess ? "Success!" : "Submit Registration"}
                  </button>
                </div>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
