import { useRef, useCallback } from "react";

export function useTtsSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const play = useCallback((text: string) => {
    if (!text.trim()) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    chunksRef.current = [];

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/tts`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        chunksRef.current.push(event.data);
      } else {
        try {
          const msg = JSON.parse(event.data);
          if (msg.status === "done" && chunksRef.current.length > 0) {
            const blob = new Blob(chunksRef.current, { type: "audio/mpeg" });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audioRef.current = audio;
            audio.onended = () => URL.revokeObjectURL(url);
            audio.play();
          }
        } catch {}
      }
    };

    ws.onopen = () => {
      ws.send(JSON.stringify({ text }));
    };

    ws.onerror = () => {};
  }, []);

  return { play };
}
