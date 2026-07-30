import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface Props {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppShell({ sidebar, children }: Props) {
  return (
    <div className="h-screen flex flex-col bg-stone-50">
      <header className="h-12 shrink-0 border-b border-stone-200 bg-white flex items-center px-5 z-10">
        <h1 className="text-sm font-semibold tracking-tight text-stone-800">
          Voice RAG
        </h1>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <Sidebar>{sidebar}</Sidebar>
        <main className="flex-1 flex flex-col min-w-0 bg-white">
          {children}
        </main>
      </div>
    </div>
  );
}
