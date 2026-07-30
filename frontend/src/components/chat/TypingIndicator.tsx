export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-stone-100 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse-dot" />
        <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse-dot" style={{ animationDelay: "0.2s" }} />
        <span className="w-1.5 h-1.5 bg-stone-400 rounded-full animate-pulse-dot" style={{ animationDelay: "0.4s" }} />
      </div>
    </div>
  );
}
