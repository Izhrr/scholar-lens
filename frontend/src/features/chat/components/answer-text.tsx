import { Fragment } from "react"

const CITATION = /\[(\d+)\]/g

interface AnswerTextProps {
  text: string
  messageId: string
  citationNumbers: Set<number>
}

/** Renders plain-text answers: blank lines split paragraphs, "- " lines become lists. */
export function AnswerText({ text, messageId, citationNumbers }: AnswerTextProps) {
  const blocks = text.split(/\n{2,}/).filter((block) => block.trim())
  return (
    <div className="flex flex-col gap-4 font-serif text-[17px] leading-relaxed">
      {blocks.map((block, index) => {
        const lines = block.split("\n").filter((line) => line.trim())
        if (lines.length > 0 && lines.every((line) => /^\s*[-*•]\s+/.test(line))) {
          return (
            <ul key={index} className="flex list-disc flex-col gap-1.5 pl-6">
              {lines.map((line, i) => (
                <li key={i}>
                  <Inline
                    text={line.replace(/^\s*[-*•]\s+/, "")}
                    messageId={messageId}
                    citationNumbers={citationNumbers}
                  />
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={index}>
            <Inline text={lines.join(" ")} messageId={messageId} citationNumbers={citationNumbers} />
          </p>
        )
      })}
    </div>
  )
}

function Inline({ text, messageId, citationNumbers }: AnswerTextProps) {
  const parts: React.ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    const number = Number(match[1])
    parts.push(text.slice(last, match.index))
    parts.push(
      citationNumbers.has(number) ? (
        <a
          key={`${match.index}-${number}`}
          href={`#${sourceAnchor(messageId, number)}`}
          aria-label={`Source ${number}`}
          className="mx-0.5 inline-grid min-w-5 place-items-center rounded bg-primary-soft px-1 align-text-top font-sans text-[11px] leading-5 font-semibold text-primary no-underline outline-none hover:bg-primary hover:text-primary-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {number}
        </a>
      ) : (
        <Fragment key={`${match.index}-${number}`}>{match[0]}</Fragment>
      )
    )
    last = (match.index ?? 0) + match[0].length
  }
  parts.push(text.slice(last))
  return <>{parts}</>
}

export function sourceAnchor(messageId: string, citationNumber: number): string {
  return `source-${messageId}-${citationNumber}`
}
