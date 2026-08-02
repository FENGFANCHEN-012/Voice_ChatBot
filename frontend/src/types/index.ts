export interface Session {
  session_id: string;
  created_at: string;
  message_count?: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  chunks?: ChunkInfo[];
}

export interface Document {
  doc_id: string;
  filename: string;
  file_path: string;
  chunk_count: number;
  total_chunks: number;
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
