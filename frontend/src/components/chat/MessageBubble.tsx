import { useState } from "react";

interface Props {
  role: "user" | "assistant";
  content: string;
}

export function MessageBubble({ role, content }: Props) {
  const [expanded, setExpanded] = useState(false);
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
          </>
        )}
      </div>
    </div>
  );
}
