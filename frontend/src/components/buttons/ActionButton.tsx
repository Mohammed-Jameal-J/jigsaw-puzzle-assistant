import type { ButtonHTMLAttributes } from "react";

interface ActionButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

export default function ActionButton({
  variant = "primary",
  className = "",
  children,
  ...rest
}: ActionButtonProps) {
  const variantClass = variant === "primary" ? "btn-primary" : "btn-secondary";
  return (
    <button className={`btn ${variantClass} ${className}`.trim()} {...rest}>
      {children}
    </button>
  );
}
