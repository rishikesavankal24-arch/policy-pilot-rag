"use client";

import { useAuth } from "@/contexts/AuthContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState, useEffect } from "react";
import { Save, AlertCircle, CheckCircle2, ShieldCheck, UserCheck, Lock } from "lucide-react";
import { useLanguage } from "@/i18n/LanguageContext";
import { SUPPORTED_LANGUAGES, normalizeLanguage } from "@/i18n";

export default function ProfilePage() {
  const { user, isLoading } = useAuth();
  const { t, setLanguage } = useLanguage();
  const [profile, setProfile] = useState<any>(null);
  const [isFetching, setIsFetching] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{type: "error"|"success", text: string} | null>(null);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiUrl}/api/customer/profile`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setProfile(data);
        } else {
          setMessage({ type: "error", text: t("profile.updateFailed") });
        }
      } catch {
        setMessage({ type: "error", text: t("profile.updateFailed") });
      } finally {
        setIsFetching(false);
      }
    }
    fetchProfile();
  }, [t]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/customer/profile`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
        credentials: 'include'
      });
      if (res.ok) {
        setMessage({ type: "success", text: t("profile.updateSuccess") });
        if (profile?.language) {
          await setLanguage(normalizeLanguage(profile.language));
        }
      } else {
        setMessage({ type: "error", text: t("profile.updateFailed") });
      }
    } catch {
      setMessage({ type: "error", text: t("profile.updateFailed") });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || isFetching) {
    return (
      <AuthenticatedLayout>
        <div className="flex flex-col h-64 items-center justify-center space-y-2">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{t("common.loading")}</p>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="max-w-3xl mx-auto space-y-6 text-slate-900 pb-12">
        
        {/* Header Strip */}
        <div className="border-b border-slate-200 pb-5">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold uppercase tracking-tight text-slate-950">
              {t("profile.title")}
            </h1>
            <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded border border-emerald-200">
              Verified Customer KYC Record
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{t("profile.subtitle")}</p>
        </div>

        {message && (
          <div className={`p-4 rounded flex items-start gap-2.5 text-xs ${
            message.type === 'success' ? 'bg-emerald-50 border border-emerald-200 text-emerald-900' : 'bg-red-50 border border-red-200 text-red-900'
          }`}>
            {message.type === 'success' ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
            )}
            <p className="font-medium">{message.text}</p>
          </div>
        )}

        {/* Official Account Master Record Overview */}
        <div className="bg-white border border-slate-200 rounded p-4 shadow-xs space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
            <UserCheck className="h-4 w-4 text-[#0B192C]" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Statutory Account Identification
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Customer Role</span>
              <p className="font-bold text-slate-900 mt-0.5">{t("nav.customer")}</p>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Onboarding Status</span>
              <p className="font-semibold text-emerald-700 mt-0.5">COMPLETED</p>
            </div>
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Data Privacy</span>
              <p className="font-semibold text-slate-700 mt-0.5 flex items-center gap-1">
                <Lock className="h-3 w-3 text-emerald-600" /> DPDP / ISO Compliant
              </p>
            </div>
          </div>
        </div>

        {/* Profile Details Edit Form */}
        <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {t("profile.personalInfoTitle")}
            </h3>
            <span className="text-[11px] text-slate-500">Official Master Record</span>
          </div>

          <div className="p-5 space-y-5 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("profile.fullName")}</label>
                <input 
                  type="text" 
                  name="full_name" 
                  value={profile?.full_name || ''} 
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("profile.emailAddress")}</label>
                <input 
                  type="email" 
                  value={profile?.email || ''} 
                  disabled
                  className="w-full px-3 py-2 border border-slate-200 bg-slate-100 text-slate-500 rounded cursor-not-allowed font-mono text-xs"
                />
                <p className="text-[10px] text-slate-400">{t("profile.emailNotice")}</p>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("profile.phoneNumber")}</label>
                <input 
                  type="text" 
                  name="phone_number" 
                  value={profile?.phone_number || ''} 
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] font-mono text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">{t("profile.dateOfBirth")}</label>
                <input 
                  type="date" 
                  name="date_of_birth" 
                  value={profile?.date_of_birth || ''} 
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                />
              </div>
            </div>

            {/* Address Details Section */}
            <div className="pt-4 border-t border-slate-200">
              <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                {t("profile.addressDetailsTitle")}
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="font-semibold text-slate-800">{t("profile.streetAddress")}</label>
                  <input 
                    type="text" 
                    name="address" 
                    value={profile?.address || ''} 
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-800">{t("profile.city")}</label>
                  <input 
                    type="text" 
                    name="city" 
                    value={profile?.city || ''} 
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-800">{t("profile.state")}</label>
                  <input 
                    type="text" 
                    name="state" 
                    value={profile?.state || ''} 
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-800">{t("profile.pincode")}</label>
                  <input 
                    type="text" 
                    name="pincode" 
                    value={profile?.pincode || ''} 
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] font-mono text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-800">{t("profile.preferredLanguage")}</label>
                  <select 
                    name="language" 
                    value={profile?.language || 'en'} 
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs"
                  >
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.nativeName} ({lang.name})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

          </div>

          <div className="px-5 py-3.5 bg-slate-50 border-t border-slate-200 flex justify-end">
            <button 
              type="submit" 
              disabled={isSaving}
              className="px-5 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-xs"
            >
              <Save className="h-3.5 w-3.5" />
              <span>{isSaving ? t("profile.saving") : t("profile.saveChanges")}</span>
            </button>
          </div>
        </form>

      </div>
    </AuthenticatedLayout>
  );
}
