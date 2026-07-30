import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
}

export function Sidebar({ children }: Props) {
  return (
    <aside className="w-72 lg:w-80 shrink-0 border-r border-stone-200 bg-stone-50 overflow-y-auto scrollbar-custom">
      {children}
    </aside>
  );
}
