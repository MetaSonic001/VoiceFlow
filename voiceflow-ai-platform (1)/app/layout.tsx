import type React from "react"
import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import "./globals.css"

export const metadata: Metadata = {
  title: "VoiceFlow AI - Create Intelligent Voice & Chat Agents",
  description:
    "Transform your business with AI agents that handle customer support, sales calls, and internal workflows. No coding required - setup in minutes.",
  generator: "VoiceFlow AI",
  keywords: "AI agents, voice AI, chatbots, customer support, automation, India",
  authors: [{ name: "VoiceFlow AI Team" }],
  openGraph: {
    title: "VoiceFlow AI - Create Intelligent Voice & Chat Agents",
    description: "Transform your business with AI agents in minutes. No coding required.",
    type: "website",
    locale: "en_IN",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`font-sans ${GeistSans.variable} ${GeistMono.variable} antialiased`}>{children}</body>
    </html>
  )
}
