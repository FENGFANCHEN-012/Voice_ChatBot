import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,
});


export async function uploadDocument(file: File, onProgress?: (pct: number) => void) {


  const form = new FormData();
  form.append("file", file);
 
  return api.post("/documents/upload", form, {
    timeout: 300000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    },
    
  });
}

export async function listDocuments() {
  return api.get("/documents/");
}

export async function deleteDocument(docId: string) {
  return api.delete(`/documents/${docId}`);
}

export async function createSession() {
  return api.post("/sessions");
}

export async function listSessions() {
  return api.get("/sessions");
}

export async function deleteSession(sessionId: string) {
  return api.delete(`/sessions/${sessionId}`);
}

export async function renameSession(sessionId: string, title: string) {
  const form = new FormData();
  form.append("title", title);
  return api.patch(`/sessions/${sessionId}`, form);
}

export async function queryChat(sessionId: string, text: string) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("text", text);
  return api.post("/chats/query", form);
}

export async function queryChatStream(
  sessionId: string,
  text: string,
  onToken: (token: string) => void,
  onDone: (chunks: Array<{content: string; page: number | null; score: number}>) => void,
): Promise<void> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("text", text);

  const response = await fetch("/api/v1/chats/query/stream", {
    method: "POST",
    body: form,
  });

  if (!response.ok) throw new Error("Query failed");

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === "token") {
            onToken(event.content);
          } else if (event.type === "done") {
            onDone(event.chunks);
          }
        } catch (e) {
          console.error("Failed to parse SSE event:", e);
        }
      }
    }
  }
}

export async function getMessages(sessionId: string) {
  return api.get(`/chats/${sessionId}/messages`);
}

export async function voiceQuery(sessionId: string, audio: Blob) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("audio", audio, "recording.webm");
  return api.post("/chats/voice-query", form);
}

export async function transcribeAudio(audio: Blob) {
  const form = new FormData();
  form.append("audio", audio, "recording.wav");
  return api.post("/audio/transcribe", form);
}

export async function synthesizeSpeech(text: string) {
  const form = new FormData();
  form.append("text", text);
  return api.post("/audio/synthesize", form, {
    responseType: "blob",
  });
}

export async function synthesizeSpeechStream(text: string) {
  const form = new FormData();
  form.append("text", text);
  const response = await fetch("/api/v1/audio/synthesize-stream", {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error("TTS failed");
  return response;
}

export function subscribeToProgress(
  docId: string,
  onProgress: (current: number, total: number) => void,
  onComplete: () => void,
  onError: (msg: string) => void,
): () => void {
  const es = new EventSource(`/api/v1/documents/${docId}/progress`);
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.status === "complete") {
      onComplete();
      es.close();
    } else if (data.status === "error") {
      onError(data.message || "Embedding failed");
      es.close();
    } else if (data.status === "not_found") {
      onError("Document not found");
      es.close();
    } else if (data.current !== undefined) {
      onProgress(data.current, data.total);
    }
  };
  es.onerror = () => {
    onError("Connection lost");
    es.close();
  };
  return () => es.close();
}

export async function healthCheck() {
  return api.get("/health");
}

export default api;
