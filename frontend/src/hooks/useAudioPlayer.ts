import { useState, useRef, useCallback } from "react";

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const play = useCallback((blob: Blob) => {
    if (!blob || blob.size < 100) {
      console.warn("Audio blob is empty or invalid.");
      setIsPlaying(false);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audioRef.current = audio;

    const cleanup = () => {
      URL.revokeObjectURL(url);
      if (audioRef.current === audio) {
        audioRef.current = null;
      }
      setIsPlaying(false);
    };

    audio.onended = cleanup;
    audio.onerror = (e) => {
      console.error("Audio playback error:", e);
      cleanup();
    };

    setIsPlaying(true);
    audio.play().catch((err) => {
      console.warn("Audio play() promise rejected:", err);
      cleanup();
    });
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  return { isPlaying, play, stop };
}

