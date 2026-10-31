import Link from "next/link"

// Text-only brand mark until a real logo exists.
export function Wordmark() {
  return (
    <Link
      href="/knowledge"
      className="rounded-md font-serif text-xl font-semibold tracking-tight outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      Scholar<span className="text-primary">Lens</span>
    </Link>
  )
}
