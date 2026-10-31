import type { Metadata } from "next"
import { IBM_Plex_Sans, Source_Serif_4 } from "next/font/google"

import { AppShell } from "@/components/layout/app-shell"

import { Providers } from "./providers"
import "./globals.css"

// Plex for interface text; Source Serif for paper titles and answers, the way papers are set.
const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
})

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "600"],
})

export const metadata: Metadata = {
  title: { default: "ScholarLens", template: "%s · ScholarLens" },
  description: "Ask questions across your academic PDFs and get answers cited to the page.",
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plexSans.variable} ${sourceSerif.variable} antialiased`}
    >
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  )
}
