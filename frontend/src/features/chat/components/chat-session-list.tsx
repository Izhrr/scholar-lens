"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"

import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

import { useChats } from "../queries"
import type { ChatSession } from "../types"

const DAY_MS = 24 * 60 * 60 * 1000

function groupByAge(sessions: ChatSession[]): [string, ChatSession[]][] {
  const startOfToday = new Date()
  startOfToday.setHours(0, 0, 0, 0)
  const today = startOfToday.getTime()
  const groups = new Map<string, ChatSession[]>()
  for (const session of sessions) {
    const updated = new Date(session.updated_at).getTime()
    const label =
      updated >= today
        ? "Today"
        : updated >= today - DAY_MS
          ? "Yesterday"
          : updated >= today - 7 * DAY_MS
            ? "Previous 7 days"
            : "Older"
    groups.set(label, [...(groups.get(label) ?? []), session])
  }
  return [...groups.entries()]
}

export function ChatSessionList({ onNavigate }: { onNavigate?: () => void }) {
  const { data: sessions, isLoading, isError } = useChats()
  const activeId = useSearchParams().get("session")

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 px-3" aria-busy="true" aria-label="Loading chats">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-4/5" />
      </div>
    )
  }
  if (isError) {
    return <p className="px-3 text-sm text-muted-foreground">Chats could not load.</p>
  }
  if (!sessions?.length) {
    return (
      <p className="px-3 text-sm text-muted-foreground">
        No chats yet. Your questions are saved here.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {groupByAge(sessions).map(([label, items]) => (
        <div key={label}>
          <h3 className="px-3 pb-1 text-xs font-medium text-muted-foreground">{label}</h3>
          <ul className="flex flex-col gap-0.5">
            {items.map((session) => {
              const active = session.id === activeId
              return (
                <li key={session.id}>
                  <Link
                    href={`/chat?session=${session.id}`}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    title={session.title}
                    className={cn(
                      "block truncate rounded-md px-3 py-2 text-sm outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                      active
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-foreground/80 hover:bg-sidebar-accent/60 hover:text-foreground"
                    )}
                  >
                    {session.title}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </div>
  )
}
