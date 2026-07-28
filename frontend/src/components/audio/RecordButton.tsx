interface Props {
  isRecording: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function RecordButton({ isRecording, onStart, onStop }: Props) {
  return (
    <button
      onClick={isRecording ? onStop : onStart}
      className={`rounded-full w-12 h-12 flex items-center justify-center ${
        isRecording ? "bg-red-500 animate-pulse" : "bg-blue-500"
      } text-white`}
    >
      {isRecording ? "■" : "●"}
    </button>
  );
}
