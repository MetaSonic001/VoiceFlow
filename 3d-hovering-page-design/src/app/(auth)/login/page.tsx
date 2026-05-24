import { Suspense } from 'react'
import LoginPage from './login-client'

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-stone-100" />}>
      <LoginPage />
    </Suspense>
  )
}
