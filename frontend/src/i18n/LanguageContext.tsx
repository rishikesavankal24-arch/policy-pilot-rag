"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { 
  SupportedLanguage, 
  LanguageInfo, 
  SUPPORTED_LANGUAGES, 
  normalizeLanguage, 
  getTranslation 
} from "./index";

interface LanguageContextType {
  language: SupportedLanguage;
  languageInfo: LanguageInfo;
  setLanguage: (lang: SupportedLanguage) => Promise<void>;
  t: (key: string, params?: Record<string, string | number>) => string;
  tStatus: (status: string) => string;
  tLoanType: (type: string) => string;
  tDocType: (type: string) => string;
  supportedLanguages: LanguageInfo[];
  isUpdatingLang: boolean;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const { user, checkAuth } = useAuth();
  
  // Initialize from localStorage cache or fallback to "en"
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    if (typeof window !== "undefined") {
      const cached = localStorage.getItem("policypilot_lang");
      if (cached) {
        return normalizeLanguage(cached);
      }
    }
    return "en";
  });
  
  const [isUpdatingLang, setIsUpdatingLang] = useState(false);

  // Sync with user's persisted language whenever user object loads or updates
  useEffect(() => {
    if (user?.language) {
      const normalized = normalizeLanguage(user.language);
      setLanguageState(normalized);
      if (typeof window !== "undefined") {
        localStorage.setItem("policypilot_lang", normalized);
      }
    }
  }, [user?.language]);

  // Persist language selection to PostgreSQL via existing customer profile endpoint
  const setLanguage = useCallback(async (newLang: SupportedLanguage) => {
    const normalized = normalizeLanguage(newLang);
    setLanguageState(normalized);
    if (typeof window !== "undefined") {
      localStorage.setItem("policypilot_lang", normalized);
    }

    if (user) {
      setIsUpdatingLang(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiUrl}/api/customer/profile`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language: normalized }),
          credentials: 'include'
        });
        if (res.ok && checkAuth) {
          await checkAuth();
        }
      } catch (err) {
        console.error("Failed to persist language preference:", err);
      } finally {
        setIsUpdatingLang(false);
      }
    }
  }, [user, checkAuth]);

  // Translation lookup helper
  const t = useCallback((key: string, params?: Record<string, string | number>) => {
    return getTranslation(language, key, params);
  }, [language]);

  // Status mapping helper
  const tStatus = useCallback((status: string) => {
    if (!status) return "";
    const key = status.toUpperCase();
    switch (key) {
      case "DRAFT":
        return getTranslation(language, "status.draft");
      case "SUBMITTED":
        return getTranslation(language, "status.submitted");
      case "UNDER_REVIEW":
        return getTranslation(language, "status.underReview");
      case "ADDITIONAL_INFO_REQUIRED":
        return getTranslation(language, "status.additionalInfoRequired");
      case "APPROVED":
        return getTranslation(language, "status.approved");
      case "DECLINED":
        return getTranslation(language, "status.declined");
      case "UPLOADED":
        return getTranslation(language, "status.uploaded");
      case "PROCESSING":
        return getTranslation(language, "status.processing");
      case "VERIFIED":
        return getTranslation(language, "status.verified");
      case "REJECTED":
        return getTranslation(language, "status.rejected");
      case "REQUIRES_REUPLOAD":
        return getTranslation(language, "status.requiresReupload");
      default:
        return status.replace(/_/g, " ");
    }
  }, [language]);

  // Loan Type mapping helper
  const tLoanType = useCallback((type: string) => {
    if (!type) return "";
    const normalized = type.trim().toLowerCase();
    if (normalized.includes("personal")) {
      return getTranslation(language, "loanTypes.personalLoan");
    }
    if (normalized.includes("home")) {
      return getTranslation(language, "loanTypes.homeLoan");
    }
    if (normalized.includes("auto") || normalized.includes("vehicle") || normalized.includes("car")) {
      return getTranslation(language, "loanTypes.autoLoan");
    }
    if (normalized.includes("business")) {
      return getTranslation(language, "loanTypes.businessLoan");
    }
    if (normalized.includes("education") || normalized.includes("student")) {
      return getTranslation(language, "loanTypes.educationLoan");
    }
    return type;
  }, [language]);

  // Document Type mapping helper
  const tDocType = useCallback((docType: string) => {
    if (!docType) return "";
    const normalized = docType.trim().toUpperCase();
    if (normalized.includes("IDENTITY") || normalized.includes("AADHAAR") || normalized.includes("PASSPORT")) {
      return getTranslation(language, "docTypes.identityProof");
    }
    if (normalized.includes("ADDRESS") || normalized.includes("RENT") || normalized.includes("UTILITY")) {
      return getTranslation(language, "docTypes.addressProof");
    }
    if (normalized.includes("INCOME") || normalized.includes("SALARY") || normalized.includes("ITR")) {
      return getTranslation(language, "docTypes.incomeProof");
    }
    if (normalized.includes("BANK") || normalized.includes("STATEMENT")) {
      return getTranslation(language, "docTypes.bankStatement");
    }
    if (normalized.includes("OTHER")) {
      return getTranslation(language, "docTypes.other");
    }
    return docType;
  }, [language]);

  const languageInfo = SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];

  return (
    <LanguageContext.Provider
      value={{
        language,
        languageInfo,
        setLanguage,
        t,
        tStatus,
        tLoanType,
        tDocType,
        supportedLanguages: SUPPORTED_LANGUAGES,
        isUpdatingLang
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
