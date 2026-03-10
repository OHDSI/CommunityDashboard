'use client'

import { useState, useRef, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  onFocus?: () => void
  onBlur?: () => void
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Search articles, videos, repositories...",
  className,
  onFocus,
  onBlur
}: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClear = () => {
    onChange('')
    inputRef.current?.focus()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Trigger search
    inputRef.current?.blur()
  }

  return (
    <form onSubmit={handleSubmit} className={cn("relative w-full", className)}>
      <div className={cn(
        "relative flex items-center rounded-lg border bg-background transition-all",
        isFocused ? "border-primary shadow-sm" : "border-input"
      )}>
        <Search className="absolute left-3 h-5 w-5 text-muted-foreground pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => {
            setIsFocused(true)
            onFocus?.()
          }}
          onBlur={() => {
            setIsFocused(false)
            onBlur?.()
          }}
          placeholder={placeholder}
          className="h-12 w-full bg-transparent pl-10 pr-10 text-base outline-none placeholder:text-muted-foreground"
        />
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleClear}
            className="absolute right-1 h-9 w-9"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      
      {/* Search suggestions could go here */}
      {isFocused && value.length > 2 && (
        <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border bg-background shadow-lg z-50">
          {/* Suggestions list */}
        </div>
      )}
    </form>
  )
}