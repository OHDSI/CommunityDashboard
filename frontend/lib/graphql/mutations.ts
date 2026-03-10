import { gql } from '@apollo/client'

export const LOGIN_USER = gql`
  mutation LoginUser($email: String!, $password: String!) {
    login(email: $email, password: $password) {
      accessToken
      user {
        id
        email
        fullName
        role
        organization
      }
    }
  }
`

export const REGISTER_USER = gql`
  mutation RegisterUser($email: String!, $password: String!, $fullName: String!, $organization: String) {
    register(email: $email, password: $password, fullName: $fullName, organization: $organization) {
      accessToken
      user {
        id
        email
        fullName
        role
        organization
      }
    }
  }
`

export const APPROVE_CONTENT = gql`
  mutation ApproveContent($id: ID!, $categories: [String!]) {
    approveContent(id: $id, categories: $categories)
  }
`

export const REJECT_CONTENT = gql`
  mutation RejectContent($id: ID!, $reason: String!) {
    rejectContent(id: $id, reason: $reason)
  }
`

export const BOOKMARK_CONTENT = gql`
  mutation BookmarkContent($contentId: ID!) {
    bookmark(contentId: $contentId)
  }
`

export const SAVE_SEARCH = gql`
  mutation SaveSearch($query: String!, $name: String) {
    saveSearch(query: $query, name: $name)
  }
`

export const CREATE_USER = gql`
  mutation CreateUser($email: String!, $password: String!, $fullName: String!, $role: String!) {
    createUser(email: $email, password: $password, fullName: $fullName, role: $role) {
      id
      email
      fullName
      role
      isActive
    }
  }
`

export const UPDATE_USER_ROLE = gql`
  mutation UpdateUserRole($userId: String!, $role: String!) {
    updateUserRole(userId: $userId, role: $role)
  }
`

export const DEACTIVATE_USER = gql`
  mutation DeactivateUser($userId: String!) {
    deactivateUser(userId: $userId)
  }
`