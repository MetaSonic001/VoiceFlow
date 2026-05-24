'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useRouter } from 'next/navigation'
import type { AuthUser } from '@/types/auth'
import { getMeClient, logoutClient } from '@/services/api'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  refresh: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({
  children,
  initialUser = null,
}: {
  children: ReactNode
  initialUser?: AuthUser | null
}) {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(initialUser)
  const [loading, setLoading] = useState(!initialUser)

  const refresh = useCallback(async () => {
    try {
      const data = await getMeClient()
      setUser(data.user)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!initialUser) {
      void refresh()
    }
  }, [initialUser, refresh])

  const signOut = useCallback(async () => {
    await logoutClient()
    setUser(null)
    router.push('/login')
    router.refresh()
  }, [router])

  const value = useMemo(
    () => ({ user, loading, refresh, signOut }),
    [user, loading, refresh, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
