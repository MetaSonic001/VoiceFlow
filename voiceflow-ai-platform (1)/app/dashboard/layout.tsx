"use client"

import { DashboardSidebar } from "@/components/dashboard/sidebar"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen bg-background">
      <DashboardSidebar />
      <main className="flex-1 ml-64 overflow-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}