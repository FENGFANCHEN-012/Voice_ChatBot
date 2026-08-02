import type { Document } from "../../types";

interface Props {
  documents: Document[];
  onDelete: (docId: string) => void;
}

export function FileList({ documents, onDelete }: Props) {
  if (documents.length === 0) {
    return <p className="text-stone-400 text-sm">No documents uploaded yet</p>;
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => (
        <li
          key={doc.doc_id}
          className="bg-white border border-stone-200 rounded-lg px-4 py-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-stone-800 truncate">
                {doc.filename}
              </p>
              <p className="text-xs text-stone-500 break-all">
                {doc.file_path}
              </p>
              <p className="text-xs text-stone-400 mt-1">
                {doc.chunk_count} embedded{doc.total_chunks > doc.chunk_count ? ` / ${doc.total_chunks} total` : ""} chunks &middot;{" "}
                {new Date(doc.uploaded_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={() => onDelete(doc.doc_id)}
              className="shrink-0 text-red-500 hover:text-red-700 text-sm font-medium"
            >
              Delete
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
