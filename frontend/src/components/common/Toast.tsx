interface Props {
  message: string;
  type: "success" | "error" | "info";
}

export function Toast({ message, type }: Props) {
  const dot = {
    success: "bg-emerald-500",
    error: "bg-red-500",
    info: "bg-brand-500",
  };
  return (
    <div className="fixed bottom-4 right-4 z-50 bg-white border border-neutral-200 shadow-pop rounded-lg px-4 py-2.5 flex items-center gap-2.5 animate-slide-up">
      <span className={`w-2 h-2 rounded-full shrink-0 ${dot[type]}`} />
      <span className="text-sm text-neutral-700">{message}</span>
    </div>
  );
}
