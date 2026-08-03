export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-white border border-neutral-200 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1 shadow-card">
        <span className="w-1.5 h-1.5 bg-neutral-300 rounded-full animate-pulse-dot" />
        <span className="w-1.5 h-1.5 bg-neutral-300 rounded-full animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
        <span className="w-1.5 h-1.5 bg-neutral-300 rounded-full animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
      </div>
    </div>
  );
}
