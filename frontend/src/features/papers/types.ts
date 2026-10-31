export type PaperStatus = "queued" | "processing" | "indexed" | "failed" | "deleting"

export interface Paper {
  id: string
  title: string
  original_filename: string
  file_size_bytes: number
  page_count: number | null
  chunk_count: number
  status: PaperStatus
  error_message: string | null
  embedding_model: string | null
  created_at: string
  updated_at: string
}

export interface UploadAccepted {
  paper_id: string
  job_id: string | null
  status: PaperStatus
}

export const IN_PROGRESS_STATUSES: readonly PaperStatus[] = ["queued", "processing", "deleting"]
