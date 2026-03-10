import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { MainNav } from '@/components/layout/main-nav'

export const metadata: Metadata = {
  title: 'OHDSI Community Intelligence Platform',
  description: 'Discover research, tools, and knowledge from the OHDSI community',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            <MainNav />
            <main className="flex-1">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  )
}