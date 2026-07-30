interface Props {
  isRecording: boolean;
  isTranscribing: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function RecordButton({ isRecording, isTranscribing, onStart, onStop }: Props) {
  const handleClick = () => {
    if (isTranscribing) return;
    if (isRecording) onStop();
    else onStart();
  };

  return (
    <button
      onClick={handleClick}
      disabled={isTranscribing}
      title={isRecording ? "Stop recording" : "Start recording"}
      className={`shrink-0 rounded-xl w-9 h-9 flex items-center justify-center transition-all duration-200 ${
        isRecording
          ? "bg-red-50 text-red-600 ring-2 ring-red-300"
          : isTranscribing
            ? "bg-amber-50 text-amber-500"
            : "bg-stone-100 text-stone-500 hover:bg-stone-200 hover:text-stone-700"
      }`}
    >
      {isTranscribing ? (
        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {isRecording ? (
            <>
              <rect x="9" y="2" width="6" height="11" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </>
          ) : (
            <>
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </>
          )}
        </svg>
      )}
    </button>
  );
}
