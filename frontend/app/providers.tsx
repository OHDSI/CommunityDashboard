'use client'

import { ApolloProvider } from '@apollo/client'
import client from '@/lib/apollo-client'
import { AuthProvider } from '@/lib/auth-context'
import { Toaster } from '@/components/ui/toaster'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ApolloProvider client={client}>
      <AuthProvider>
        {children}
        <Toaster />
      </AuthProvider>
    </ApolloProvider>
  )
}
