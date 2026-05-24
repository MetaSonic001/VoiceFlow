'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { registerSchema, type RegisterFormValues } from '@/schemas/auth'
import { signupClient } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function RegisterPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (values: RegisterFormValues) => {
    setError(null)
    try {
      await signupClient(values.email, values.password)
      router.push('/dashboard')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    }
  }

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 bg-stone-900 p-12 items-center justify-center">
        <div className="max-w-md text-stone-100">
          <Link href="/" className="flex items-center gap-2 mb-8">
            <div className="w-10 h-10 rounded-lg bg-stone-100/10 flex items-center justify-center">
              <span className="font-serif font-bold text-lg">V</span>
            </div>
            <span className="text-2xl font-serif font-bold">VoiceFlow</span>
          </Link>
          <h2 className="text-3xl font-serif font-bold mb-4">
            Start building voice agents in minutes
          </h2>
          <p className="font-serif text-stone-300 leading-relaxed">
            Join teams automating customer support, sales outreach, and appointment scheduling with AI voice agents.
          </p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg bg-stone-900 flex items-center justify-center">
                <span className="font-serif font-bold text-stone-100 text-sm">V</span>
              </div>
              <span className="text-xl font-serif font-bold text-stone-900">VoiceFlow</span>
            </Link>
          </div>

          <h1 className="text-2xl font-serif font-bold text-stone-900 mb-1">Create your account</h1>
          <p className="font-mono text-sm text-stone-600 mb-8">Get started with VoiceFlow for free</p>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm font-mono">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <Label htmlFor="email" className="font-mono text-xs uppercase tracking-wider text-stone-700">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                className="mt-2 bg-white border-stone-300 font-mono"
                {...register('email')}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600 font-mono">{errors.email.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="password" className="font-mono text-xs uppercase tracking-wider text-stone-700">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                className="mt-2 bg-white border-stone-300 font-mono"
                {...register('password')}
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 font-mono">{errors.password.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="passwordConfirm" className="font-mono text-xs uppercase tracking-wider text-stone-700">
                Confirm Password
              </Label>
              <Input
                id="passwordConfirm"
                type="password"
                autoComplete="new-password"
                className="mt-2 bg-white border-stone-300 font-mono"
                {...register('passwordConfirm')}
              />
              {errors.passwordConfirm && (
                <p className="mt-1 text-sm text-red-600 font-mono">{errors.passwordConfirm.message}</p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-stone-900 hover:bg-stone-800 text-white font-serif text-base py-6"
            >
              {isSubmitting ? 'Creating account...' : 'Create Account'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm font-mono text-stone-600">
            Already have an account?{' '}
            <Link href="/login" className="text-stone-900 font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
