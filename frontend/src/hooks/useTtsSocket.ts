import { useRef, useCallback } from "react";

interface PlayItem {
  id: number;
  text: string;
  blob: Blob | null;
  status: "pending" | "synthesizing" | "ready" | "played";
}

export function useTtsSocket() {
  const itemsRef = useRef<PlayItem[]>([]);
  const seqRef = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const activeSynthRef = useRef(false);
  const activePlayRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const synthChunksRef = useRef<Blob[]>([]);
  const synthTargetRef = useRef<PlayItem | null>(null);

  const playSequence = useCallback(() => {
    if (activePlayRef.current) return;

    const nextItem = itemsRef.current[0];
    if (!nextItem || nextItem.status !== "ready" || !nextItem.blob) return;

    activePlayRef.current = true;
    const itemToPlay = itemsRef.current.shift()!;
    if (!itemToPlay.blob) {
      activePlayRef.current = false;
      playSequence();
      return;
    }

    const url = URL.createObjectURL(itemToPlay.blob);
    const audio = new Audio(url);
    audioRef.current = audio;

    const onEnded = () => {
      URL.revokeObjectURL(url);
      audioRef.current = null;
      activePlayRef.current = false;
      playSequence();
    };

    audio.onended = onEnded;
    audio.onerror = onEnded;
    audio.play().catch(onEnded);
  }, []);

  const synthesizeNext = useCallback(() => {
    if (activeSynthRef.current) return;

    const target = itemsRef.current.find((i) => i.status === "pending");
    if (!target) return;

    activeSynthRef.current = true;
    target.status = "synthesizing";
    synthTargetRef.current = target;
    synthChunksRef.current = [];

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/tts`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ text: target.text }));
    };

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        synthChunksRef.current.push(event.data);
        return;
      }

      try {
        const msg = JSON.parse(event.data);
        if (msg.status !== "done") return;

        const t = synthTargetRef.current;
        synthTargetRef.current = null;
        if (t) {
          t.blob = new Blob(synthChunksRef.current, { type: "audio/mpeg" });
          t.status = "ready";
        }
        synthChunksRef.current = [];
        activeSynthRef.current = false;
        try { ws.close(); } catch {}
        wsRef.current = null;
        playSequence();
        synthesizeNext();
      } catch {}
    };

    ws.onerror = () => {
      const t = synthTargetRef.current;
      synthTargetRef.current = null;
      if (t) t.status = "played";
      synthChunksRef.current = [];
      activeSynthRef.current = false;
      try { ws.close(); } catch {}
      wsRef.current = null;
      playSequence();
      synthesizeNext();
    };
  }, [playSequence]);

  const play = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      itemsRef.current.push({
        id: seqRef.current++,
        text: text.trim(),
        blob: null,
        status: "pending",
      });
      synthesizeNext();
    },
    [synthesizeNext],
  );

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    try { wsRef.current?.close(); } catch {}
    wsRef.current = null;
    itemsRef.current = [];
    seqRef.current = 0;
    synthChunksRef.current = [];
    synthTargetRef.current = null;
    activeSynthRef.current = false;
    activePlayRef.current = false;
  }, []);

  return { play, stop };
}
