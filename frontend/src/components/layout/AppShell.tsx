import { useState, type ReactNode } from "react";

interface Props {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppShell({ sidebar, children }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="h-full flex bg-white">
      <aside
        className={`shrink-0 h-full border-r border-neutral-200 bg-white overflow-hidden flex flex-col transition-[width] duration-200 ${
          collapsed ? "w-14" : "w-72"
        }`}
      >
        {collapsed ? (
          <div className="flex flex-col items-center gap-2 py-3">
            <button
              onClick={() => setCollapsed(false)}
              title="Expand sidebar"
              className="icon-btn w-9 h-9"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between pl-4 pr-2 h-12 border-b border-neutral-100 shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-6 h-6 rounded-md bg-brand-600 flex items-center justify-center shrink-0">
                  <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 1.5l2.2 6.2 6.6.1-5.2 4 1.9 6.3-5.5-3.6-5.5 3.6 1.9-6.3-5.2-4 6.6-.1L12 1.5z" />
                  </svg>
                </span>
                <span className="text-[15px] font-semibold text-neutral-800 truncate">Voice RAG</span>
              </div>
              <button
                onClick={() => setCollapsed(true)}
                title="Collapse sidebar"
                className="icon-btn w-8 h-8"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7M19 19l-7-7 7-7" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin">{sidebar}</div>
          </>
        )}
      </aside>
      <main className="flex-1 flex flex-col min-w-0">{children}</main>
    </div>
  );
}
