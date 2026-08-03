import { useState, useRef, type ChangeEvent } from "react";

interface Props {
  onUpload: (file: File) => void;
  disabled: boolean;
}

export function FileDropzone({ onUpload, disabled }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    if (file.type !== "application/pdf") {
      alert("Only PDF files are supported");
      return;
    }
    if (file.size > 40 * 1024 * 1024) {
      alert("File exceeds 40 MB limit");
      return;
    }
    onUpload(file);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onInput = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      className={`rounded-lg border border-dashed px-4 py-5 text-center cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 ${
        dragging
          ? "border-brand-400 bg-brand-50"
          : "border-neutral-300 hover:border-neutral-400 hover:bg-neutral-50"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
    >
      <input ref={inputRef} type="file" accept=".pdf" onChange={onInput} hidden />
      <div className="space-y-1.5">
        <svg className="w-5 h-5 mx-auto text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-xs font-medium text-neutral-600">
          {dragging ? "Drop to upload" : "Upload a PDF"}
        </p>
        <p className="text-[11px] text-neutral-400">Click or drag · up to 40 MB</p>
      </div>
    </div>
  );
}
