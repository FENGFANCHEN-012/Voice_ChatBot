import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-9 px-4",
  lg: "h-11 px-5",
};

export function Button({ variant = "primary", size = "md", className = "", ...props }: Props) {
  const variantClass = `btn-${variant}`;
  return <button className={`${variantClass} ${sizes[size]} ${className}`} {...props} />;
}
