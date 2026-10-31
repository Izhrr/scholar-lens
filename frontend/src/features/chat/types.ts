export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Source {
  citation_number: number
  chunk_id: string | null
  paper_id: string | null
  paper_title: string
  page_number: number
  excerpt: string
  rrf_score: number | null
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  model: string | null
  created_at: string
  sources: Source[]
}

export interface AskPayload {
  question: string
  // null searches every indexed paper; the API rejects an empty list.
  paper_ids: string[] | null
}

export interface AskResponse {
  message_id: string
  user_message_id: string
  answer: string
  grounded: boolean
  sources: Source[]
  retrieval: { bm25_candidates: number; dense_candidates: number; selected_chunks: number }
}

export const QUESTION_MAX_LENGTH = 2000
export const SCOPE_MAX_PAPERS = 20
