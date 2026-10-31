import type { Metadata } from "next"

import { KnowledgeView } from "@/features/papers/components/knowledge-view"

export const metadata: Metadata = { title: "Knowledge" }

export default function KnowledgePage() {
  return <KnowledgeView />
}
