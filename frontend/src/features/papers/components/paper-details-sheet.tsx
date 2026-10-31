"use client"

import { ExternalLink, RotateCw, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { ApiError } from "@/lib/api-client"
import { formatBytes, formatDateTime } from "@/lib/format"

import { paperFileUrl } from "../api"
import { useRetryPaper } from "../queries"
import type { Paper } from "../types"
import { PaperStatusBadge } from "./paper-status-badge"

interface PaperDetailsSheetProps {
  paper: Paper | null
  onOpenChange: (open: boolean) => void
  onDelete: (paper: Paper) => void
}

export function PaperDetailsSheet({ paper, onOpenChange, onDelete }: PaperDetailsSheetProps) {
  return (
    <Sheet open={paper !== null} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        {paper && <PaperDetails paper={paper} onDelete={onDelete} />}
      </SheetContent>
    </Sheet>
  )
}

function PaperDetails({ paper, onDelete }: { paper: Paper; onDelete: (paper: Paper) => void }) {
  const retry = useRetryPaper()
  const canRetry = paper.status === "failed" || paper.status === "deleting"
  const busy = paper.status === "queued" || paper.status === "processing"

  const rows: [string, string][] = [
    ["File", paper.original_filename],
    ["Size", formatBytes(paper.file_size_bytes)],
    ["Pages", paper.page_count?.toString() ?? "Not read yet"],
    ["Passages indexed", paper.chunk_count.toString()],
    ["Added", formatDateTime(paper.created_at)],
    ["Last change", formatDateTime(paper.updated_at)],
    ["Embedding model", paper.embedding_model ?? "None yet"],
  ]

  async function handleRetry() {
    try {
      await retry.mutateAsync(paper.id)
      toast.success(paper.status === "deleting" ? "Deletion finished." : "Indexing restarted.")
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Retry failed.")
    }
  }

  return (
    <>
      <SheetHeader className="border-b px-6 pt-6 pb-5">
        <PaperStatusBadge status={paper.status} />
        <SheetTitle className="mt-2 pr-6 font-serif text-xl leading-snug">{paper.title}</SheetTitle>
        <SheetDescription>The PDF file stays on this machine.</SheetDescription>
      </SheetHeader>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {paper.error_message && (
          <p role="alert" className="mb-5 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {paper.error_message}
          </p>
        )}
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="min-w-0 break-words">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <SheetFooter className="flex-row flex-wrap gap-2 border-t px-6 py-4">
        <Button asChild variant="outline">
          <a href={paperFileUrl(paper.id)} target="_blank" rel="noreferrer">
            <ExternalLink aria-hidden="true" />
            Open PDF
          </a>
        </Button>
        {canRetry && (
          <Button variant="outline" onClick={handleRetry} disabled={retry.isPending}>
            <RotateCw aria-hidden="true" />
            {paper.status === "deleting" ? "Retry delete" : "Retry indexing"}
          </Button>
        )}
        <Button
          variant="destructive"
          className="ml-auto"
          disabled={busy || paper.status === "deleting"}
          onClick={() => onDelete(paper)}
        >
          <Trash2 aria-hidden="true" />
          Delete
        </Button>
      </SheetFooter>
    </>
  )
}
