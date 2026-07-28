import { useState, useRef, useCallback } from "react";

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const play = useCallback((blob: Blob) => {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => {
      URL.revokeObjectURL(url);
      setIsPlaying(false);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      setIsPlaying(false);
    };
    audioRef.current = audio;
    setIsPlaying(true);
    audio.play();
  }, []);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setIsPlaying(false);
  }, []);

  return { isPlaying, play, stop };
}
