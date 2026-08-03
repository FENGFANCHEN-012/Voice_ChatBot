import { useMemo } from "react";

interface Props {
  levels: Uint8Array;
  barCount?: number;
  active?: boolean;
}

export function AudioVisualizer({ levels, barCount = 24, active = false }: Props) {
  const bars = useMemo(() => {
    if (levels.length === 0) return new Array(barCount).fill(0);
    const step = Math.max(1, Math.floor(levels.length / barCount));
    const result: number[] = [];
    for (let i = 0; i < barCount; i++) {
      const idx = Math.min(i * step, levels.length - 1);
      result.push(levels[idx] / 255);
    }
    return result;
  }, [levels, barCount]);

  return (
    <div className="flex items-center gap-[3px] h-6">
      {bars.map((h, i) => (
        <span
          key={i}
          className={`w-[3px] rounded-full ${active ? "bg-brand-500" : "bg-neutral-300"}`}
          style={{ height: `${Math.max(3, h * 24)}px`, transition: "height 75ms ease" }}
        />
      ))}
    </div>
  );
}
