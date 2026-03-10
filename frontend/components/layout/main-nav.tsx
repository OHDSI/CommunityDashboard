'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { OHDSILogo } from '@/components/ui/ohdsi-logo'
import { useAuth } from '@/lib/auth-context'
import {
  Search,
  Users,
  ShieldCheck,
  BarChart3,
  LogOut
} from 'lucide-react'

export function MainNav() {
  const pathname = usePathname()
  const { isAuthenticated, isAdmin, user, logout } = useAuth()

  const navItems = [
    {
      href: '/search',
      label: 'Search',
      icon: Search,
      show: true,
    },
    {
      href: '/review',
      label: 'Review',
      icon: Users,
      show: true,
    },
    {
      href: '/analytics',
      label: 'Analytics',
      icon: BarChart3,
      show: isAuthenticated,
    },
    {
      href: '/admin/users',
      label: 'Admin',
      icon: ShieldCheck,
      show: isAdmin,
    },
  ]

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-white/95 backdrop-blur-md supports-[backdrop-filter]:bg-white/90 shadow-sm">
      <div className="container flex h-16 items-center px-4 md:px-8">
        <div className="flex items-center gap-2 md:gap-4">
          <Link href="/" className="flex items-center space-x-2 group">
            <OHDSILogo
              width={140}
              height={45}
              className="group-hover:scale-105 transition-transform"
            />
            <div className="hidden md:flex flex-col border-l-2 border-accent/30 pl-3 ml-2">
              <span className="text-xs font-medium text-muted-foreground leading-tight">
                Community
              </span>
              <span className="font-bold text-sm leading-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                Intelligence Platform
              </span>
            </div>
          </Link>
          <nav className="flex items-center space-x-1">
            {navItems
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "group relative flex items-center space-x-2 px-2 md:px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                      isActive
                        ? "text-primary bg-gradient-to-r from-primary/10 to-accent/10"
                        : "text-muted-foreground hover:text-primary hover:bg-gradient-to-r hover:from-primary/5 hover:to-accent/5"
                    )}
                  >
                    <Icon className={cn(
                      "h-4 w-4 transition-all duration-200",
                      isActive
                        ? "text-primary"
                        : "text-muted-foreground group-hover:text-primary group-hover:scale-110"
                    )} />
                    <span className="hidden sm:inline">{item.label}</span>
                    {isActive && (
                      <div className="absolute bottom-0 left-2 md:left-3 right-2 md:right-3 h-0.5 bg-gradient-to-r from-primary to-accent rounded-full" />
                    )}
                  </Link>
                )
              })}
          </nav>
        </div>
        <div className="ml-auto flex items-center space-x-3">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2">
              <span className="hidden md:inline text-sm text-muted-foreground">
                {user.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-9 rounded-lg hover:bg-muted text-muted-foreground"
              >
                <LogOut className="h-4 w-4 mr-1" />
                <span className="hidden sm:inline">Sign Out</span>
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  )
}
