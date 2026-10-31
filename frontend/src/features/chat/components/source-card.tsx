"use client"

import { ExternalLink } from "lucide-react"
import { useState } from "react"

import { paperFileUrl } from "@/features/papers/api"

import type { Source } from "../types"
import { sourceAnchor } from "./answer-text"

const EXCERPT_PREVIEW = 220

export function SourceCard({ source, messageId }: { source: Source; messageId: string }) {
  const [expanded, setExpanded] = useState(false)
  const long = source.excerpt.length > EXCERPT_PREVIEW
  const excerpt =
    expanded || !long ? source.excerpt : `${source.excerpt.slice(0, EXCERPT_PREVIEW).trimEnd()}…`

  return (
    <li
      id={sourceAnchor(messageId, source.citation_number)}
      className="flex scroll-mt-24 flex-col gap-3 rounded-lg border bg-card p-4 transition-colors target:border-primary"
    >
      <div className="flex items-start gap-3">
        <span className="grid size-6 shrink-0 place-items-center rounded bg-primary-soft text-xs font-semibold text-primary">
          {source.citation_number}
        </span>
        <div className="min-w-0">
          <p className="line-clamp-2 font-serif text-[15px] font-semibold leading-snug">
            {source.paper_title}
          </p>
          <p className="text-xs text-muted-foreground">Page {source.page_number}</p>
        </div>
      </div>
      <blockquote className="border-l-2 border-border pl-3 text-sm leading-relaxed text-muted-foreground">
        {excerpt}
      </blockquote>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        {long && (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="rounded font-medium text-foreground underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            {expanded ? "Show less" : "Show full passage"}
          </button>
        )}
        {source.paper_id ? (
          <a
            href={paperFileUrl(source.paper_id, source.page_number)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded font-medium text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            Open page {source.page_number}
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </a>
        ) : (
          <span className="text-muted-foreground">Paper deleted. Excerpt kept for this chat.</span>
        )}
      </div>
    </li>
  )
}
