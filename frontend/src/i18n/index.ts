import { SupportedLanguage, LanguageInfo, TranslationDictionary } from "./types";
import { en } from "./en";
import { ta } from "./ta";
import { hi } from "./hi";
import { te } from "./te";
import { kn } from "./kn";
import { ml } from "./ml";

export * from "./types";
export { en, ta, hi, te, kn, ml };

export const translations: Record<SupportedLanguage, TranslationDictionary> = {
  en,
  ta,
  hi,
  te,
  kn,
  ml
};

export const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "ta", name: "Tamil", nativeName: "தமிழ்" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी" },
  { code: "te", name: "Telugu", nativeName: "తెలుగు" },
  { code: "kn", name: "Kannada", nativeName: "ಕನ್ನಡ" },
  { code: "ml", name: "Malayalam", nativeName: "മലയാളം" },
];

/**
 * Normalizes input string (code or full name) to a valid SupportedLanguage
 */
export function normalizeLanguage(lang?: string | null): SupportedLanguage {
  if (!lang) return "en";
  const cleaned = lang.trim().toLowerCase();
  
  if (cleaned === "en" || cleaned === "english") return "en";
  if (cleaned === "ta" || cleaned === "tamil" || cleaned === "தமிழ்") return "ta";
  if (cleaned === "hi" || cleaned === "hindi" || cleaned === "हिन्दी") return "hi";
  if (cleaned === "te" || cleaned === "telugu" || cleaned === "తెలుగు") return "te";
  if (cleaned === "kn" || cleaned === "kannada" || cleaned === "ಕನ್ನಡ") return "kn";
  if (cleaned === "ml" || cleaned === "malayalam" || cleaned === "മലയാളം") return "ml";
  
  return "en";
}

/**
 * Deep key lookup with dot notation e.g. "dashboard.welcomeBack"
 */
export function getTranslation(
  lang: SupportedLanguage,
  key: string,
  params?: Record<string, string | number>
): string {
  const dict = translations[lang] || translations.en;
  const parts = key.split(".");
  
  let current: any = dict;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = current[part];
    } else {
      // Fallback to English dictionary
      let fallback: any = translations.en;
      for (const fbPart of parts) {
        if (fallback && typeof fallback === "object" && fbPart in fallback) {
          fallback = fallback[fbPart];
        } else {
          return key;
        }
      }
      current = fallback;
      break;
    }
  }

  if (typeof current !== "string") {
    return key;
  }

  let result = current;
  if (params) {
    for (const [pKey, pVal] of Object.entries(params)) {
      result = result.replace(new RegExp(`\\{${pKey}\\}`, "g"), String(pVal));
    }
  }
  return result;
}
