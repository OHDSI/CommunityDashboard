interface GraphQLResponse<T = any> {
  data?: T
  errors?: Array<{
    message: string
    path?: string[]
    extensions?: Record<string, any>
  }>
}

class APIClient {
  private baseURL: string
  private token: string | null = null

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL ?? ''
  }

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  getToken(): string | null {
    if (this.token) return this.token
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
    return this.token
  }

  private async request<T = any>(
    url: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {})
    }

    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${this.baseURL}${url}`, {
      ...options,
      headers
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        message: `HTTP ${response.status}: ${response.statusText}`
      }))
      throw new Error(error.message || error.detail || 'Request failed')
    }

    return response.json()
  }

  async graphql<T = any>(
    query: string,
    variables?: Record<string, any>
  ): Promise<GraphQLResponse<T>> {
    return this.request<GraphQLResponse<T>>('/graphql', {
      method: 'POST',
      body: JSON.stringify({ query, variables })
    })
  }

  async get<T = any>(url: string): Promise<T> {
    return this.request<T>(url)
  }

  async post<T = any>(url: string, data?: any): Promise<T> {
    return this.request<T>(url, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async put<T = any>(url: string, data?: any): Promise<T> {
    return this.request<T>(url, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async delete<T = any>(url: string): Promise<T> {
    return this.request<T>(url, {
      method: 'DELETE'
    })
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.graphql<{
      login: {
        token: string
        user: {
          id: string
          email: string
          role: string
        }
      }
    }>(`
      mutation Login($email: String!, $password: String!) {
        login(email: $email, password: $password) {
          token
          user {
            id
            email
            role
          }
        }
      }
    `, { email, password })

    if (response.data?.login) {
      this.setToken(response.data.login.token)
      return response.data.login
    }
    
    throw new Error(response.errors?.[0]?.message || 'Login failed')
  }

  async register(email: string, password: string, name?: string) {
    const response = await this.graphql<{
      register: {
        token: string
        user: {
          id: string
          email: string
          role: string
        }
      }
    }>(`
      mutation Register($email: String!, $password: String!, $name: String) {
        register(email: $email, password: $password, name: $name) {
          token
          user {
            id
            email
            role
          }
        }
      }
    `, { email, password, name })

    if (response.data?.register) {
      this.setToken(response.data.register.token)
      return response.data.register
    }
    
    throw new Error(response.errors?.[0]?.message || 'Registration failed')
  }

  async logout() {
    this.setToken(null)
  }

  // Review endpoints
  async approveContent(id: string, categories: string[]) {
    return this.graphql(`
      mutation ApproveContent($id: ID!, $categories: [String!]!) {
        approveContent(id: $id, categories: $categories)
      }
    `, { id, categories })
  }

  async rejectContent(id: string, reason: string) {
    return this.graphql(`
      mutation RejectContent($id: ID!, $reason: String!) {
        rejectContent(id: $id, reason: $reason)
      }
    `, { id, reason })
  }

  // User actions
  async bookmark(contentId: string) {
    return this.graphql(`
      mutation Bookmark($contentId: ID!) {
        bookmark(contentId: $contentId)
      }
    `, { contentId })
  }

  async saveSearch(query: string, name: string) {
    return this.graphql(`
      mutation SaveSearch($query: String!, $name: String!) {
        saveSearch(query: $query, name: $name)
      }
    `, { query, name })
  }
}

export const apiClient = new APIClient()