import type { Session } from "../../types";

interface Props {
  sessions: Session[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function SessionList({ sessions, currentId, onSelect, onCreate }: Props) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium uppercase tracking-wider text-stone-400">
          Chats
        </span>
        <button
          onClick={onCreate}
          className="text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors"
        >
          + New
        </button>
      </div>
      {sessions.length === 0 ? (
        <p className="text-xs text-stone-400 py-2">
          No chats yet. Start one above.
        </p>
      ) : (
        sessions.map((s) => (
          <button
            key={s.session_id}
            onClick={() => onSelect(s.session_id)}
            className={`w-full text-left px-3 py-2 rounded-md text-sm transition-all duration-150 ${
              currentId === s.session_id
                ? "bg-stone-200 text-stone-900 font-medium"
                : "text-stone-600 hover:bg-stone-100 hover:text-stone-800"
            }`}
          >
            <span className="truncate block">
              Chat {s.session_id.slice(0, 8)}
            </span>
          </button>
        ))
      )}
    </div>
  );
}
