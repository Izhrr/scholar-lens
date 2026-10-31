import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-start gap-3 px-6 py-20">
      <h1 className="font-serif text-3xl font-semibold">Page not found</h1>
      <p className="text-muted-foreground">ScholarLens has two pages: Knowledge and Research chat.</p>
      <Button asChild className="mt-2 h-11">
        <Link href="/knowledge">Go to your library</Link>
      </Button>
    </div>
  )
}
