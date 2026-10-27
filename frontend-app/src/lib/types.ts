// Shared types mirroring the FastAPI `/api/v1` contract exactly.
// Keep this file in sync with the backend's Pydantic response models.

export interface AuthTokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface CurrentUser {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
}

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'won' | 'lost'

export interface Lead {
  id: string
  name: string
  email: string
  phone: string | null
  company: string | null
  status: LeadStatus
  source: string | null
  owner_id: string | null
  created_at: string
}

export type PostStatus = 'draft' | 'published' | 'archived'

export interface Post {
  id: string
  title: string
  slug: string
  status: PostStatus
  published_at: string | null
  author_email: string
}

export interface HealthResponse {
  status: 'ok'
}

export type NotificationMessage =
  | { type: 'session.init'; session_id: string }
  | { type: 'notification'; message: string }
