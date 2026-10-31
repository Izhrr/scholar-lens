"use client"

import { SendHorizontal } from "lucide-react"
import { useId } from "react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import { QUESTION_MAX_LENGTH } from "../types"

interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled: boolean
  busy: boolean
}

export function Composer({ value, onChange, onSubmit, disabled, busy }: ComposerProps) {
  const id = useId()
  const trimmed = value.trim()
  const tooLong = value.length > QUESTION_MAX_LENGTH
  const canSend = !disabled && !busy && trimmed.length > 0 && !tooLong

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (canSend) onSubmit()
      }}
      className="rounded-xl border bg-card p-2 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/30"
    >
      <label htmlFor={id} className="block px-2 pt-1 text-xs font-medium text-muted-foreground">
        Your question
      </label>
      <Textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          // Enter sends, Shift+Enter adds a line; ignore Enter while an IME is composing.
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            if (canSend) onSubmit()
          }
        }}
        disabled={disabled}
        placeholder={disabled ? "Index a paper to start asking" : "Ask about your papers…"}
        rows={2}
        className="max-h-48 min-h-14 resize-none border-0 bg-transparent px-2 text-base shadow-none focus-visible:ring-0 dark:bg-transparent"
      />
      <div className="flex items-center justify-between gap-3 px-2 pt-1">
        <span
          className={cn("text-xs text-muted-foreground", tooLong && "font-medium text-destructive")}
          aria-live="polite"
        >
          {tooLong
            ? `${value.length - QUESTION_MAX_LENGTH} characters over the limit`
            : "Enter to send · Shift+Enter for a new line"}
        </span>
        <Button type="submit" size="icon" className="size-10" disabled={!canSend} aria-label="Send question">
          <SendHorizontal aria-hidden="true" />
        </Button>
      </div>
    </form>
  )
}
