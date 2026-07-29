interface Props {
  progress: number; // 0-100
  filename: string;
}

export function UploadProgress({ progress, filename }: Props) {
  if (progress === 0) return null;

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{filename}</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      {progress === 100 && <p className="text-xs text-green-500 mt-1">Processing complete</p>}
    </div>
  );
}
