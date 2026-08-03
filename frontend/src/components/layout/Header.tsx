interface Props {
  title?: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: Props) {
  return (
    <header className="h-12 shrink-0 border-b border-neutral-200 bg-white flex items-center justify-between px-6">
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="text-sm font-medium text-neutral-800 truncate">{title || "Voice RAG"}</h1>
        {subtitle && <span className="text-xs text-neutral-400 hidden sm:inline truncate">{subtitle}</span>}
      </div>
    </header>
  );
}
