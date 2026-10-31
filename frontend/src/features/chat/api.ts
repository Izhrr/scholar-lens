import { apiRequest } from "@/lib/api-client"

import type { AskPayload, AskResponse, ChatMessage, ChatSession } from "./types"

export async function listChats(): Promise<ChatSession[]> {
  const { items } = await apiRequest<{ items: ChatSession[] }>("/api/chats")
  return items
}

export function createChat(): Promise<ChatSession> {
  return apiRequest<ChatSession>("/api/chats", { method: "POST" })
}

export async function listMessages(chatId: string): Promise<ChatMessage[]> {
  const { items } = await apiRequest<{ items: ChatMessage[] }>(`/api/chats/${chatId}/messages`)
  return items
}

export function askQuestion(chatId: string, payload: AskPayload): Promise<AskResponse> {
  return apiRequest<AskResponse>(`/api/chats/${chatId}/messages`, {
    method: "POST",
    json: payload,
  })
}
