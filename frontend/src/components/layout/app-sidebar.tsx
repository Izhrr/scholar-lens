"use client"

import { BookOpen, MessageSquareText, Plus } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Suspense } from "react"

import { Button } from "@/components/ui/button"
import { ChatSessionList } from "@/features/chat/components/chat-session-list"
import { cn } from "@/lib/utils"

import { ThemeToggle } from "./theme-toggle"
import { Wordmark } from "./wordmark"

const NAV = [
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/chat", label: "Research chat", icon: MessageSquareText },
] as const

export function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  const onChat = pathname.startsWith("/chat")

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="px-5 pt-6 pb-5">
        <Wordmark />
      </div>

      <nav aria-label="Main" className="px-3">
        <ul className="flex flex-col gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href)
            return (
              <li key={href}>
                <Link
                  href={href}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex h-11 items-center gap-3 rounded-md px-3 text-[15px] outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                    active
                      ? "bg-primary-soft font-medium text-primary"
                      : "text-foreground/80 hover:bg-sidebar-accent hover:text-foreground"
                  )}
                >
                  <Icon className="size-4.5" aria-hidden="true" />
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {onChat && (
        <section aria-labelledby="chats-heading" className="mt-6 flex min-h-0 flex-1 flex-col border-t pt-4">
          <div className="flex items-center justify-between px-5 pb-2">
            <h2 id="chats-heading" className="text-sm font-semibold">
              Conversations
            </h2>
            <Button asChild variant="ghost" size="icon" className="size-9">
              <Link href="/chat" onClick={onNavigate} aria-label="Start a new chat">
                <Plus aria-hidden="true" />
              </Link>
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
            <Suspense fallback={null}>
              <ChatSessionList onNavigate={onNavigate} />
            </Suspense>
          </div>
        </section>
      )}

      <div className="mt-auto flex flex-col gap-3 border-t p-4">
        <ThemeToggle />
        <p className="text-xs leading-relaxed text-muted-foreground">
          Local workspace. PDFs stay on this machine; questions and matching passages are sent to
          OpenAI.
        </p>
      </div>
    </div>
  )
}
