import { useMemo } from "react";

interface Props {
  levels: Uint8Array;
  barCount?: number;
}

export function AudioVisualizer({ levels, barCount = 20 }: Props) {
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
    <div className="flex items-end gap-[2px] h-6">
      {bars.map((h, i) => (
        <span
          key={i}
          className="w-[3px] rounded-full bg-red-500 transition-all duration-75"
          style={{ height: `${Math.max(2, h * 24)}px` }}
        />
      ))}
    </div>
  );
}
