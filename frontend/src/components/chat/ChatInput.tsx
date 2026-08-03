import { useState, useRef, useEffect } from "react";
import { RecordButton } from "../audio/RecordButton";
import { AudioVisualizer } from "../audio/AudioVisualizer";
import { useAudioAnalyser } from "../../hooks/useAudioAnalyser";

interface Props {
  onVoiceQuery: (blob: Blob) => void;
  disabled: boolean;
}

function formatTime(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ChatInput({ onVoiceQuery, disabled }: Props) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const cancelledRef = useRef(false);
  const startedAtRef = useRef(0);
  const analyser = useAudioAnalyser();

  useEffect(() => {
    if (!disabled) setProcessing(false);
  }, [disabled]);

  useEffect(() => {
    if (!recording) return;
    startedAtRef.current = Date.now();
    setElapsed(0);
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 500);
    return () => clearInterval(timer);
  }, [recording]);

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
      streamRef.current = stream;
      analyser.start(stream);

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      cancelledRef.current = false;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        analyser.stop();
        setRecording(false);

        if (cancelledRef.current) {
          chunksRef.current = [];
          return;
        }

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 0) {
          setProcessing(true);
          onVoiceQuery(blob);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch {
      setRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  };

  const cancelRecording = () => {
    cancelledRef.current = true;
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try { recorder.stop(); } catch {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        analyser.stop();
        setRecording(false);
        chunksRef.current = [];
      }
    } else {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      analyser.stop();
      setRecording(false);
      chunksRef.current = [];
    }
    setProcessing(false);
  };

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div className="shrink-0 border-t border-neutral-200 bg-white">
      <div className="max-w-3xl mx-auto px-6 py-4">
        {recording ? (
          <div className="flex items-center justify-center gap-3">
            <div className="flex-1 max-w-md">
              <div className="rounded-xl border border-red-200 bg-red-50/60 px-4 py-3 flex items-center gap-3">
                <span className="flex items-center gap-1.5 shrink-0">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-xs font-medium text-red-600 tabular-nums">{formatTime(elapsed)}</span>
                </span>
                <div className="flex-1 flex justify-center">
                  <AudioVisualizer levels={analyser.levels} barCount={24} active />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={stopRecording}
                className="btn-primary px-4 py-2"
              >
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
                Send
              </button>
              <button
                onClick={cancelRecording}
                className="btn-secondary px-3 py-2"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-4">
            <RecordButton
              isRecording={recording}
              isTranscribing={processing}
              onStart={startRecording}
              onStop={stopRecording}
            />
            <div className="text-sm text-neutral-400">
              {processing ? (
                "Processing…"
              ) : (
                "Tap the microphone to ask a question"
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
