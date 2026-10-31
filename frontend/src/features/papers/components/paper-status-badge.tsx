import { AlertCircle, Check, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

import type { PaperStatus } from "../types"

const STATUS_META: Record<PaperStatus, { label: string; className: string }> = {
  queued: { label: "Queued", className: "bg-warning-soft text-warning" },
  processing: { label: "Indexing", className: "bg-warning-soft text-warning" },
  indexed: { label: "Indexed", className: "bg-success-soft text-success" },
  failed: { label: "Failed", className: "bg-destructive/10 text-destructive" },
  deleting: { label: "Deleting", className: "bg-muted text-muted-foreground" },
}

export function PaperStatusBadge({ status }: { status: PaperStatus }) {
  const meta = STATUS_META[status]
  const busy = status === "queued" || status === "processing" || status === "deleting"
  return (
    <Badge className={cn("rounded-md font-medium", meta.className)}>
      {busy && <Loader2 className="animate-spin" aria-hidden="true" />}
      {status === "indexed" && <Check aria-hidden="true" />}
      {status === "failed" && <AlertCircle aria-hidden="true" />}
      {meta.label}
    </Badge>
  )
}
