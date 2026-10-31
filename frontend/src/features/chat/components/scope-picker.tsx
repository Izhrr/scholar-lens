"use client"

import { BookOpen, ChevronDown } from "lucide-react"
import { useId } from "react"

import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import type { Paper } from "@/features/papers/types"
import { plural } from "@/lib/format"

import { SCOPE_MAX_PAPERS } from "../types"

interface ScopePickerProps {
  papers: Paper[]
  // null means every indexed paper, which also covers papers added later.
  value: string[] | null
  onChange: (value: string[] | null) => void
}

export function scopeLabel(papers: Paper[], value: string[] | null): string {
  if (value === null) return `All papers (${papers.length})`
  if (value.length === 1) return papers.find((p) => p.id === value[0])?.title ?? "1 paper"
  return `${value.length} of ${papers.length} papers`
}

export function ScopePicker({ papers, value, onChange }: ScopePickerProps) {
  const baseId = useId()
  const selected = new Set(value ?? [])

  function toggle(id: string, checked: boolean) {
    const next = new Set(selected)
    if (checked) next.add(id)
    else next.delete(id)
    // Unticking the last paper falls back to "all" instead of an empty, invalid scope.
    onChange(next.size === 0 || next.size === papers.length ? null : [...next])
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" className="h-11 max-w-full justify-start gap-3 px-3 text-left">
          <BookOpen className="text-primary" aria-hidden="true" />
          <span className="flex min-w-0 flex-col leading-tight">
            <span className="text-[11px] font-normal text-muted-foreground">Searching</span>
            <span className="truncate text-sm">{scopeLabel(papers, value)}</span>
          </span>
          <ChevronDown className="ml-auto text-muted-foreground" aria-hidden="true" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[min(26rem,calc(100vw-2rem))] p-0">
        <div className="px-4 pt-4 pb-3">
          <p className="font-semibold">Search scope</p>
          <p className="text-sm text-muted-foreground">Pick which papers answers can cite.</p>
        </div>
        <div className="px-2 pb-2">
          <label
            htmlFor={`${baseId}-all`}
            className="flex items-start gap-3 rounded-md px-2 py-2.5 hover:bg-muted"
          >
            <Checkbox
              id={`${baseId}-all`}
              checked={value === null}
              onCheckedChange={(checked) => checked && onChange(null)}
              className="mt-0.5"
            />
            <span className="flex flex-col">
              <span className="text-sm font-medium">All indexed papers</span>
              <span className="text-xs text-muted-foreground">
                {plural(papers.length, "paper")}, including ones you add later
              </span>
            </span>
          </label>
          <Separator className="my-1" />
          <ul className="max-h-72 overflow-y-auto">
            {papers.map((paper) => {
              const id = `${baseId}-${paper.id}`
              const checked = selected.has(paper.id)
              const limitReached = !checked && selected.size >= SCOPE_MAX_PAPERS
              return (
                <li key={paper.id}>
                  <label
                    htmlFor={id}
                    className="flex items-start gap-3 rounded-md px-2 py-2.5 hover:bg-muted"
                  >
                    <Checkbox
                      id={id}
                      checked={checked}
                      disabled={limitReached}
                      onCheckedChange={(state) => toggle(paper.id, state === true)}
                      className="mt-0.5"
                    />
                    <span className="flex min-w-0 flex-col">
                      <span className="line-clamp-2 font-serif text-sm font-medium">
                        {paper.title}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {plural(paper.page_count ?? 0, "page")}
                      </span>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          {selected.size >= SCOPE_MAX_PAPERS && (
            <p className="px-2 pt-2 text-xs text-muted-foreground">
              Up to {SCOPE_MAX_PAPERS} papers per scope. Choose “All indexed papers” for more.
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
