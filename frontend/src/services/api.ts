import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 60000,
});

export async function uploadDocument(file: File, onProgress?: (pct: number) => void) {
  const form = new FormData();
  form.append("file", file);
  return api.post("/documents/upload", form, {
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

export async function queryChat(sessionId: string, text: string) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("text", text);
  return api.post("/chats/query", form);
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

export async function healthCheck() {
  return api.get("/health");
}

export default api;
