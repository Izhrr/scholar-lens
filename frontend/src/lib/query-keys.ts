export const queryKeys = {
  papers: ["papers"] as const,
  chats: ["chats"] as const,
  chatMessages: (chatId: string) => ["chats", chatId, "messages"] as const,
}
