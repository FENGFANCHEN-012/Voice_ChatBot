import { useState, useEffect, useCallback, useRef } from "react";
import { AppShell } from "./components/layout/AppShell";
import { SessionList } from "./components/chat/SessionList";
import { ChatWindow } from "./components/chat/ChatWindow";
import { ChatInput } from "./components/chat/ChatInput";
import { FileDropzone } from "./components/upload/FileDropzone";
import { FileList } from "./components/upload/FileList";
import { UploadProgress } from "./components/upload/UploadProgress";

// import the API functions and types
import {
  uploadDocument, listDocuments, deleteDocument,
  createSession, listSessions, queryChat, getMessages,
  voiceQuery, synthesizeSpeech,
} from "./services/api";


import type { Document, Session, Message } from "./types";

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadFilename, setUploadFilename] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const initRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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


  const playTts = useCallback(async (text: string) => {
    try {
      const { data } = await synthesizeSpeech(text);
      const url = URL.createObjectURL(data);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => URL.revokeObjectURL(url);
      audio.play();
    } catch {}
  }, []);
  

  const handleCreateSession = async () => {
    try {
      const { data } = await createSession();
      setSessions((prev) => [...prev, data]);
      setCurrentId(data.session_id);
      setMessages([]);
    } catch {}
  };

  const handleSend = async (text: string) => {
    if (!currentId) return;
    setSending(true);
    const userMsg: Message = { role: "user", content: text, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const { data } = await queryChat(currentId, text);
      const botMsg: Message = { role: "assistant", content: data.answer_text, timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, botMsg]);
      playTts(data.answer_text);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I couldn't process that request.", timestamp: new Date().toISOString() }]);
    } finally {
      setSending(false);
    }
  };

  const handleVoiceQuery = async (blob: Blob) => {
    if (!currentId) return;
    setSending(true);
    const userMsg: Message = { role: "user", content: "🎤 Voice input", timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const { data } = await voiceQuery(currentId, blob);
      const botMsg: Message = { role: "assistant", content: data.answer_text, timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, botMsg]);
      playTts(data.answer_text);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I couldn't process that.", timestamp: new Date().toISOString() }]);
    } finally {
      setSending(false);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setProgress(0);
    setUploadFilename(file.name);
    try {
      const { data } = await uploadDocument(file, setProgress);
      setProgress(100);
      setDocuments((prev) => [...prev, data]);
      setTimeout(() => setProgress(0), 1500);
    } catch {
      setProgress(0);
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
    <div className="p-4 space-y-6">
      <section>
        <h2 className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-3">Upload</h2>
        <FileDropzone onUpload={handleUpload} disabled={uploading} />
        {uploading && (
          <div className="mt-3"><UploadProgress progress={progress} filename={uploadFilename} /></div>
        )}
      </section>
      <section>
        <h2 className="text-xs font-medium uppercase tracking-wider text-stone-400 mb-3">Documents</h2>
        <FileList documents={documents} onDelete={handleDelete} />
      </section>
      <section>
        <SessionList sessions={sessions} currentId={currentId} onSelect={setCurrentId} onCreate={handleCreateSession} />
      </section>
    </div>
  );

  const chatArea = currentId ? (
    <>
      <ChatWindow messages={messages} loading={sending} />
      <ChatInput onSend={handleSend} onVoiceQuery={handleVoiceQuery} disabled={sending} />
    </>
  ) : (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-2">
        <p className="text-sm text-stone-400">Select a chat or create a new one</p>
        <button onClick={handleCreateSession} className="text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors">
          + New Chat
        </button>
      </div>
    </div>
  );

  return (
    <AppShell sidebar={sidebar}>
      {chatArea}
    </AppShell>
  );
}

export default App;
