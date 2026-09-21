"use client";

import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  Save, 
  AlertCircle, 
  ArrowRight
} from "lucide-react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageContext";

export default function NewApplicationPage() {
  const router = useRouter();
  const { t, tLoanType } = useLanguage();
  
  const [formData, setFormData] = useState({
    loan_type: 'Personal Loan',
    requested_amount: '',
    tenure: '12',
    purpose: '',
    employment_info: '',
    income_info: '',
    existing_liabilities: ''
  });

  const [hasDeclared, setHasDeclared] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAction = async () => {
    setError(null);

    // Basic client validation
    const cleanAmountStr = String(formData.requested_amount || '').replace(/[^\d]/g, '');
    const amountNum = parseInt(cleanAmountStr, 10);
    if (!cleanAmountStr || isNaN(amountNum) || amountNum <= 0) {
      setError("Please enter a valid requested principal loan amount.");
      return;
    }

    const cleanTenureStr = String(formData.tenure || '').replace(/[^\d]/g, '');
    const tenureNum = parseInt(cleanTenureStr, 10);
    if (!cleanTenureStr || isNaN(tenureNum) || tenureNum <= 0) {
      setError("Please select a valid repayment tenure.");
      return;
    }

    if (!formData.purpose || !formData.purpose.trim()) {
      setError("Please specify the purpose of the credit facility.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        loan_type: formData.loan_type,
        requested_amount: amountNum,
        tenure: tenureNum,
        purpose: formData.purpose.trim(),
        employment_info: formData.employment_info?.trim() || null,
        income_info: formData.income_info?.trim() || null,
        existing_liabilities: formData.existing_liabilities?.trim() || null
      };

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      // Step 1: Create Draft Application
      const res = await fetch(`${apiUrl}/api/applications/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (!res.ok) {
        let errorMsg = t("newApplication.createFailed");
        try {
          const errData = await res.json();
          if (errData?.detail) {
            if (typeof errData.detail === "string") {
              errorMsg = errData.detail;
            } else if (Array.isArray(errData.detail) && errData.detail.length > 0) {
              const firstErr = errData.detail[0];
              const msg = firstErr.msg ? firstErr.msg.replace(/^Value error,\s*/i, "") : "";
              errorMsg = msg || errorMsg;
            }
          }
        } catch {
          // ignore parse error
        }
        throw new Error(errorMsg);
      }

      const newApp = await res.json();

      // Redirect to detail page as draft so customer can review, attach documents, and submit
      router.push(`/dashboard/applications/${newApp.id}`);
    } catch (err: any) {
      setError(err.message || t("newApplication.createFailed"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="max-w-3xl mx-auto space-y-6 text-slate-900">
        
        {/* Page Title & Breadcrumb */}
        <div className="flex items-center gap-3 border-b border-slate-200 pb-5">
          <Link 
            href="/dashboard/applications" 
            className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-800 transition-colors" 
            aria-label={t("common.back")}
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold uppercase tracking-tight text-slate-950">
                {t("newApplication.title")}
              </h1>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                Form No. PL-01
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{t("newApplication.subtitle")}</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded p-4 flex gap-2.5 items-start text-red-900 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-red-600" />
            <p className="font-medium">{error}</p>
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); handleAction(); }} className="space-y-6">
          
          {/* SECTION 1: Loan Details */}
          <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("newApplication.sec1Title")}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t("newApplication.sec1Desc")}
              </p>
            </div>

            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.loanType")} <span className="text-red-500">*</span>
                </label>
                <select 
                  name="loan_type" 
                  value={formData.loan_type}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs"
                >
                  <option value="Personal Loan">{tLoanType("Personal Loan")}</option>
                  <option value="Home Loan">{tLoanType("Home Loan")}</option>
                  <option value="Auto Loan">{tLoanType("Auto Loan")}</option>
                  <option value="Business Loan">{tLoanType("Business Loan")}</option>
                  <option value="Education Loan">{tLoanType("Education Loan")}</option>
                </select>
              </div>
              
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.requestedAmount")} <span className="text-red-500">*</span>
                </label>
                <input 
                  type="number" 
                  name="requested_amount" 
                  required
                  min="1000"
                  placeholder={t("newApplication.requestedAmountPlaceholder")}
                  value={formData.requested_amount}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] font-mono text-xs"
                />
              </div>
              
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.tenure")} <span className="text-red-500">*</span>
                </label>
                <select 
                  name="tenure" 
                  value={formData.tenure}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] bg-white text-xs"
                >
                  <option value="12">12 {t("newApplication.monthsSuffix")}</option>
                  <option value="24">24 {t("newApplication.monthsSuffix")}</option>
                  <option value="36">36 {t("newApplication.monthsSuffix")}</option>
                  <option value="48">48 {t("newApplication.monthsSuffix")}</option>
                  <option value="60">60 {t("newApplication.monthsSuffix")}</option>
                  <option value="120">120 {t("newApplication.monthsSuffix")}</option>
                  <option value="240">240 {t("newApplication.monthsSuffix")}</option>
                </select>
              </div>
            </div>
          </div>

          {/* SECTION 2: Financial Information */}
          <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("newApplication.sec2Title")}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t("newApplication.sec2Desc")}
              </p>
            </div>

            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.monthlyIncome")}
                </label>
                <input 
                  type="text" 
                  name="income_info" 
                  placeholder={t("newApplication.monthlyIncomePlaceholder")}
                  value={formData.income_info}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                />
              </div>
              
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.existingLiabilities")}
                </label>
                <input 
                  type="text" 
                  name="existing_liabilities" 
                  placeholder={t("newApplication.liabilitiesPlaceholder")}
                  value={formData.existing_liabilities}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: Employment Information */}
          <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("newApplication.sec3Title")}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t("newApplication.sec3Desc")}
              </p>
            </div>

            <div className="p-5 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.employmentInfo")}
                </label>
                <input 
                  type="text" 
                  name="employment_info" 
                  placeholder={t("newApplication.employmentPlaceholder")}
                  value={formData.employment_info}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs"
                />
              </div>
            </div>
          </div>

          {/* SECTION 4: Purpose */}
          <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("newApplication.sec4Title")}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t("newApplication.sec4Desc")}
              </p>
            </div>

            <div className="p-5 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-800">
                  {t("newApplication.purpose")} <span className="text-red-500">*</span>
                </label>
                <textarea 
                  name="purpose"
                  required
                  placeholder={t("newApplication.purposePlaceholder")}
                  value={formData.purpose}
                  onChange={handleChange}
                  rows={3}
                  className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-[#0B192C] text-xs leading-relaxed"
                ></textarea>
              </div>
            </div>
          </div>

          {/* SECTION 5: Review & Declaration */}
          <div className="bg-white border border-slate-200 rounded shadow-xs overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {t("newApplication.sec5Title")}
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {t("newApplication.sec5Desc")}
              </p>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* Summary verification pill */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-1 text-slate-700">
                <div className="flex justify-between">
                  <span className="text-slate-500">Facility Type:</span>
                  <span className="font-semibold text-slate-900">{formData.loan_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Requested Principal:</span>
                  <span className="font-mono font-semibold text-slate-900">
                    {formData.requested_amount ? `₹${Number(formData.requested_amount).toLocaleString('en-IN')}` : "—"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tenure:</span>
                  <span className="font-semibold text-slate-900">{formData.tenure} Months</span>
                </div>
              </div>

              {/* Statutory Declaration Checkbox */}
              <label className="flex items-start gap-3 p-3 bg-amber-50/50 border border-amber-200 rounded cursor-pointer hover:bg-amber-50 transition-colors">
                <input 
                  type="checkbox"
                  checked={hasDeclared}
                  onChange={(e) => setHasDeclared(e.target.checked)}
                  className="mt-0.5 h-4 w-4 text-[#0B192C] rounded border-slate-300 focus:ring-[#0B192C]"
                />
                <span className="text-xs text-slate-800 leading-relaxed">
                  {t("newApplication.declarationText")}
                </span>
              </label>
            </div>
          </div>

          {/* Form Actions Strip */}
          <div className="p-4 bg-white border border-slate-200 rounded shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
            <Link 
              href="/dashboard/applications"
              className="w-full sm:w-auto px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded text-xs font-semibold hover:bg-slate-50 transition-colors text-center"
            >
              {t("newApplication.cancel")}
            </Link>

            <div className="w-full sm:w-auto flex items-center gap-2">
              <button 
                type="button" 
                onClick={handleAction}
                disabled={isSubmitting}
                className="flex-1 sm:flex-initial px-4 py-2 bg-white border border-slate-300 text-slate-800 rounded text-xs font-semibold hover:bg-slate-50 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                <Save className="h-3.5 w-3.5 text-slate-500" />
                <span>{isSubmitting ? t("newApplication.saving") : t("newApplication.saveDraft")}</span>
              </button>

              <button 
                type="submit" 
                disabled={isSubmitting}
                className="flex-1 sm:flex-initial px-5 py-2 bg-[#0B192C] text-white rounded text-xs font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5 shadow-xs"
              >
                <ArrowRight className="h-3.5 w-3.5" />
                <span>{isSubmitting ? t("newApplication.saving") : "Save & Proceed to Dossier"}</span>
              </button>
            </div>
          </div>

        </form>

      </div>
    </AuthenticatedLayout>
  );
}
