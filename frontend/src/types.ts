export interface KnowledgeItem {
  id: number;
  title: string;
  category: string;
  content: string;
  source: string;
  citation_index?: number | null;
  relevance_score?: number | null;
  match_reason?: string | null;
  document_name?: string | null;
  document_path?: string | null;
  chunk_index?: number | null;
  chunk_total?: number | null;
  chunking_method?: string | null;
  embedding?: number[] | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgePayload {
  title: string;
  category: string;
  content: string;
  source: string;
  document_name?: string | null;
  document_path?: string | null;
  chunk_index?: number | null;
  chunk_total?: number | null;
  chunking_method?: string | null;
}

export type ChunkingMethod = 'fixed_size' | 'paragraph' | 'markdown_heading' | 'full_document';

export interface KnowledgeImportOptions {
  category: string;
  source: string;
  chunking_method: ChunkingMethod;
  chunk_size: number;
  chunk_overlap: number;
}

export interface KnowledgeImportResponse {
  filename: string;
  stored_file_path: string;
  imported_count: number;
  items: KnowledgeItem[];
}

export interface AskResponse {
  answer: string;
  qa_record_id: number;
  retrieved_context: KnowledgeItem[];
  model_provider: string;
}

export interface FeedbackPayload {
  qa_record_id: number;
  rating: 'like' | 'dislike';
  comment?: string;
}

export interface FeedbackItem {
  id: number;
  qa_record_id: number;
  rating: string;
  comment?: string | null;
  created_at: string;
}

export interface User {
  id: number;
  username: string;
  nickname?: string | null;
  created_at: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  nickname?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface QARecord {
  id: number;
  question: string;
  answer: string;
  retrieved_context: KnowledgeItem[];
  model_provider: string;
  status: 'active' | 'archived' | 'deleted';
  created_at: string;
  updated_at: string;
}

export interface QARecordListResponse {
  records: QARecord[];
  total: number;
  skip: number;
  limit: number;
}
