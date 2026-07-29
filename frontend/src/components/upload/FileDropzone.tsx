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
    if (file.size > 20 * 1024 * 1024) {
      alert("File exceeds 20 MB limit");
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
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-gray-400"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
    >
      <input ref={inputRef} type="file" accept=".pdf" onChange={onInput} hidden />
      <p className="text-gray-500">
        {dragging ? "Drop your PDF here" : "Click or drag a PDF to upload"}
      </p>
      <p className="text-xs text-gray-400 mt-1">Max 20 MB</p>
    </div>
  );
}
