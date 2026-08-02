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

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-slide-up`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] lg:max-w-[65%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-stone-800 text-stone-100 rounded-br-md"
            : "bg-stone-100 text-stone-800 rounded-bl-md"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <>
            <p className="whitespace-pre-wrap break-words">
              {expanded ? content : content.length > 600 ? content.slice(0, 600) + "..." : content}
            </p>
            {content.length > 600 && (
              <button
                onClick={() => setExpanded((e) => !e)}
                className="text-xs text-stone-500 hover:text-stone-700 mt-1 font-medium"
              >
                {expanded ? "Show less" : "Show more"}
              </button>
            )}
            {chunks && chunks.length > 0 && (
              <div className="mt-2 border-t border-stone-200 pt-2">
                <button
                  onClick={() => setShowCitations((s) => !s)}
                  className="text-xs text-stone-500 hover:text-stone-700 font-medium flex items-center gap-1"
                >
                  <svg className={`w-3 h-3 transition-transform ${showCitations ? "rotate-90" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  Sources ({chunks.length})
                </button>
                {showCitations && (
                  <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                    {chunks.map((chunk, i) => (
                      <div key={i} className="text-xs bg-stone-50 rounded p-2 border border-stone-200">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-stone-500 font-medium">Page {chunk.page || "?"}</span>
                          <span className="text-stone-400">{(chunk.score * 100).toFixed(0)}% match</span>
                        </div>
                        <p className="text-stone-600 line-clamp-2">{chunk.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
