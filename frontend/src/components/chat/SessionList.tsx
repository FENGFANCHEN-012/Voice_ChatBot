import { useState } from "react";
import type { Session } from "../../types";

interface Props {
  sessions: Session[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}

export function SessionList({ sessions, currentId, onSelect, onCreate, onDelete, onRename }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const startEdit = (s: Session) => {
    setEditingId(s.session_id);
    setDraft(s.title || `Chat ${s.session_id.slice(0, 8)}`);
  };

  const commitEdit = () => {
    if (editingId && draft.trim()) {
      onRename(editingId, draft.trim());
    }
    setEditingId(null);
  };

  const label = (s: Session) => s.title?.trim() || `Chat ${s.session_id.slice(0, 8)}`;

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between px-2 pt-4 pb-1.5">
        <span className="section-label">Chats</span>
        <button
          onClick={onCreate}
          title="New chat"
          aria-label="New chat"
          className="icon-btn w-6 h-6"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>

      {sessions.length === 0 ? (
        <p className="text-xs text-neutral-400 px-2 py-2">No chats yet</p>
      ) : (
        sessions.map((s) => {
          const isEditing = editingId === s.session_id;
          const isActive = currentId === s.session_id;
          return (
            <div
              key={s.session_id}
              className={`group flex items-center gap-1 rounded-lg mx-1 transition-colors duration-150 ${
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "hover:bg-neutral-50"
              }`}
            >
              {isEditing ? (
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commitEdit}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit();
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  className="input flex-1 min-w-0 m-1 py-1 text-sm"
                />
              ) : (
                <button
                  onClick={() => onSelect(s.session_id)}
                  className="flex-1 min-w-0 text-left px-2.5 py-1.5"
                >
                  <span className={`truncate block text-[13px] ${isActive ? "font-medium text-brand-700" : "text-neutral-700"}`}>
                    {label(s)}
                  </span>
                </button>
              )}
              {!isEditing && (
                <div className="flex items-center gap-0.5 pr-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                  <button
                    onClick={() => startEdit(s)}
                    title="Rename"
                    className={`icon-btn w-6 h-6 ${isActive ? "text-brand-400 hover:text-brand-700 hover:bg-brand-100" : ""}`}
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-5m-1.414-9.414a2 2 0 1 1 2.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => onDelete(s.session_id)}
                    title="Delete"
                    className="icon-btn w-6 h-6 hover:text-red-600 hover:bg-red-50"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
