"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { queryKeys } from "@/lib/query-keys"

import { askQuestion, createChat, listChats, listMessages } from "./api"
import type { AskPayload, ChatMessage } from "./types"

export function useChats() {
  return useQuery({ queryKey: queryKeys.chats, queryFn: listChats })
}

export function useChatMessages(chatId: string | null) {
  return useQuery({
    queryKey: queryKeys.chatMessages(chatId ?? "new"),
    queryFn: () => listMessages(chatId!),
    enabled: chatId !== null,
  })
}

interface AskVariables extends AskPayload {
  chatId: string | null
}

export function useAskQuestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ chatId, question, paper_ids }: AskVariables) => {
      // A session is created on the first question, so empty chats never pile up.
      const id = chatId ?? (await createChat()).id
      const response = await askQuestion(id, { question, paper_ids })
      return { chatId: id, question, response }
    },
    onSuccess: ({ chatId, question, response }) => {
      const now = new Date().toISOString()
      const appended: ChatMessage[] = [
        { id: response.user_message_id, role: "user", content: question, model: null, created_at: now, sources: [] },
        { id: response.message_id, role: "assistant", content: response.answer, model: null, created_at: now, sources: response.sources },
      ]
      // Seed the cache so the answer shows instantly, then let the server copy win.
      queryClient.setQueryData<ChatMessage[]>(queryKeys.chatMessages(chatId), (old) => [
        ...(old ?? []),
        ...appended,
      ])
      void queryClient.invalidateQueries({ queryKey: queryKeys.chats })
    },
  })
}
