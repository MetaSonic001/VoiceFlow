"use client"

import { createContext, useContext, type ReactNode } from "react"
import { apiClient } from "@/lib/api-client"
import { ErrorBoundary } from "@/components/ui/error-boundary"

const ApiContext = createContext(apiClient)

export function useApiClient() {
  return useContext(ApiContext)
}

interface ApiProviderProps {
  children: ReactNode
}

export function ApiProvider({ children }: ApiProviderProps) {
  return (
    <ErrorBoundary>
      <ApiContext.Provider value={apiClient}>{children}</ApiContext.Provider>
    </ErrorBoundary>
  )
}
