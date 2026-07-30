import { useRef, useEffect, useState, useCallback } from "react";

export function useAudioAnalyser() {
  const ctxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const frameRef = useRef<number>(0);
  const [levels, setLevels] = useState<Uint8Array>(new Uint8Array(0));

  const start = useCallback(async (stream: MediaStream) => {
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 64;
    const source = ctx.createMediaStreamSource(stream);
    source.connect(analyser);

    ctxRef.current = ctx;
    analyserRef.current = analyser;
    sourceRef.current = source;

    const data = new Uint8Array(analyser.frequencyBinCount);

    const tick = () => {
      analyser.getByteFrequencyData(data);
      setLevels(new Uint8Array(data));
      frameRef.current = requestAnimationFrame(tick);
    };
    tick();
  }, []);

  const stop = useCallback(() => {
    cancelAnimationFrame(frameRef.current);
    sourceRef.current?.disconnect();
    ctxRef.current?.close();
    sourceRef.current = null;
    analyserRef.current = null;
    ctxRef.current = null;
    setLevels(new Uint8Array(0));
  }, []);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  return { levels, start, stop };
}
