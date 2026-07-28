export interface Session {
  session_id: string;
  created_at: string;
  message_count?: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface Document {
  doc_id: string;
  filename: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface ChunkInfo {
  content: string;
  page: number;
  score: number;
}

export interface QueryResponse {
  answer_text: string;
  audio_url: string;
  chunks: ChunkInfo[];
}

export interface TranscribeResponse {
  text: string;
  language: string;
  duration: number;
}
