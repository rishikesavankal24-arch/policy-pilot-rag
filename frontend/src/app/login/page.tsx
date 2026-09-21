"use client";

import { useAuth } from "@/contexts/AuthContext";
import { setActiveSessionToken, getPortalScope } from "@/lib/session";
import { Shield, Eye, EyeOff, Smartphone, Mail } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const { isLoading, checkAuth } = useAuth();
  const router = useRouter();

  const [authMethod, setAuthMethod] = useState<"local" | "mobile_otp">("local");
  
  // Local Auth State
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // OTP Auth State
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [expiryTimer, setExpiryTimer] = useState(0);

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (cooldown > 0) {
      timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [cooldown]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (expiryTimer > 0) {
      timer = setTimeout(() => setExpiryTimer(expiryTimer - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [expiryTimer]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleGoogleLogin = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/google/login`;
  };

  const [portal, setPortal] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search).get("portal");
      setPortal(p);
    }
  }, []);

  const handleLocalLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (!identifier || !password) {
      setError("Please enter your credentials.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/local/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ identifier, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Invalid credentials");
      }

      if (data.session_token) {
        setActiveSessionToken(data.session_token, data.role);
      }

      const hasEmp = typeof window !== "undefined" && !!localStorage.getItem("employee_session_token");
      const hasCust = typeof window !== "undefined" && !!localStorage.getItem("customer_session_token");

      console.log("[DEBUG LOGIN RESPONSE]", {
        currentPathname: typeof window !== "undefined" ? window.location.pathname : "/login",
        requestedPortal: portal,
        returnedRole: data.role,
        selectedPortalScope: getPortalScope(),
        hasEmployeeToken: hasEmp,
        hasCustomerToken: hasCust,
      });

      await checkAuth();
      const target = data.redirect || (data.role === "EMPLOYEE" ? "/employee/dashboard" : "/dashboard");

      console.log("[DEBUG LOGIN REDIRECT]", {
        currentPathname: typeof window !== "undefined" ? window.location.pathname : "/login",
        requestedPortal: portal,
        returnedRole: data.role,
        selectedPortalScope: getPortalScope(),
        hasEmployeeToken: hasEmp,
        hasCustomerToken: hasCust,
        finalRedirectPath: target,
      });

      router.push(target);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    const cleaned = phoneNumber.replace(/\D/g, '');
    if (cleaned.length !== 10) {
      setError("Please enter a valid 10-digit mobile number.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/mobile/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: cleaned }),
      });

      const data = await res.json();
      if (!res.ok) {
        if (res.status === 429) {
          const retryAfter = data.detail?.retry_after_seconds || parseInt(res.headers.get("Retry-After") || "0", 10);
          if (retryAfter > 0) setCooldown(retryAfter);
        }
        throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message || "Failed to send OTP");
      }
      setSuccessMsg("OTP sent successfully");
      setStep("otp");
      setCooldown(60);
      setExpiryTimer(300);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (otp.length !== 6) {
      setError("Please enter the 6-digit OTP.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/mobile/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone_number: phoneNumber.replace(/\D/g, ''), otp }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to verify OTP");

      if (data.session_token) {
        setActiveSessionToken(data.session_token, data.role);
      }

      const hasEmp = typeof window !== "undefined" && !!localStorage.getItem("employee_session_token");
      const hasCust = typeof window !== "undefined" && !!localStorage.getItem("customer_session_token");

      console.log("[DEBUG OTP LOGIN RESPONSE]", {
        currentPathname: typeof window !== "undefined" ? window.location.pathname : "/login",
        requestedPortal: portal,
        returnedRole: data.role,
        selectedPortalScope: getPortalScope(),
        hasEmployeeToken: hasEmp,
        hasCustomerToken: hasCust,
      });

      await checkAuth();
      const target = data.redirect || (data.role === "EMPLOYEE" ? "/employee/dashboard" : "/dashboard");

      console.log("[DEBUG OTP REDIRECT]", {
        currentPathname: typeof window !== "undefined" ? window.location.pathname : "/login",
        requestedPortal: portal,
        returnedRole: data.role,
        selectedPortalScope: getPortalScope(),
        hasEmployeeToken: hasEmp,
        hasCustomerToken: hasCust,
        finalRedirectPath: target,
      });

      router.push(target);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
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
      {/* Left Column: Form */}
      <div className="flex flex-1 flex-col justify-center py-12 px-4 sm:px-6 lg:flex-none lg:w-[480px] xl:w-[560px] lg:px-20 xl:px-24 bg-white border-r border-[#E2E8F0] shadow-[1px_0_15px_rgba(0,0,0,0.03)] z-10">
        <div className="mx-auto w-full max-w-sm lg:w-[360px]">
          
          <div className="mb-10">
            <div className="flex items-center gap-2.5 text-[#0F172A] font-bold text-2xl tracking-tight mb-8">
              <Shield className="h-7 w-7 text-[#2563EB]" strokeWidth={2.5} />
              PolicyPilot
            </div>
            {portal === "employee" ? (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 text-amber-700 border border-amber-500/30 rounded-full text-xs font-semibold uppercase tracking-wider mb-3">
                Institutional Officer Portal
              </div>
            ) : null}
            <h2 className="text-2xl font-bold text-[#0F172A] tracking-tight">
              {portal === "employee" ? "Officer Sign In" : "Sign in"}
            </h2>
            <p className="mt-2 text-sm text-[#64748B] font-medium">
              {portal === "employee" 
                ? "Authorized institutional underwriters & bank officers" 
                : "Secure access to your compliance workspace"}
            </p>
          </div>

          <div className="mt-8">
            {error && (
              <div className="mb-6 bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] px-4 py-3 rounded-md text-sm font-medium" role="alert">
                {error}
              </div>
            )}

            {authMethod === "local" ? (
              <form onSubmit={handleLocalLogin} className="space-y-5">
                <div>
                  <label htmlFor="identifier" className="block text-sm font-semibold text-[#334155] mb-1.5">
                    Email or mobile number
                  </label>
                  <input
                    type="text"
                    id="identifier"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors"
                    placeholder="name@company.com"
                    required
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor="password" className="block text-sm font-semibold text-[#334155]">
                      Password
                    </label>
                    <Link href="/forgot-password" className="text-sm font-medium text-[#2563EB] hover:text-[#1D4ED8] transition-colors">
                      Forgot password?
                    </Link>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      id="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="block w-full px-3.5 py-2.5 rounded-md border border-[#CBD5E1] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors pr-10"
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

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F172A] disabled:opacity-50 transition-colors mt-2"
                >
                  {isSubmitting ? "Signing in..." : "Sign in"}
                </button>
              </form>
            ) : (
              /* OTP Form Flow */
              <div className="space-y-5">
                <button 
                  type="button" 
                  onClick={() => { setAuthMethod("local"); setError(""); }} 
                  className="text-sm font-medium text-[#2563EB] hover:text-[#1D4ED8] mb-2 inline-block"
                >
                  &larr; Back to password login
                </button>

                {step === "phone" ? (
                  <form onSubmit={handleSendOtp} className="space-y-5">
                    <div>
                      <label htmlFor="phone" className="block text-sm font-semibold text-[#334155] mb-1.5">
                        Mobile Number
                      </label>
                      <div className="flex rounded-md shadow-sm">
                        <span className="inline-flex items-center px-3 rounded-l-md border border-r-0 border-[#CBD5E1] bg-[#F1F5F9] text-[#64748B] sm:text-sm font-medium">
                          +91
                        </span>
                        <input
                          type="tel"
                          id="phone"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                          className="flex-1 block w-full px-3.5 py-2.5 rounded-none rounded-r-md border border-[#CBD5E1] text-[#0F172A] focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm outline-none transition-colors"
                          placeholder="10-digit mobile number"
                          maxLength={10}
                          required
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={isSubmitting || cooldown > 0}
                      className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F172A] disabled:opacity-50 transition-colors"
                    >
                      {isSubmitting ? "Sending..." : cooldown > 0 ? `Wait ${formatTime(cooldown)}` : "Send OTP"}
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleVerifyOtp} className="space-y-5">
                    {successMsg && (
                      <div className="bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] px-4 py-3 rounded-md text-sm font-medium">
                        {successMsg}
                      </div>
                    )}
                    <div>
                      <div className="flex justify-between items-end mb-1.5">
                        <label htmlFor="otp" className="block text-sm font-semibold text-[#334155]">
                          6-digit OTP
                        </label>
                        <span className="text-xs font-medium text-[#64748B]">
                          Sent to {phoneNumber}
                        </span>
                      </div>
                      <input
                        type="text"
                        id="otp"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value)}
                        className="block w-full px-3.5 py-2.5 border border-[#CBD5E1] rounded-md focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] sm:text-sm tracking-widest text-center text-[#0F172A] font-medium outline-none transition-colors"
                        placeholder="• • • • • •"
                        maxLength={6}
                        required
                      />
                    </div>
                    
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F172A] disabled:opacity-50 transition-colors"
                    >
                      {isSubmitting ? "Verifying..." : "Verify OTP"}
                    </button>

                    <div className="text-center mt-3">
                      {expiryTimer > 0 ? (
                        <p className="text-xs font-medium text-[#64748B] mb-2">Expires in {formatTime(expiryTimer)}</p>
                      ) : (
                        <p className="text-xs font-medium text-[#EF4444] mb-2">OTP expired</p>
                      )}
                      <button
                        type="button"
                        disabled={cooldown > 0 || isSubmitting}
                        onClick={handleSendOtp}
                        className="text-sm font-semibold text-[#2563EB] hover:text-[#1D4ED8] disabled:text-[#94A3B8] transition-colors"
                      >
                        {cooldown > 0 ? `Resend available in ${formatTime(cooldown)}` : "Resend OTP"}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}

            {/* Secondary Options */}
            <div className="mt-8">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#E2E8F0]" />
                </div>
                <div className="relative flex justify-center text-xs font-semibold">
                  <span className="bg-white px-2 text-[#94A3B8] uppercase tracking-wider">Alternative Options</span>
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
                
                {authMethod === "local" && (
                  <button
                    type="button"
                    onClick={() => { setAuthMethod("mobile_otp"); setError(""); }}
                    className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-[#E2E8F0] shadow-sm text-sm font-semibold rounded-md text-[#334155] bg-white hover:bg-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#E2E8F0] transition-colors"
                  >
                    <Smartphone className="h-4 w-4 text-[#64748B]" />
                    Sign in with Mobile OTP
                  </button>
                )}
              </div>
            </div>

            <div className="mt-10 pt-6 border-t border-[#E2E8F0] text-center">
              <p className="text-sm font-medium text-[#64748B]">
                New to PolicyPilot?{" "}
                <Link href="/register" className="text-[#2563EB] hover:text-[#1D4ED8] font-semibold transition-colors">
                  Create your account &rarr;
                </Link>
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
            Enterprise Compliance <br/>
            <span className="text-[#3B82F6]">Infrastructure</span>
          </h1>
          <p className="text-[#94A3B8] text-lg font-medium leading-relaxed max-w-md">
            Strict role-based access control, real-time policy adaptation, and immutable audit trails built for modern banking.
          </p>
          
          <div className="mt-12 grid grid-cols-2 gap-8">
            <div>
              <div className="h-10 w-10 rounded-md bg-[#1E293B] border border-[#334155] flex items-center justify-center mb-4">
                <Shield className="h-5 w-5 text-[#3B82F6]" />
              </div>
              <h3 className="text-white font-semibold mb-2">Secure by Design</h3>
              <p className="text-[#64748B] text-sm leading-relaxed">Multi-layered security architecture protecting institutional data.</p>
            </div>
            <div>
              <div className="h-10 w-10 rounded-md bg-[#1E293B] border border-[#334155] flex items-center justify-center mb-4">
                <Mail className="h-5 w-5 text-[#3B82F6]" />
              </div>
              <h3 className="text-white font-semibold mb-2">Strict Verification</h3>
              <p className="text-[#64748B] text-sm leading-relaxed">Rigorous identity vetting and role authorization flow.</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs font-medium text-[#475569] max-w-xl mx-auto w-full">
          &copy; {new Date().getFullYear()} PolicyPilot Enterprise. All rights reserved.
        </div>
      </div>
    </div>
  );
}
