import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDateTime(isoString?: string | null): string {
  if (!isoString) return "N/A"
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return "N/A"
    const formatted = d.toLocaleString("en-GB", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    })
    return formatted.replace(/am|pm/i, (m) => m.toUpperCase())
  } catch {
    return "N/A"
  }
}
