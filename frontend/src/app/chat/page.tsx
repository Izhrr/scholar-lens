import type { Metadata } from "next"
import { Suspense } from "react"

import { ChatView } from "@/features/chat/components/chat-view"

export const metadata: Metadata = { title: "Research chat" }

export default function ChatPage() {
  return (
    // ChatView reads ?session= from the URL, which needs a Suspense boundary.
    <Suspense>
      <ChatView />
    </Suspense>
  )
}
