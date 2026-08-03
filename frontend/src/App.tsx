import { useState, useEffect, useCallback, useRef } from "react";
import { AppShell } from "./components/layout/AppShell";
import { Header } from "./components/layout/Header";
import { SessionList } from "./components/chat/SessionList";
import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import { FileDropzone } from "./components/upload/FileDropzone";
import { FileList } from "./components/upload/FileList";
import { UploadProgress } from "./components/upload/UploadProgress";
import { Button } from "./components/common/Button";

import {
  uploadDocument, listDocuments, deleteDocument,
  createSession, listSessions, getMessages,
  queryChatStream, transcribeAudio, subscribeToProgress,
  deleteSession, renameSession,
} from "./services/api";

import { useTtsSocket } from "./hooks/useTtsSocket";

import type { Document, Session, Message } from "./types";

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadPhase, setUploadPhase] = useState<"uploading" | "embedding" | "done" | "error">("uploading");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [embedCurrent, setEmbedCurrent] = useState(0);
  const [embedTotal, setEmbedTotal] = useState(0);
  const [uploadFilename, setUploadFilename] = useState("");
  const [uploadError, setUploadError] = useState("");
  const cleanupSSE = useRef<(() => void) | null>(null);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const initRef = useRef(false);
  const { play: playTts } = useTtsSocket();

  const fetchDocs = useCallback(async () => {
    try { const { data } = await listDocuments(); setDocuments(data); } catch {}
  }, []);

  const fetchSessions = useCallback(async () => {
    try { const { data } = await listSessions(); setSessions(data); } catch {}
  }, []);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    fetchDocs();
    fetchSessions();
  }, [fetchDocs, fetchSessions]);

  useEffect(() => {
    if (!currentId) return;
    getMessages(currentId).then(({ data }) => setMessages(data)).catch(() => {});
  }, [currentId]);

  const handleCreateSession = async () => {
    try {
      const { data } = await createSession();
      setSessions((prev) => [...prev, data]);
      setCurrentId(data.session_id);
      setMessages([]);
    } catch {}
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (currentId === sessionId) {
        setCurrentId(null);
        setMessages([]);
      }
    } catch {}
  };

  const handleRenameSession = async (sessionId: string, title: string) => {
    try {
      const { data } = await renameSession(sessionId, title);
      setSessions((prev) => prev.map((s) => (s.session_id === sessionId ? data : s)));
    } catch {}
  };

  const handleVoiceQuery = async (blob: Blob) => {
    if (!currentId) return;
    setSending(true);
    const botMsgId = crypto.randomUUID();
    const userMsg: Message = { role: "user", content: "🎤 Voice input", timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);

    let fullAnswer = "";
    let lastTtsIndex = 0;
    let ttsTimer: ReturnType<typeof setTimeout> | null = null;

    const updateBot = (patch: Partial<Message>) => {
      setMessages((prev) => {
        const exists = prev.some((m) => m.id === botMsgId);
        if (exists) {
          return prev.map((m) => (m.id === botMsgId ? { ...m, ...patch } : m));
        }
        return [...prev, { id: botMsgId, role: "assistant", content: "", timestamp: new Date().toISOString(), ...patch }];
      });
    };

    const flushTts = (force = false) => {
      if (ttsTimer) {
        clearTimeout(ttsTimer);
        ttsTimer = null;
      }
      let pending = fullAnswer.slice(lastTtsIndex);
      if (!pending) return;

      let ready = "";
      let consumed = 0;
      const MAX_SEGMENT = 350;

      while (consumed < pending.length && ready.length < MAX_SEGMENT) {
        const match = pending.slice(consumed).match(/^[\s\S]*?[.!?。！？\n]+/);
        if (!match) break;
        consumed += match[0].length;
        ready += match[0];
      }

      if (ready) {
        const seg = ready.trim();
        lastTtsIndex += consumed;
        if (seg) playTts(seg);
      }

      const tail = pending.slice(consumed).trim();
      if (!tail) return;
      if (!force) {
        ttsTimer = setTimeout(() => flushTts(true), 400);
      } else {
        lastTtsIndex = fullAnswer.length;
        playTts(tail);
      }
    };

    try {
      const transcript = await transcribeAudio(blob);
      const text = transcript.data.text;

      await queryChatStream(
        currentId,
        text,
        (token) => {
          fullAnswer += token;
          updateBot({ content: fullAnswer });

          if (ttsTimer) {
            clearTimeout(ttsTimer);
            ttsTimer = null;
          }
          ttsTimer = setTimeout(flushTts, 400);
        },
        (chunks) => {
          updateBot({ chunks });
          flushTts(true);
          setSending(false);
        },
      );
    } catch {
      updateBot({ content: "Sorry, I couldn't process that." });
    } finally {
      if (ttsTimer) {
        clearTimeout(ttsTimer);
        ttsTimer = null;
      }
      setSending(false);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadPhase("uploading");
    setUploadProgress(0);
    setEmbedCurrent(0);
    setEmbedTotal(0);
    setUploadFilename(file.name);
    setUploadError("");
    try {
      const { data } = await uploadDocument(file, setUploadProgress);
      setUploadPhase("embedding");
      setEmbedTotal(data.total_chunks);
      setDocuments((prev) => [...prev, data]);

      cleanupSSE.current = subscribeToProgress(
        data.doc_id,
        (current, total) => {
          setEmbedCurrent(current);
          setEmbedTotal(total);
        },
        async () => {
          setUploadPhase("done");
          try {
            const { data: docs } = await listDocuments();
            setDocuments(docs);
          } catch {}
          setTimeout(() => setUploadProgress(0), 2000);
        },
        (msg) => {
          setUploadPhase("error");
          setUploadError(msg);
        },
      );
    } catch {
      setUploadPhase("error");
      setUploadError("Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch {}
  };

  const sidebar = (
    <div className="flex flex-col h-full px-3 pb-4 space-y-5">
      <section>
        <SessionList sessions={sessions} currentId={currentId} onSelect={setCurrentId} onCreate={handleCreateSession} onDelete={handleDeleteSession} onRename={handleRenameSession} />
      </section>

      <div className="border-t border-neutral-100" />

      <section>
        <h2 className="section-label px-2 mb-1.5">Knowledge base</h2>
        <FileDropzone onUpload={handleUpload} disabled={uploading} />
        {uploadProgress > 0 && (
          <div className="mt-2 px-1">
            <UploadProgress
              phase={uploadPhase}
              uploadProgress={uploadProgress}
              embedCurrent={embedCurrent}
              embedTotal={embedTotal}
              filename={uploadFilename}
              errorMsg={uploadError}
            />
          </div>
        )}
      </section>
      <section className="-mt-3 px-2">
        <FileList documents={documents} onDelete={handleDelete} />
      </section>
    </div>
  );

  const activeSession = sessions.find((s) => s.session_id === currentId);

  const chatArea = currentId ? (
    <>
      <Header
        title={activeSession?.title?.trim() || `Chat ${currentId.slice(0, 8)}`}
        subtitle={`${documents.length} document${documents.length === 1 ? "" : "s"}`}
      />
      <ChatWindow messages={messages} loading={sending} />
      <ChatInput onVoiceQuery={handleVoiceQuery} disabled={sending} />
    </>
  ) : (
    <>
      <Header subtitle={`${documents.length} document${documents.length === 1 ? "" : "s"}`} />
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-sm space-y-4">
          <div className="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <div className="space-y-1">
            <h2 className="text-[15px] font-semibold text-neutral-800">Start a conversation</h2>
            <p className="text-sm text-neutral-500">Create a chat, then ask questions with your voice.</p>
          </div>
          <Button variant="primary" size="md" onClick={handleCreateSession}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New chat
          </Button>
        </div>
      </div>
    </>
  );

  return (
    <AppShell sidebar={sidebar}>
      {chatArea}
    </AppShell>
  );
}

export default App;
