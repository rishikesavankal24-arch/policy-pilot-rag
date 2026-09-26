import React from "react";
import { PolicyStatus } from "@/types";
import { cn } from "@/lib/utils";

interface PolicyStatusBadgeProps {
  status: PolicyStatus | string;
  className?: string;
  size?: "sm" | "md";
}

export function PolicyStatusBadge({ status, className, size = "sm" }: PolicyStatusBadgeProps) {
  const normStatus = (status || "").toUpperCase();

  const config: Record<string, { bg: string; text: string; border: string; dot: string; label: string }> = {
    DRAFT: {
      bg: "bg-slate-100",
      text: "text-slate-700",
      border: "border-slate-300",
      dot: "bg-slate-500",
      label: "DRAFT"
    },
    PUBLISHED: {
      bg: "bg-blue-50",
      text: "text-blue-800",
      border: "border-blue-200",
      dot: "bg-blue-600",
      label: "PUBLISHED"
    },
    ACTIVE: {
      bg: "bg-emerald-50",
      text: "text-emerald-800",
      border: "border-emerald-300",
      dot: "bg-emerald-600",
      label: "ACTIVE"
    },
    SUPERSEDED: {
      bg: "bg-amber-50",
      text: "text-amber-900",
      border: "border-amber-300",
      dot: "bg-amber-600",
      label: "SUPERSEDED"
    },
    ARCHIVED: {
      bg: "bg-stone-100",
      text: "text-stone-600",
      border: "border-stone-300",
      dot: "bg-stone-400",
      label: "ARCHIVED"
    }
  };

  const style = config[normStatus] || {
    bg: "bg-slate-100",
    text: "text-slate-600",
    border: "border-slate-200",
    dot: "bg-slate-400",
    label: normStatus || "UNKNOWN"
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-bold font-mono uppercase rounded border transition-colors",
        style.bg,
        style.text,
        style.border,
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        className
      )}
      title={`Policy Status: ${style.label}`}
    >
      <span className={cn("rounded-full shrink-0", style.dot, size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2")} />
      <span>{style.label}</span>
    </span>
  );
}
