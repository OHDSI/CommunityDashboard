'use client'

import React, { Component, ReactNode } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
  resetKeys?: Array<string | number>
  resetOnPropsChange?: boolean
  isolate?: boolean
  componentName?: string
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    this.setState({
      error,
      errorInfo
    })

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  componentDidUpdate(prevProps: Props) {
    const { resetKeys, resetOnPropsChange } = this.props
    const { hasError } = this.state
    
    if (hasError) {
      // Reset on key changes
      if (resetKeys) {
        const hasResetKeyChanged = resetKeys.some(
          (key, idx) => key !== prevProps.resetKeys?.[idx]
        )
        if (hasResetKeyChanged) {
          this.resetError()
        }
      }
      
      // Reset when props change
      if (resetOnPropsChange && prevProps.children !== this.props.children) {
        this.resetError()
      }
    }
  }

  resetError = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    const { hasError, error, errorInfo } = this.state
    const { children, fallback, isolate, componentName } = this.props

    if (hasError) {
      // Custom fallback
      if (fallback) {
        return <>{fallback}</>
      }

      // Isolated error (minimal UI disruption)
      if (isolate) {
        return (
          <Alert variant="destructive" className="m-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Component Error</AlertTitle>
            <AlertDescription>
              {componentName ? `The ${componentName} component` : 'This component'} failed to load.
              <Button
                variant="link"
                size="sm"
                onClick={this.resetError}
                className="ml-2 p-0 h-auto"
              >
                Try again
              </Button>
            </AlertDescription>
          </Alert>
        )
      }

      // Full error display
      return (
        <Card className="m-4 border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertDescription>
                {error?.message || 'An unexpected error occurred'}
              </AlertDescription>
            </Alert>
            
            {process.env.NODE_ENV === 'development' && errorInfo && (
              <details className="space-y-2">
                <summary className="cursor-pointer text-sm font-medium">
                  Error Details (Development Only)
                </summary>
                <pre className="mt-2 p-3 bg-muted rounded-lg text-xs overflow-auto">
                  {error?.stack}
                </pre>
                <pre className="p-3 bg-muted rounded-lg text-xs overflow-auto">
                  Component Stack:
                  {errorInfo.componentStack}
                </pre>
              </details>
            )}
            
            <div className="flex gap-2">
              <Button onClick={this.resetError} variant="default" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" />
                Try Again
              </Button>
              <Button 
                onClick={() => window.location.reload()} 
                variant="outline" 
                size="sm"
              >
                Reload Page
              </Button>
            </div>
          </CardContent>
        </Card>
      )
    }

    return children
  }
}

// Convenience wrapper for isolated components
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<Props, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  )
  
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`
  
  return WrappedComponent
}

// Hook for error handling (requires React 18.2+)
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null)
  
  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])
  
  return setError
}