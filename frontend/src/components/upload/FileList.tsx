import type { Document } from "../../types";

interface Props {
  documents: Document[];
  onDelete: (docId: string) => void;
}

export function FileList({ documents, onDelete }: Props) {
  if (documents.length === 0) {
    return (
      <p className="text-xs text-neutral-400 py-1">
        No documents yet
      </p>
    );
  }

  return (
    <ul className="space-y-1">
      {documents.map((doc) => (
        <li
          key={doc.doc_id}
          className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2 hover:bg-neutral-50 transition-colors duration-150"
        >
          <svg className="w-4 h-4 text-red-400 shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 2a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6H6zm7 1.5L18.5 9H13V3.5z" />
          </svg>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium text-neutral-700 truncate">
              {doc.filename}
            </p>
            <p className="text-[11px] text-neutral-400">
              {doc.chunk_count} chunks · {new Date(doc.uploaded_at).toLocaleDateString()}
            </p>
          </div>
          <button
            onClick={() => onDelete(doc.doc_id)}
            className="icon-btn w-7 h-7 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
            aria-label={`Delete ${doc.filename}`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </li>
      ))}
    </ul>
  );
}
