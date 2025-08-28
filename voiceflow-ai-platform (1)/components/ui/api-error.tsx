"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"
import type { ApiError } from "@/lib/api-client"

interface ApiErrorComponentProps {
  error: ApiError
  onRetry?: () => void
  title?: string
}

export function ApiErrorComponent({ error, onRetry, title = "Error Loading Data" }: ApiErrorComponentProps) {
  const getErrorMessage = (error: ApiError) => {
    if (error.status === 0) {
      return "Unable to connect to the server. Please check your internet connection."
    }
    if (error.status === 401) {
      return "You are not authorized to access this resource. Please log in again."
    }
    if (error.status === 403) {
      return "You do not have permission to access this resource."
    }
    if (error.status === 404) {
      return "The requested resource was not found."
    }
    if (error.status >= 500) {
      return "A server error occurred. Please try again later."
    }
    return error.message || "An unexpected error occurred."
  }

  return (
    <Card className="max-w-md mx-auto">
      <CardHeader className="text-center">
        <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
        <CardTitle>{title}</CardTitle>
        <CardDescription>{getErrorMessage(error)}</CardDescription>
      </CardHeader>
      {onRetry && (
        <CardContent className="text-center">
          <Button onClick={onRetry} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      )}
    </Card>
  )
}
