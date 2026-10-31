"use client"

import { AlertCircle, Plus } from "lucide-react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useIndexedPapers } from "@/features/papers/queries"

import { useAskQuestion, useChatMessages } from "../queries"
import { Composer } from "./composer"
import { AssistantAnswer, PendingAnswer, UserQuestion } from "./message-thread"
import { ScopePicker } from "./scope-picker"

export function ChatView() {
  const router = useRouter()
  const chatId = useSearchParams().get("session")
  const { papers, isLoading: papersLoading } = useIndexedPapers()
  const messages = useChatMessages(chatId)
  const ask = useAskQuestion()
  const [draft, setDraft] = useState("")
  const [scope, setScope] = useState<string[] | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Drop selections for papers that were deleted since they were picked.
  const indexedIds = new Set(papers.map((paper) => paper.id))
  const activeScope = scope?.filter((id) => indexedIds.has(id)) ?? null
  const effectiveScope = activeScope && activeScope.length > 0 ? activeScope : null

  const pendingQuestion = ask.isPending ? ask.variables?.question : undefined
  const failed = ask.isError && ask.variables?.chatId === chatId

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" })
  }, [messages.data?.length, pendingQuestion])

  function submit() {
    const question = draft.trim()
    setDraft("")
    ask.mutate(
      { chatId, question, paper_ids: effectiveScope },
      {
        onSuccess: ({ chatId: id }) => {
          if (id !== chatId) router.replace(`/chat?session=${id}`)
        },
        // Give the question back so a failed request costs no retyping.
        onError: () => setDraft(question),
      }
    )
  }

  const noPapers = !papersLoading && papers.length === 0
  const thread = messages.data ?? []

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-8">
        <div className="min-w-0 flex-1">
          {papers.length > 0 && (
            <ScopePicker papers={papers} value={effectiveScope} onChange={setScope} />
          )}
        </div>
        <Button asChild variant="outline" className="h-11 shrink-0">
          <Link href="/chat" onClick={() => ask.reset()}>
            <Plus aria-hidden="true" />
            New chat
          </Link>
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-8 sm:px-8">
          {chatId && messages.isLoading && <ThreadSkeleton />}

          {chatId && messages.isError && (
            <ErrorNote
              message={`${messages.error.message} This chat may have been removed.`}
              action={
                <Button variant="outline" size="sm" className="h-9" onClick={() => messages.refetch()}>
                  Retry
                </Button>
              }
            />
          )}

          {!chatId && thread.length === 0 && !pendingQuestion && (
            <Intro noPapers={noPapers} loading={papersLoading} />
          )}

          {thread.map((message) =>
            message.role === "user" ? (
              <UserQuestion key={message.id} content={message.content} />
            ) : (
              <AssistantAnswer key={message.id} message={message} />
            )
          )}

          {pendingQuestion && (
            <>
              <UserQuestion content={pendingQuestion} />
              <PendingAnswer />
            </>
          )}

          {failed && (
            <ErrorNote message={`${ask.error.message} Your question is back in the box below.`} />
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t bg-background px-4 pt-3 pb-4 sm:px-8">
        <div className="mx-auto w-full max-w-3xl">
          <Composer
            value={draft}
            onChange={setDraft}
            onSubmit={submit}
            disabled={noPapers}
            busy={ask.isPending}
          />
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Answers can be wrong. Check claims against the cited pages before you rely on them.
          </p>
        </div>
      </div>
    </div>
  )
}

function Intro({ noPapers, loading }: { noPapers: boolean; loading: boolean }) {
  if (loading) return <ThreadSkeleton />
  if (noPapers) {
    return (
      <div className="flex flex-col items-start gap-3 py-10">
        <h1 className="font-serif text-3xl font-semibold tracking-tight">No papers to search yet</h1>
        <p className="max-w-lg text-muted-foreground">
          Chat answers only come from papers in your library. Add a PDF and wait until it shows
          Indexed, then come back here.
        </p>
        <Button asChild className="mt-2 h-11">
          <Link href="/knowledge">Add a paper</Link>
        </Button>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-3 py-10">
      <h1 className="font-serif text-3xl font-semibold tracking-tight">Ask your papers</h1>
      <p className="max-w-lg text-muted-foreground">
        Each answer quotes the passages it used, with the paper and page, so you can check every
        claim. If the papers do not cover a question, ScholarLens says so instead of guessing.
      </p>
    </div>
  )
}

function ThreadSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading conversation">
      <Skeleton className="ml-auto h-10 w-2/5" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-11/12" />
      <Skeleton className="h-4 w-3/5" />
    </div>
  )
}

function ErrorNote({ message, action }: { message: string; action?: React.ReactNode }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg bg-destructive/10 p-4 text-sm text-destructive"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <p className="flex-1">{message}</p>
      {action}
    </div>
  )
}
