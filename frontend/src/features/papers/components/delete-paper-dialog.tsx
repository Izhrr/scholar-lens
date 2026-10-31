"use client"

import { toast } from "sonner"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { ApiError } from "@/lib/api-client"

import { useDeletePaper } from "../queries"
import type { Paper } from "../types"

interface DeletePaperDialogProps {
  paper: Paper | null
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
}

export function DeletePaperDialog({ paper, onOpenChange, onDeleted }: DeletePaperDialogProps) {
  const remove = useDeletePaper()

  async function handleDelete() {
    if (!paper) return
    try {
      await remove.mutateAsync(paper.id)
      toast.success(`Deleted “${paper.title}”.`)
      onDeleted?.()
      onOpenChange(false)
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Delete failed. Try again.")
    }
  }

  return (
    <AlertDialog open={paper !== null} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this paper?</AlertDialogTitle>
          <AlertDialogDescription>
            “{paper?.title}” will be removed with its stored PDF and search index, so chat stops
            using it right away. Past answers keep their quoted excerpts but lose the link to the
            PDF. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={remove.isPending}>Keep paper</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={remove.isPending}
            onClick={(event) => {
              // Keep the dialog open until the request settles.
              event.preventDefault()
              void handleDelete()
            }}
          >
            {remove.isPending ? "Deleting…" : "Delete paper"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
