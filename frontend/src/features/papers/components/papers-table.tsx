"use client"

import { FileText, RotateCw, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ApiError } from "@/lib/api-client"
import { formatDate, plural } from "@/lib/format"

import { useRetryPaper } from "../queries"
import type { Paper } from "../types"
import { PaperStatusBadge } from "./paper-status-badge"

interface PapersTableProps {
  papers: Paper[]
  onOpen: (paper: Paper) => void
  onDelete: (paper: Paper) => void
}

export function PapersTable({ papers, onOpen, onDelete }: PapersTableProps) {
  return (
    <>
      <Table className="hidden table-fixed xl:table">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-5">Paper</TableHead>
            <TableHead className="w-32">Added</TableHead>
            <TableHead className="w-44">Size in index</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-40 pr-5 text-right">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {papers.map((paper) => (
            <TableRow key={paper.id}>
              <TableCell className="py-3 pl-5 whitespace-normal">
                <PaperTitleButton paper={paper} onOpen={onOpen} />
              </TableCell>
              <TableCell className="text-muted-foreground">{formatDate(paper.created_at)}</TableCell>
              <TableCell className="text-muted-foreground">
                <PaperSize paper={paper} />
              </TableCell>
              <TableCell>
                <PaperStatusBadge status={paper.status} />
              </TableCell>
              <TableCell className="pr-5 whitespace-normal">
                <RowActions paper={paper} onDelete={onDelete} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ul className="divide-y xl:hidden">
        {papers.map((paper) => (
          <li key={paper.id} className="flex flex-col gap-3 px-4 py-4">
            <PaperTitleButton paper={paper} onOpen={onOpen} />
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
              <PaperStatusBadge status={paper.status} />
              <span>{formatDate(paper.created_at)}</span>
              <PaperSize paper={paper} />
            </div>
            <RowActions paper={paper} onDelete={onDelete} />
          </li>
        ))}
      </ul>
    </>
  )
}

function PaperTitleButton({ paper, onOpen }: { paper: Paper; onOpen: (paper: Paper) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(paper)}
      className="group flex w-full min-w-0 items-start gap-3 rounded-md text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-md bg-primary-soft text-primary">
        <FileText className="size-4" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block truncate font-serif text-[15px] font-semibold group-hover:underline group-hover:underline-offset-4">
          {paper.title}
        </span>
        <span className="block truncate text-xs text-muted-foreground">
          {paper.original_filename}
        </span>
        {paper.status === "failed" && paper.error_message && (
          <span className="mt-1 line-clamp-2 block text-xs text-destructive">
            {paper.error_message}
          </span>
        )}
      </span>
    </button>
  )
}

function PaperSize({ paper }: { paper: Paper }) {
  if (paper.page_count === null) {
    return <span>{paper.status === "failed" ? "Not indexed" : "Waiting to read"}</span>
  }
  return (
    <span>
      {plural(paper.page_count, "page")} · {plural(paper.chunk_count, "passage")}
    </span>
  )
}

function RowActions({ paper, onDelete }: { paper: Paper; onDelete: (paper: Paper) => void }) {
  const retry = useRetryPaper()
  const canRetry = paper.status === "failed" || paper.status === "deleting"
  const busy = paper.status === "queued" || paper.status === "processing" || paper.status === "deleting"

  async function handleRetry() {
    try {
      await retry.mutateAsync(paper.id)
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Retry failed.")
    }
  }

  return (
    <div className="flex items-center justify-start gap-1 xl:justify-end">
      {canRetry && (
        <Button
          variant="ghost"
          size="sm"
          className="h-11 xl:h-8"
          onClick={handleRetry}
          disabled={retry.isPending}
        >
          <RotateCw aria-hidden="true" />
          {paper.status === "deleting" ? "Retry delete" : "Retry"}
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="size-11 text-muted-foreground hover:text-destructive xl:size-9"
        disabled={busy}
        onClick={() => onDelete(paper)}
        aria-label={`Delete ${paper.title}`}
      >
        <Trash2 aria-hidden="true" />
      </Button>
    </div>
  )
}
