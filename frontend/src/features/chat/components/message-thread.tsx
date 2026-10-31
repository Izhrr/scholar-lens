"use client"

import { Check, Copy, Loader2 } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { plural } from "@/lib/format"

import type { ChatMessage } from "../types"
import { AnswerText } from "./answer-text"
import { SourceCard } from "./source-card"

export function UserQuestion({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] rounded-lg bg-secondary px-4 py-2.5 whitespace-pre-wrap text-secondary-foreground">
        {content}
      </p>
    </div>
  )
}

export function AssistantAnswer({ message }: { message: ChatMessage }) {
  const citationNumbers = new Set(message.sources.map((source) => source.citation_number))
  return (
    <article className="flex flex-col gap-5" aria-label="Answer">
      <AnswerText text={message.content} messageId={message.id} citationNumbers={citationNumbers} />

      {message.sources.length > 0 ? (
        <section aria-label="Sources" className="flex flex-col gap-3">
          <h3 className="flex items-baseline justify-between text-sm font-semibold">
            Sources
            <span className="text-xs font-normal text-muted-foreground">
              {plural(message.sources.length, "citation")}
            </span>
          </h3>
          <ol className="grid gap-3 lg:grid-cols-2">
            {message.sources.map((source) => (
              <SourceCard key={source.citation_number} source={source} messageId={message.id} />
            ))}
          </ol>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">No passages cited for this reply.</p>
      )}

      <div>
        <CopyButton text={message.content} />
      </div>
    </article>
  )
}

export function PendingAnswer() {
  return (
    <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      Searching your papers and writing a cited answer…
    </p>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-9 text-muted-foreground"
      onClick={async () => {
        await navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
      {copied ? "Copied" : "Copy answer"}
    </Button>
  )
}
