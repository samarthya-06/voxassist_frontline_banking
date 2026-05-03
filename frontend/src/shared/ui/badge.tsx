import * as React from "react";
import { cn } from "../lib/utils";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "blue" | "green" | "amber" | "red" | "slate";
};

const tones = {
  blue: "bg-primary-fixed text-on-primary-fixed",
  green: "bg-emerald-50 text-emerald-800 border-emerald-200",
  amber: "bg-amber-50 text-amber-800 border-amber-200",
  red: "bg-error-container text-red-900 border-red-200",
  slate: "bg-slate-100 text-slate-700 border-slate-200"
};

export function Badge({ className, tone = "slate", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded border px-2 text-[11px] font-bold uppercase tracking-[0.05em]",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
