import * as React from "react";
import { cn } from "../lib/utils";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "outline" | "ghost" | "danger" | "soft";
  size?: "sm" | "md" | "icon";
};

const variants = {
  primary: "bg-primary text-on-primary hover:bg-primary-container",
  outline: "border border-outline-variant bg-white text-on-surface hover:bg-surface-container-low",
  ghost: "text-on-surface-variant hover:bg-surface-container",
  danger: "bg-error text-white hover:bg-red-800",
  soft: "bg-primary-fixed text-on-primary-fixed hover:bg-secondary-container"
};

const sizes = {
  sm: "h-8 px-3 text-sm",
  md: "h-9 px-4 text-sm",
  icon: "h-8 w-8 p-0"
};

export function Button({ className, variant = "primary", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded border border-transparent font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}
