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
      <div className="flex items-center gap-2 py-1">
        <span className="w-4 h-4 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center text-[10px]">
          <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </span>
        <span className="text-xs text-neutral-600 truncate">{filename} ready</span>
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className="flex items-center gap-2 py-1">
        <span className="w-4 h-4 rounded-full bg-red-50 text-red-500 flex items-center justify-center text-[10px]">
          <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </span>
        <span className="text-xs text-red-600 truncate">{errorMsg || "Upload failed"}</span>
      </div>
    );
  }

  const pct = phase === "uploading"
    ? uploadProgress
    : embedTotal > 0 ? Math.round((embedCurrent / embedTotal) * 100) : 0;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-[11px] text-neutral-500">
        <span className="truncate">{phase === "uploading" ? "Uploading…" : `Processing ${embedCurrent}/${embedTotal}`}</span>
        <span className="shrink-0 ml-2 tabular-nums">{pct}%</span>
      </div>
      <div className="w-full bg-neutral-100 rounded-full h-1 overflow-hidden">
        <div
          className="bg-brand-500 h-1 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
