'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@apollo/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { RequireAuth } from '@/components/auth/require-auth'
import { LIST_USERS } from '@/lib/graphql/queries'
import { CREATE_USER, UPDATE_USER_ROLE, DEACTIVATE_USER } from '@/lib/graphql/mutations'
import { Loader2, Plus, ShieldCheck, UserX } from 'lucide-react'

interface UserData {
  id: string
  email: string
  fullName: string | null
  role: string
  isActive: boolean
  createdAt: string
  lastLogin: string | null
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-red-100 text-red-800',
  reviewer: 'bg-blue-100 text-blue-800',
  contributor: 'bg-green-100 text-green-800',
  explorer: 'bg-gray-100 text-gray-800',
}

export default function AdminUsersPage() {
  const { toast } = useToast()
  const [showAddForm, setShowAddForm] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newFullName, setNewFullName] = useState('')
  const [newRole, setNewRole] = useState('reviewer')

  const { data, loading, refetch } = useQuery(LIST_USERS, {
    fetchPolicy: 'network-only',
  })

  const [createUser, { loading: creating }] = useMutation(CREATE_USER, {
    onCompleted: () => {
      toast({ title: 'User Created', description: `${newEmail} has been added.` })
      setNewEmail('')
      setNewPassword('')
      setNewFullName('')
      setNewRole('reviewer')
      setShowAddForm(false)
      refetch()
    },
    onError: (err) => {
      toast({ title: 'Error', description: err.message, variant: 'destructive' })
    },
  })

  const [updateRole] = useMutation(UPDATE_USER_ROLE, {
    onCompleted: () => {
      toast({ title: 'Role Updated' })
      refetch()
    },
    onError: (err) => {
      toast({ title: 'Error', description: err.message, variant: 'destructive' })
    },
  })

  const [deactivateUser] = useMutation(DEACTIVATE_USER, {
    onCompleted: () => {
      toast({ title: 'User Deactivated' })
      refetch()
    },
    onError: (err) => {
      toast({ title: 'Error', description: err.message, variant: 'destructive' })
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEmail || !newPassword || !newFullName) {
      toast({ title: 'Missing fields', description: 'All fields are required.', variant: 'destructive' })
      return
    }
    createUser({
      variables: { email: newEmail, password: newPassword, fullName: newFullName, role: newRole },
    })
  }

  const users: UserData[] = data?.listUsers ?? []

  return (
    <RequireAuth role="admin">
      <div className="container mx-auto py-8 max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <ShieldCheck className="h-8 w-8 text-primary" />
              User Management
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage reviewer and admin accounts
            </p>
          </div>
          <Button onClick={() => setShowAddForm(!showAddForm)}>
            <Plus className="h-4 w-4 mr-2" />
            Add User
          </Button>
        </div>

        {showAddForm && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Add New User</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new-email">Email</Label>
                  <Input
                    id="new-email"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="user@ohdsi.org"
                    disabled={creating}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-name">Full Name</Label>
                  <Input
                    id="new-name"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    placeholder="Jane Doe"
                    disabled={creating}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-password">Password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Strong password"
                    disabled={creating}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-role">Role</Label>
                  <Select value={newRole} onValueChange={setNewRole} disabled={creating}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="reviewer">Reviewer</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="explorer">Explorer</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="md:col-span-2 flex gap-2">
                  <Button type="submit" disabled={creating}>
                    {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Create User
                  </Button>
                  <Button type="button" variant="outline" onClick={() => setShowAddForm(false)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : users.length === 0 ? (
              <p className="text-muted-foreground text-center py-12">No users found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-4 text-sm font-medium text-muted-foreground">Email</th>
                      <th className="text-left p-4 text-sm font-medium text-muted-foreground">Name</th>
                      <th className="text-left p-4 text-sm font-medium text-muted-foreground">Role</th>
                      <th className="text-left p-4 text-sm font-medium text-muted-foreground">Status</th>
                      <th className="text-right p-4 text-sm font-medium text-muted-foreground">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b last:border-b-0 hover:bg-muted/30">
                        <td className="p-4 text-sm">{u.email}</td>
                        <td className="p-4 text-sm text-muted-foreground">{u.fullName ?? '-'}</td>
                        <td className="p-4">
                          <Select
                            value={u.role}
                            onValueChange={(val) =>
                              updateRole({ variables: { userId: u.id, role: val } })
                            }
                          >
                            <SelectTrigger className="w-[130px] h-8">
                              <Badge className={`${ROLE_COLORS[u.role] ?? 'bg-gray-100 text-gray-800'} text-xs`}>
                                {u.role}
                              </Badge>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="reviewer">Reviewer</SelectItem>
                              <SelectItem value="explorer">Explorer</SelectItem>
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="p-4">
                          <Badge variant={u.isActive ? 'default' : 'secondary'} className="text-xs">
                            {u.isActive ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                        <td className="p-4 text-right">
                          {u.isActive && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              onClick={() =>
                                deactivateUser({ variables: { userId: u.id } })
                              }
                            >
                              <UserX className="h-4 w-4 mr-1" />
                              Deactivate
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  )
}
