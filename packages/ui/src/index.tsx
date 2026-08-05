import type { ButtonHTMLAttributes, PropsWithChildren } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  variant = "secondary",
  className = "",
  children,
  ...props
}: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }>) {
  return (
    <button className={`ui-button ui-button--${variant} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

export function StatusBadge({
  tone = "neutral",
  children
}: PropsWithChildren<{ tone?: "neutral" | "info" | "success" | "warning" | "danger" }>) {
  return <span className={`ui-status ui-status--${tone}`}>{children}</span>;
}
