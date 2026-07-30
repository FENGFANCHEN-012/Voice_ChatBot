import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { RecordButton } from "../audio/RecordButton";
import { AudioVisualizer } from "../audio/AudioVisualizer";
import { useAudioAnalyser } from "../../hooks/useAudioAnalyser";

interface Props {
  onSend: (text: string) => void;
  onVoiceQuery: (blob: Blob) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, onVoiceQuery, disabled }: Props) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const analyser = useAudioAnalyser();

  useEffect(() => {
    if (!disabled) setProcessing(false);
  }, [disabled]);

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
    textRef.current?.focus();
  };

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const adjustHeight = () => {
    const el = textRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      analyser.start(stream);

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        analyser.stop();

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 0) {
          setProcessing(true);
          onVoiceQuery(blob);
        }
        setRecording(false);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch {
      setRecording(false);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
  };

  return (
    <div className="border-t border-stone-200 bg-white px-4 py-3">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <RecordButton
          isRecording={recording}
          isTranscribing={processing}
          onStart={startRecording}
          onStop={stopRecording}
        />
        <div className="flex-1 min-w-0">
          {recording ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse shrink-0" />
              <span className="text-xs text-red-600 font-medium shrink-0">Recording</span>
              <div className="flex-1 flex justify-center">
                <AudioVisualizer levels={analyser.levels} barCount={24} />
              </div>
            </div>
          ) : (
            <textarea
              ref={textRef}
              value={text}
              onChange={(e) => { setText(e.target.value); adjustHeight(); }}
              onKeyDown={handleKey}
              placeholder="Ask a question..."
              disabled={disabled || processing}
              rows={1}
              className="w-full resize-none rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-900 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-300 focus:border-stone-300 disabled:opacity-50 scrollbar-custom"
            />
          )}
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim() || processing}
          className="shrink-0 rounded-xl bg-stone-800 px-4 py-2 text-xs font-medium text-white hover:bg-stone-700 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
