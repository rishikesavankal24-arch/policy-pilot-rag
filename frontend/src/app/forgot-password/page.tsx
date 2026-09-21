"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    
    if (!identifier) {
      setError("Please enter your email or mobile number.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/local/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to process request");
      }
      
      setSuccess(true);
      
      // In local dev we can simulate navigation to reset-password with the token.
      // But a real user would click a link in their email.
      // We will just tell them to check the backend logs for the token,
      // and provide a link to the reset-password page.
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F8FAFC] font-sans">
      <div className="flex flex-1 flex-col justify-center py-12 px-4 sm:px-6 lg:flex-none lg:w-[480px] xl:w-[560px] lg:px-20 xl:px-24 bg-white border-r border-[#E2E8F0] shadow-sm z-10 mx-auto lg:mx-0">
        <div className="mx-auto w-full max-w-sm lg:w-[360px]">
          
          <div className="mb-10">
            <div className="flex items-center gap-2.5 text-[#0F172A] font-bold text-2xl tracking-tight mb-10">
              <Shield className="h-7 w-7 text-[#2563EB]" strokeWidth={2.5} />
              PolicyPilot
            </div>
            <h2 className="text-2xl font-bold text-[#0F172A] tracking-tight">Reset password</h2>
            <p className="mt-2 text-sm text-[#64748B] font-medium">
              Enter your email or mobile number to receive a reset link.
            </p>
          </div>

          <div className="mt-8">
            {error && (
              <div className="mb-6 bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] px-4 py-3 rounded-md text-sm font-medium">
                {error}
              </div>
            )}
            
            {success ? (
              <div className="space-y-6">
                <div className="bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] px-4 py-3 rounded-md text-sm font-medium">
                  If an account exists, a password reset link has been generated. Check the backend logs for your local reset token!
                </div>
                <Link 
                  href="/reset-password"
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] transition-colors"
                >
                  Go to Reset Password (Dev Mode)
                </Link>
                <div className="text-center mt-4">
                  <Link href="/login" className="text-[#2563EB] hover:text-[#1D4ED8] font-semibold text-sm transition-colors">
                    Back to login
                  </Link>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
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

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-bold text-white bg-[#0F172A] hover:bg-[#1E293B] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0F172A] disabled:opacity-50 transition-colors mt-2"
                >
                  {isSubmitting ? "Sending..." : "Send reset link"}
                </button>
              </form>
            )}

            {!success && (
              <div className="mt-6 text-center">
                <Link href="/login" className="text-[#2563EB] hover:text-[#1D4ED8] font-semibold text-sm transition-colors">
                  &larr; Back to login
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
