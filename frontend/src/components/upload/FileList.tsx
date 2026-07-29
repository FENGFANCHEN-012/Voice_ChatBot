import type { Document } from "../../types";

interface Props {
  documents: Document[];
  onDelete: (docId: string) => void;
}

export function FileList({ documents, onDelete }: Props) {
  if (documents.length === 0) {
    return <p className="text-gray-400 text-sm">No documents uploaded yet</p>;
  }

  return (
    <ul className="space-y-2">
      {documents.map((doc) => (
        <li
          key={doc.doc_id}
          className="flex items-center justify-between bg-white border rounded-lg px-4 py-3"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-800 truncate">
              {doc.filename}
            </p>
            <p className="text-xs text-gray-400">
              {doc.chunk_count} chunks &middot;{" "}
              {new Date(doc.uploaded_at).toLocaleString()}
            </p>
          </div>
          <button
            onClick={() => onDelete(doc.doc_id)}
            className="ml-3 text-red-500 hover:text-red-700 text-sm font-medium"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
