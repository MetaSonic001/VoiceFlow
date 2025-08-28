"use client"

import { useState, useEffect } from "react"
import { apiClient, ApiError } from "@/lib/api-client"

// Generic hook for API calls
export function useApi<T>(apiCall: () => Promise<T>, dependencies: any[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  const refetch = async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await apiCall()
      setData(result)
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError("Unknown error", 0))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refetch()
  }, dependencies)

  return { data, loading, error, refetch }
}

// Specific hooks for common API calls
export function useAgents() {
  return useApi(() => apiClient.getAgents())
}

export function useAgent(agentId: string) {
  return useApi(() => apiClient.getAgent(agentId), [agentId])
}

export function useAnalyticsOverview(timeRange: string, agentId?: string) {
  return useApi(() => apiClient.getAnalyticsOverview(timeRange, agentId), [timeRange, agentId])
}

export function useMetricsData(timeRange: string, agentId?: string) {
  return useApi(() => apiClient.getMetricsData(timeRange, agentId), [timeRange, agentId])
}

export function usePerformanceData(timeRange: string, agentId?: string) {
  return useApi(() => apiClient.getPerformanceData(timeRange, agentId), [timeRange, agentId])
}

export function useAgentComparison() {
  return useApi(() => apiClient.getAgentComparison())
}

export function useRealtimeMetrics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const result = await apiClient.getRealtimeMetrics()
        setData(result)
        setError(null)
      } catch (err) {
        setError(err instanceof ApiError ? err : new ApiError("Unknown error", 0))
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchMetrics()

    // Set up polling every 5 seconds
    const interval = setInterval(fetchMetrics, 5000)

    return () => clearInterval(interval)
  }, [])

  return { data, loading, error }
}

export function useCallLogs(params: any = {}) {
  return useApi(() => apiClient.getCallLogs(params), [JSON.stringify(params)])
}

export function useCallDetails(callId: string) {
  return useApi(() => apiClient.getCallDetails(callId), [callId])
}

// Mutation hooks for actions
export function useApiMutation<T, P>(apiCall: (params: P) => Promise<T>) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const mutate = async (params: P): Promise<T | null> => {
    try {
      setLoading(true)
      setError(null)
      const result = await apiCall(params)
      return result
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError("Unknown error", 0)
      setError(apiError)
      throw apiError
    } finally {
      setLoading(false)
    }
  }

  return { mutate, loading, error }
}

// Auth hooks
export function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem("auth_token")
        if (token) {
          const userData = await apiClient.getCurrentUser()
          setUser(userData)
        }
      } catch (error) {
        localStorage.removeItem("auth_token")
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const response = await apiClient.login(email, password)
    localStorage.setItem("auth_token", response.token)
    setUser(response.user)
    return response
  }

  const signup = async (email: string, password: string, companyName: string) => {
    const response = await apiClient.signup(email, password, companyName)
    localStorage.setItem("auth_token", response.token)
    setUser(response.user)
    return response
  }

  const logout = () => {
    localStorage.removeItem("auth_token")
    setUser(null)
  }

  return { user, loading, login, signup, logout }
}
