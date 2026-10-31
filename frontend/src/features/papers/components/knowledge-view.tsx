"use client"

import { FileUp, SearchX, ServerCrash } from "lucide-react"
import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { MAX_UPLOAD_MB } from "@/lib/env"
import { plural } from "@/lib/format"

import { usePapers } from "../queries"
import type { Paper, PaperStatus } from "../types"
import { DeletePaperDialog } from "./delete-paper-dialog"
import { PaperDetailsSheet } from "./paper-details-sheet"
import { PapersTable } from "./papers-table"
import { UploadButton } from "./upload-button"

const PAGE_SIZE = 10

type StatusFilter = "all" | "indexed" | "in-progress" | "failed"

const FILTERS: Record<StatusFilter, { label: string; matches: (status: PaperStatus) => boolean }> = {
  all: { label: "All statuses", matches: () => true },
  indexed: { label: "Indexed", matches: (s) => s === "indexed" },
  "in-progress": {
    label: "In progress",
    matches: (s) => s === "queued" || s === "processing" || s === "deleting",
  },
  failed: { label: "Failed", matches: (s) => s === "failed" },
}

export function KnowledgeView() {
  const { data: papers, isLoading, isError, error, refetch, isRefetching } = usePapers()
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [page, setPage] = useState(0)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<Paper | null>(null)

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (papers ?? []).filter(
      (paper) =>
        FILTERS[statusFilter].matches(paper.status) &&
        (!term ||
          paper.title.toLowerCase().includes(term) ||
          paper.original_filename.toLowerCase().includes(term))
    )
  }, [papers, search, statusFilter])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount - 1)
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)
  // Look the selection up live so the details sheet follows status polling.
  const selected = papers?.find((paper) => paper.id === selectedId) ?? null

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-8 lg:py-12">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            Your research library
          </h1>
          <p className="mt-2 max-w-xl text-muted-foreground">
            Every chat answer is grounded in the papers indexed here.
          </p>
          {papers && papers.length > 0 && <LibrarySummary papers={papers} />}
        </div>
        <UploadButton size="lg" className="h-11 px-4 sm:self-auto" />
      </header>

      <section
        aria-labelledby="papers-heading"
        className="overflow-hidden rounded-xl border bg-card"
      >
        <div className="flex flex-col gap-4 border-b p-4 sm:p-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 id="papers-heading" className="text-base font-semibold">
              Papers
            </h2>
            <p className="text-sm text-muted-foreground">
              {papers ? plural(papers.length, "paper") : "Loading"} in this workspace
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="paper-search" className="text-xs text-muted-foreground">
                Search
              </Label>
              <Input
                id="paper-search"
                type="search"
                placeholder="Title or filename"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(0)
                }}
                className="h-10 sm:w-64"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="paper-status" className="text-xs text-muted-foreground">
                Status
              </Label>
              <Select
                value={statusFilter}
                onValueChange={(value) => {
                  setStatusFilter(value as StatusFilter)
                  setPage(0)
                }}
              >
                <SelectTrigger id="paper-status" className="h-10! w-full sm:w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(FILTERS).map(([value, filter]) => (
                    <SelectItem key={value} value={value}>
                      {filter.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {isLoading ? (
          <LoadingRows />
        ) : isError ? (
          <StateMessage
            icon={<ServerCrash aria-hidden="true" />}
            title="The library could not load"
            body={error.message}
            action={
              <Button variant="outline" onClick={() => refetch()} disabled={isRefetching}>
                {isRefetching ? "Retrying…" : "Retry"}
              </Button>
            }
          />
        ) : papers?.length === 0 ? (
          <StateMessage
            icon={<FileUp aria-hidden="true" />}
            title="No papers yet"
            body={`Add a text-based PDF up to ${MAX_UPLOAD_MB} MB. ScholarLens reads it page by page, indexes it, and it becomes searchable in Research chat.`}
            action={<UploadButton>Add your first paper</UploadButton>}
          />
        ) : filtered.length === 0 ? (
          <StateMessage
            icon={<SearchX aria-hidden="true" />}
            title="No papers match"
            body="Nothing matches this search and status. Clear the filters to see every paper."
            action={
              <Button
                variant="outline"
                onClick={() => {
                  setSearch("")
                  setStatusFilter("all")
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <>
            <PapersTable
              papers={visible}
              onOpen={(paper) => setSelectedId(paper.id)}
              onDelete={setToDelete}
            />
            {pageCount > 1 && (
              <nav
                aria-label="Papers pages"
                className="flex items-center justify-between border-t px-4 py-3 text-sm text-muted-foreground sm:px-5"
              >
                <span>
                  {currentPage * PAGE_SIZE + 1}–{currentPage * PAGE_SIZE + visible.length} of{" "}
                  {filtered.length}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9"
                    disabled={currentPage === 0}
                    onClick={() => setPage(currentPage - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9"
                    disabled={currentPage >= pageCount - 1}
                    onClick={() => setPage(currentPage + 1)}
                  >
                    Next
                  </Button>
                </div>
              </nav>
            )}
          </>
        )}
      </section>

      <PaperDetailsSheet
        paper={selected}
        onOpenChange={(open) => !open && setSelectedId(null)}
        onDelete={setToDelete}
      />
      <DeletePaperDialog
        paper={toDelete}
        onOpenChange={(open) => !open && setToDelete(null)}
        onDeleted={() => setSelectedId(null)}
      />
    </div>
  )
}

function LibrarySummary({ papers }: { papers: Paper[] }) {
  const indexed = papers.filter((paper) => paper.status === "indexed")
  const pages = indexed.reduce((sum, paper) => sum + (paper.page_count ?? 0), 0)
  const passages = indexed.reduce((sum, paper) => sum + paper.chunk_count, 0)
  return (
    <p className="mt-4 text-sm">
      <span className="font-semibold">{plural(indexed.length, "paper")}</span>
      <span className="text-muted-foreground"> searchable · </span>
      <span className="font-semibold">{plural(pages, "page")}</span>
      <span className="text-muted-foreground"> · </span>
      <span className="font-semibold">{plural(passages, "passage")}</span>
      <span className="text-muted-foreground"> in the index</span>
    </p>
  )
}

function LoadingRows() {
  return (
    <div className="flex flex-col gap-4 p-5" aria-busy="true" aria-label="Loading papers">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="size-9 rounded-md" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-2/5" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      ))}
    </div>
  )
}

function StateMessage({
  icon,
  title,
  body,
  action,
}: {
  icon: React.ReactNode
  title: string
  body: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <span className="grid size-11 place-items-center rounded-lg bg-muted text-muted-foreground [&_svg]:size-5">
        {icon}
      </span>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
