import { useState } from "react";
import type { ChunkInfo } from "../../types";

interface Props {
  role: "user" | "assistant";
  content: string;
  chunks?: ChunkInfo[];
}

export function MessageBubble({ role, content, chunks }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const isUser = role === "user";
  const isLong = content.length > 600;
  const hasCitations = !!chunks && chunks.length > 0;

  return (
    <div className={`flex animate-fade-in ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] sm:max-w-[75%] ${isUser ? "" : "w-full"}`}>
        {isUser ? (
          <div className="inline-block bg-neutral-800 text-white rounded-2xl rounded-br-md px-4 py-2.5">
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{content}</p>
          </div>
        ) : (
          <div className="bg-white border border-neutral-200 rounded-2xl rounded-bl-md shadow-card">
            <div className="px-4 py-3.5">
              <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words text-neutral-800">
                {expanded ? content : content.length > 600 ? content.slice(0, 600) + "…" : content}
              </p>
              {isLong && (
                <button
                  onClick={() => setExpanded((e) => !e)}
                  className="text-xs font-medium text-brand-600 hover:text-brand-700 mt-2.5 transition-colors duration-150"
                >
                  {expanded ? "Show less" : "Show more"}
                </button>
              )}
            </div>
            {hasCitations && (
              <div className="border-t border-neutral-100">
                <button
                  onClick={() => setShowCitations((s) => !s)}
                  className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-neutral-50 transition-colors duration-150 rounded-b-2xl"
                >
                  <svg className="w-3.5 h-3.5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-xs font-medium text-neutral-500">{showCitations ? "Hide" : "Show"} sources ({chunks.length})</span>
                  <svg
                    className={`w-3 h-3 text-neutral-400 ml-auto transition-transform duration-150 ${showCitations ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showCitations && (
                  <div className="px-4 pb-3 space-y-2 max-h-72 overflow-y-auto scrollbar-thin">
                    {chunks.map((chunk, i) => (
                      <div key={i} className="text-xs rounded-lg border border-neutral-100 bg-neutral-50/50 p-3">
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="font-medium text-neutral-500">
                            Page {chunk.page ?? "—"}
                          </span>
                          <span className="text-neutral-400 text-[11px]">
                            {(chunk.score * 100).toFixed(0)}% match
                          </span>
                        </div>
                        <p className="text-neutral-600 leading-relaxed line-clamp-2">{chunk.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
