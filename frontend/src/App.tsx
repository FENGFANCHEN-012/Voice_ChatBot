import { useState, useEffect, useCallback } from "react";
import { FileDropzone } from "./components/upload/FileDropzone";
import { FileList } from "./components/upload/FileList";
import { UploadProgress } from "./components/upload/UploadProgress";
import { uploadDocument, listDocuments, deleteDocument } from "./services/api";
import type { Document } from "./types";

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadFilename, setUploadFilename] = useState("");

  const fetchDocs = useCallback(async () => {
    try {
      const { data } = await listDocuments();
      setDocuments(data);
    } catch {
      console.error("Failed to fetch documents");
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setProgress(0);
    setUploadFilename(file.name);

    try {
      const { data } = await uploadDocument(file, (pct) => {
        setProgress(pct);
      });
      setProgress(100);
      setDocuments((prev) => [...prev, data]);
      setTimeout(() => setProgress(0), 1500);
    } catch {
      alert("Upload failed");
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch {
      alert("Delete failed");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-800">
          Voice RAG Assistant
        </h1>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <section className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-medium text-gray-700 mb-4">
            Upload PDF
          </h2>
          <FileDropzone onUpload={handleUpload} disabled={uploading} />
          {uploading && (
            <div className="mt-4">
              <UploadProgress progress={progress} filename={uploadFilename} />
            </div>
          )}
        </section>

        <section className="bg-white rounded-lg border p-6">
          <h2 className="text-lg font-medium text-gray-700 mb-4">
            Uploaded Documents
          </h2>
          <FileList documents={documents} onDelete={handleDelete} />
        </section>
      </main>
    </div>
  );
}

export default App;
