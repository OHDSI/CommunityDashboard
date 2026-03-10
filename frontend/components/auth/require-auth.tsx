'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

interface RequireAuthProps {
  children: React.ReactNode
  role?: 'reviewer' | 'admin'
}

export function RequireAuth({ children, role = 'reviewer' }: RequireAuthProps) {
  const { isAuthenticated, isReviewer, isAdmin, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (loading) return

    if (!isAuthenticated) {
      // Save where the user was trying to go
      localStorage.setItem('auth_return_url', window.location.pathname)
      router.push('/login')
      return
    }

    if (role === 'admin' && !isAdmin) {
      router.push('/')
      return
    }

    if (role === 'reviewer' && !isReviewer) {
      router.push('/')
      return
    }
  }, [isAuthenticated, isReviewer, isAdmin, loading, role, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!isAuthenticated) return null
  if (role === 'admin' && !isAdmin) return null
  if (role === 'reviewer' && !isReviewer) return null

  return <>{children}</>
}
