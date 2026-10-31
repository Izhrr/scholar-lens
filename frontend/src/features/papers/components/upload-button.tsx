"use client"

import { Plus } from "lucide-react"
import { useRef } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api-client"
import { MAX_UPLOAD_MB } from "@/lib/env"

import { useUploadPaper } from "../queries"

type UploadButtonProps = Omit<React.ComponentProps<typeof Button>, "onClick">

export function UploadButton({ children = "Add paper", ...props }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useUploadPaper()

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return
    // Sequential uploads keep the single backend worker from embedding several PDFs at once.
    for (const file of Array.from(files)) {
      const problem = validate(file)
      if (problem) {
        toast.error(`${file.name}: ${problem}`)
        continue
      }
      const id = toast.loading(`Uploading ${file.name}`)
      try {
        await upload.mutateAsync(file)
        toast.success(`${file.name} uploaded. Indexing has started.`, { id })
      } catch (error) {
        const message = error instanceof ApiError ? error.message : "Upload failed."
        toast.error(`${file.name}: ${message}`, { id })
      }
    }
    if (inputRef.current) inputRef.current.value = ""
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => handleFiles(event.target.files)}
      />
      <Button
        {...props}
        disabled={upload.isPending || props.disabled}
        onClick={() => inputRef.current?.click()}
      >
        <Plus aria-hidden="true" />
        {upload.isPending ? "Uploading…" : children}
      </Button>
    </>
  )
}

function validate(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
  if (!isPdf) return "only PDF files are accepted."
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `larger than the ${MAX_UPLOAD_MB} MB limit.`
  if (file.size === 0) return "the file is empty."
  return null
}
