import { apiRequest, apiUrl } from "@/lib/api-client"

import type { Paper, UploadAccepted } from "./types"

export async function listPapers(): Promise<Paper[]> {
  const { items } = await apiRequest<{ items: Paper[] }>("/api/papers")
  return items
}

export function uploadPaper(file: File): Promise<UploadAccepted> {
  const body = new FormData()
  body.append("file", file)
  return apiRequest<UploadAccepted>("/api/papers", { method: "POST", body })
}

export function deletePaper(paperId: string): Promise<void> {
  return apiRequest<void>(`/api/papers/${paperId}`, { method: "DELETE" })
}

export function retryPaper(paperId: string): Promise<UploadAccepted | undefined> {
  return apiRequest<UploadAccepted | undefined>(`/api/papers/${paperId}/retry`, {
    method: "POST",
  })
}

export function paperFileUrl(paperId: string, page?: number): string {
  const url = apiUrl(`/api/papers/${paperId}/file`)
  // Browser PDF viewers honour #page=N; support varies, the file still opens without it.
  return page ? `${url}#page=${page}` : url
}
