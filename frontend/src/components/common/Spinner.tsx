export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-spin rounded-full border-2 border-neutral-200 border-t-brand-600 ${className || "w-5 h-5"}`} />
  );
}
