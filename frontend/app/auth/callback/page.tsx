'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'

export default function AuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState('Completing authentication...')
  
  useEffect(() => {
    const handleCallback = async () => {
      // Get parameters from URL
      const token = searchParams.get('token')
      const provider = searchParams.get('provider')
      const error = searchParams.get('error')
      const errorMessage = searchParams.get('message')
      
      // Handle error case
      if (error) {
        setStatus('error')
        setMessage(errorMessage || 'Authentication failed. Please try again.')
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push(`/login?error=${error}&message=${encodeURIComponent(errorMessage || '')}`)
        }, 3000)
        return
      }
      
      // Handle success case
      if (token) {
        try {
          // Store token in localStorage
          // In production, consider using httpOnly cookies for better security
          localStorage.setItem('token', token)
          
          // Store provider info for UI display
          if (provider) {
            localStorage.setItem('auth_provider', provider)
          }
          
          // Optional: Fetch user info with the new token
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (response.ok) {
            const userData = await response.json()
            localStorage.setItem('user', JSON.stringify(userData))
          }
          
          setStatus('success')
          setMessage('Authentication successful! Redirecting...')
          
          // Redirect to dashboard or return URL
          const returnUrl = localStorage.getItem('auth_return_url') || '/'
          localStorage.removeItem('auth_return_url')
          
          setTimeout(() => {
            router.push(returnUrl)
          }, 1500)
          
        } catch (error) {
          console.error('Error processing authentication:', error)
          setStatus('error')
          setMessage('Failed to complete authentication. Please try again.')
          
          setTimeout(() => {
            router.push('/login')
          }, 3000)
        }
      } else {
        // No token or error - something went wrong
        setStatus('error')
        setMessage('No authentication data received. Please try again.')
        
        setTimeout(() => {
          router.push('/login')
        }, 3000)
      }
    }
    
    handleCallback()
  }, [router, searchParams])
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-primary/5 via-accent/5 to-background">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          {/* Status Icon */}
          <div className="flex justify-center mb-4">
            {status === 'processing' && (
              <div className="relative">
                <Loader2 className="h-16 w-16 text-primary animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 bg-primary/20 rounded-full animate-ping" />
                </div>
              </div>
            )}
            {status === 'success' && (
              <div className="relative">
                <CheckCircle className="h-16 w-16 text-green-500" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 bg-green-500/20 rounded-full animate-ping" />
                </div>
              </div>
            )}
            {status === 'error' && (
              <XCircle className="h-16 w-16 text-red-500" />
            )}
          </div>
          
          {/* Status Message */}
          <h2 className="text-2xl font-bold mb-2">
            {status === 'processing' && 'Authenticating...'}
            {status === 'success' && 'Welcome to OHDSI!'}
            {status === 'error' && 'Authentication Failed'}
          </h2>
          
          <p className="text-muted-foreground">
            {message}
          </p>
          
          {/* Provider Info */}
          {status === 'success' && searchParams.get('provider') && (
            <div className="mt-4 inline-flex items-center px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">
              Authenticated with {searchParams.get('provider')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}