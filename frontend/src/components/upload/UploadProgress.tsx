interface Props {
  phase: "uploading" | "embedding" | "done" | "error";
  uploadProgress: number;
  embedCurrent: number;
  embedTotal: number;
  filename: string;
  errorMsg?: string;
}

export function UploadProgress({ phase, uploadProgress, embedCurrent, embedTotal, filename, errorMsg }: Props) {
  if (phase === "done") {
    return (
      <div className="w-full">
        <p className="text-xs text-green-600 mt-1">✓ {filename} ready</p>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="w-full">
        <p className="text-xs text-red-500 mt-1">✗ {errorMsg || "Embedding failed"}</p>
      </div>
    );
  }

  const pct = phase === "uploading"
    ? uploadProgress
    : embedTotal > 0 ? Math.round((embedCurrent / embedTotal) * 100) : 0;

  const label = phase === "uploading"
    ? `Uploading ${filename}...`
    : `Embedding ${filename}... ${embedCurrent}/${embedTotal}`;

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-stone-500 mb-1">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-stone-200 rounded-full h-2">
        <div
          className="bg-amber-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
