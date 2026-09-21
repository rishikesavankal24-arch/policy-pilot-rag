"use client";

import { useAuth } from "@/contexts/AuthContext";
import { Shield, Eye, EyeOff, Briefcase, User, Building, MapPin, Hash, BookOpen, Mail } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const { isLoading, checkAuth, user, logout } = useAuth();
  const router = useRouter();
  const [isMobileStub, setIsMobileStub] = useState(false);

  const [role, setRole] = useState<"CUSTOMER" | "EMPLOYEE">("CUSTOMER");
  
  useEffect(() => {
    const savedRole = localStorage.getItem("selectedRole");
    if (savedRole && (savedRole.toUpperCase() === "CUSTOMER" || savedRole.toUpperCase() === "EMPLOYEE")) {
      setRole(savedRole.toUpperCase() as "CUSTOMER" | "EMPLOYEE");
    }
  }, []);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [language, setLanguage] = useState("English");
  const [consentAccepted, setConsentAccepted] = useState(false);

  // Employee specific
  const [organization, setOrganization] = useState("");
  const [department, setDepartment] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [designation, setDesignation] = useState("");
  const [workEmail, setWorkEmail] = useState("");

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);


  
  useEffect(() => {
    if (user) {
      if (user.authentication_provider === "mobile") {
        setIsMobileStub(true);
        if (user.phone_number) {
          // Remove the +91 prefix for the input since it has a hardcoded span
          const num = user.phone_number.startsWith("+91") 
            ? user.phone_number.substring(3) 
            : user.phone_number;
          setPhoneNumber(num);
        }
        if (user.email && !user.email.endsWith("@mobile.policypilot.internal")) {
          setEmail(user.email);
        }
      }
    }
  }, [user]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (!email || !password || !confirmPassword || !fullName || !phoneNumber) {
      setError("Please fill in all required fields.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (!consentAccepted) {
      setError("You must accept the terms and privacy policy.");
      return;
    }

    if (role === "EMPLOYEE") {
      if (!organization || !department || !employeeId || !designation || !workEmail) {
        setError("Please fill in all employee details.");
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const payload = {
        email,
        password,
        role,
        full_name: fullName,
        phone_number: phoneNumber,
        language,
        consent_accepted: consentAccepted,
        ...(role === "EMPLOYEE" ? {
          organization,
          department,
          employee_id: employeeId,
          designation,
          work_email: workEmail
        } : {})
      };

      // 1. Register the user
      const registerRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/auth/local/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const registerData = await registerRes.json();
      if (!registerRes.ok) {
        // Detailed error parsing
        let errorMsg = "Registration failed";
        if (registerData.detail) {
          if (typeof registerData.detail === 'string') {
            errorMsg = registerData.detail;
          } else if (Array.isArray(registerData.detail)) {
            errorMsg = registerData.detail.map((err: any) => err.msg || err.message).join(", ");
          }
        }
        throw new Error(errorMsg);
      }

      // 2. Automatically log them in to establish session
      const loginRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/auth/local/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ identifier: email, password }),
      });

      const loginData = await loginRes.json();
      if (!loginRes.ok) {
        router.push("/login?message=Registration successful. Please log in.");
        return;
      }

      await checkAuth();
      router.push(loginData.redirect || "/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isEmailTaken = error.toLowerCase().includes("email already registered");

  const handleGoogleLogin = () => {
    localStorage.setItem("selectedRole", role.toLowerCase());
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/auth/google/login`;
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC]">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#1E293B]"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans selection:bg-[#0F172A] selection:text-white">
      <div className="flex flex-1 flex-col justify-center py-12 px-4 sm:px-6 lg:flex-none lg:w-[560px] xl:w-[640px] lg:px-20 xl:px-24 bg-white border-r border-[#E2E8F0] shadow-[1px_0_15px_rgba(0,0,0,0.03)] z-10 overflow-y-auto">
        <div className="mx-auto w-full max-w-sm lg:w-[400px]">
          
          <div className="mb-10">
            <div className="flex items-center gap-2.5 text-[#0F172A] font-bold text-2xl tracking-tight mb-10">
              <Shield className="h-7 w-7 text-[#2563EB]" strokeWidth={2.5} />
              PolicyPilot
            </div>
            <h2 className="text-2xl font-bold text-[#0F172A] tracking-tight">Create your account</h2>
            <p className="mt-2 text-sm text-[#64748B] font-medium">
              Start your secure enterprise banking setup
            </p>
          </div>

          <div className="mt-8">
            {error && !isEmailTaken && (
              <div className="mb-6 bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] px-4 py-3 rounded-md text-sm font-medium" role="alert">
                {error}
              </div>
            )}

            {isEmailTaken && (
              <div className="mb-6 bg-amber-50 border border-amber-200 p-4 rounded-md flex flex-col gap-3">
                <div className="text-sm text-amber-800 font-medium">
                  This email is already registered. Please sign in to your existing PolicyPilot account.
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="self-start inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-amber-600 hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 transition-colors"
                >
                  Go to Sign In
                </button>
              </div>
            )}

            <form onSubmit={handleRegister} className="space-y-6">
              
              {/* Role Selection */}
              <div>
                <label className="block text-sm font-semibold text-[#334155] mb-2">
                  I am registering as a:
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setRole("CUSTOMER")}
                    className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                      role === "CUSTOMER" 
                        ? "border-[#2563EB] bg-[#EFF6FF] text-[#1E3A8A]" 
                        : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1]"
                    }`}
                  >
                    <User className="h-6 w-6 mb-2" />
                    <span className="font-semibold text-sm">Customer</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRole("EMPLOYEE")}
                    className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                      role === "EMPLOYEE" 
                        ? "border-[#2563EB] bg-[#EFF6FF] text-[#1E3A8A]" 
                        : "border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1]"
                    }`}
                  >
                    <Briefcase className="h-6 w-6 mb-2" />
                    <span className="font-semibold text-sm">Employee</span>
                  </button>
                </div>
              </div>

              {!isMobileStub && (
                <div className="mt-8">
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-[#E2E8F0]" />
                    </div>
                    <div className="relative flex justify-center text-xs font-semibold">
                      <span className="bg-white px-2 text-[#94A3B8] uppercase tracking-wider">Continue With</span>
                    </div>
                  </div>

                  <div className="mt-6 space-y-3">
                    <button
                      type="button"
                      onClick={handleGoogleLogin}
                      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-[#E2E8F0] shadow-sm text-sm font-semibold rounded-md text-[#334155] bg-white hover:bg-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#E2E8F0] transition-colors"
                    >
                      <svg className="h-4 w-4" aria-hidden="true" viewBox="0 0 24 24">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                      Continue with Google
                    </button>
                    
                    <button
                      type="button"
                      onClick={() => {
                        localStorage.setItem("selectedRole", role.toLowerCase());
                        router.push("/login");
                      }}
                      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-[#E2E8F0] shadow-sm text-sm font-semibold rounded-md text-[#334155] bg-white hover:bg-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#E2E8F0] transition-colors"
                    >
                      <span className="font-semibold text-xl leading-none">📱</span>
                      Continue with Mobile OTP
                    </button>
                  </div>
                  
                  <div className="relative mt-8 mb-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-[#E2E8F0]" />
                    </div>
                    <div className="relative flex justify-center text-xs font-semibold">
                      <span className="bg-white px-2 text-[#94A3B8] uppercase tracking-wider">Or register manually</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Core Information */}
              <div className="space-y-4 pt-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#94A3B8] border-b border-[#E2E8F0] pb-2">
                  Basic Information
                </h3>
                
                <div>
                  <label htmlFor="fullName" className="block text-sm font-semibold text-[#334155] mb-1.5">Full Name</label>
                  <input
                    type="text"
                    id="fullName"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-semibold text-[#334155] mb-1.5">Email Address</label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="phoneNumber" className="block text-sm font-semibold text-[#334155] mb-1.5">Mobile Number</label>
                  <div className="flex rounded-md shadow-sm">
                    <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-[#CBD5E1] bg-[#F1F5F9] text-[#64748B] sm:text-sm font-medium">+91</span>
                    <input
                      type="tel"
                      id="phoneNumber"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      className={`flex-1 block w-full px-3.5 py-2.5 rounded-none rounded-r-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors ${isMobileStub ? "bg-[#F1F5F9] text-gray-500 cursor-not-allowed" : ""}`}
                      required
                      readOnly={isMobileStub}
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="language" className="block text-sm font-semibold text-[#334155] mb-1.5">Preferred Language</label>
                  <select
                    id="language"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors bg-white"
                  >
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Marathi">Marathi</option>
                  </select>
                </div>
              </div>

              {/* Employee Information */}
              {role === "EMPLOYEE" && (
                <div className="space-y-4 pt-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-[#94A3B8] border-b border-[#E2E8F0] pb-2">
                    Employment Details
                  </h3>
                  
                  <div>
                    <label htmlFor="organization" className="block text-sm font-semibold text-[#334155] mb-1.5">Organization</label>
                    <input type="text" id="organization" value={organization} onChange={(e) => setOrganization(e.target.value)} className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors" required={role === "EMPLOYEE"} />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="department" className="block text-sm font-semibold text-[#334155] mb-1.5">Department</label>
                      <input type="text" id="department" value={department} onChange={(e) => setDepartment(e.target.value)} className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors" required={role === "EMPLOYEE"} />
                    </div>
                    <div>
                      <label htmlFor="designation" className="block text-sm font-semibold text-[#334155] mb-1.5">Designation</label>
                      <input type="text" id="designation" value={designation} onChange={(e) => setDesignation(e.target.value)} className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors" required={role === "EMPLOYEE"} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="employeeId" className="block text-sm font-semibold text-[#334155] mb-1.5">Employee ID</label>
                      <input type="text" id="employeeId" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors" required={role === "EMPLOYEE"} />
                    </div>
                    <div>
                      <label htmlFor="workEmail" className="block text-sm font-semibold text-[#334155] mb-1.5">Work Email</label>
                      <input type="email" id="workEmail" value={workEmail} onChange={(e) => setWorkEmail(e.target.value)} className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors" required={role === "EMPLOYEE"} />
                    </div>
                  </div>
                </div>
              )}

              {/* Password Section */}
              <div className="space-y-4 pt-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#94A3B8] border-b border-[#E2E8F0] pb-2">
                  Security
                </h3>
                
                <div>
                  <label htmlFor="password" className="block text-sm font-semibold text-[#334155] mb-1.5">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      id="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors pr-10"
                      placeholder="At least 8 characters"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#64748B] hover:text-[#334155] transition-colors"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-semibold text-[#334155] mb-1.5">Confirm Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      id="confirmPassword"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className="flex items-center h-5">
                    <input
                      type="checkbox"
                      checked={consentAccepted}
                      onChange={(e) => setConsentAccepted(e.target.checked)}
                      className="w-4 h-4 text-[#2563EB] border-[#CBD5E1] rounded focus:ring-[#2563EB]"
                    />
                  </div>
                  <span className="text-sm text-[#475569] leading-relaxed group-hover:text-[#334155] transition-colors">
                    I acknowledge that I have read and agree to the{" "}
                    <a href="#" className="text-[#2563EB] hover:underline font-semibold">Terms of Service</a> and{" "}
                    <a href="#" className="text-[#2563EB] hover:underline font-semibold">Privacy Policy</a>, and I consent to the processing of my data for compliance purposes.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F172A] disabled:opacity-50 transition-colors mt-4"
              >
                {isSubmitting ? "Creating account..." : role === "EMPLOYEE" ? "Submit for Verification" : "Create Account"}
              </button>
            </form>

            <div className="mt-10 pt-6 border-t border-[#E2E8F0] text-center">
              <p className="text-sm font-medium text-[#64748B]">
                Already have an account?{" "}
                <button 
                  type="button" 
                  onClick={logout} 
                  className="text-[#2563EB] hover:text-[#1D4ED8] font-semibold transition-colors"
                >
                  Sign in &rarr;
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Right Column: Brand Presentation */}
      <div className="hidden lg:flex relative w-0 flex-1 bg-[#0F172A] flex-col justify-between p-12">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:24px_24px]"></div>
        
        <div className="relative z-10 max-w-xl mx-auto mt-24">
          <h1 className="text-4xl font-bold text-white tracking-tight mb-6 leading-tight">
            Deploy Policy Protocols <br/>
            <span className="text-[#3B82F6]">in Minutes</span>
          </h1>
          <p className="text-[#94A3B8] text-lg font-medium leading-relaxed max-w-md">
            Join the secure network for institutional compliance, risk assessment, and identity verification.
          </p>
        </div>

        <div className="relative z-10 text-xs font-medium text-[#475569] max-w-xl mx-auto w-full">
          &copy; {new Date().getFullYear()} PolicyPilot Enterprise. All rights reserved.
        </div>
      </div>
    </div>
  );
}
