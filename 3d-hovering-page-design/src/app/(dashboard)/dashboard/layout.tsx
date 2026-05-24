import { cookies } from 'next/headers'
import { DashboardSidebar } from '@/components/dashboard/dashboard-sidebar'
import { DashboardHeader } from '@/components/dashboard/dashboard-header'
import { AuthProvider } from '@/providers/auth-provider'
import { getSessionFromCookies, parseUserCookie, USER_COOKIE } from '@/lib/auth'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  const session = getSessionFromCookies(cookieStore)
  const initialUser = session?.user ?? parseUserCookie(cookieStore.get(USER_COOKIE)?.value)

  return (
    <AuthProvider initialUser={initialUser}>
      <div className="flex h-screen bg-background">
        <DashboardSidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <DashboardHeader />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </div>
    </AuthProvider>
  )
}
