export interface AuthUser {
  id: string
  email: string
  tenantId: string
  brandId?: string | null
  tenant?: { id: string; name: string } | null
  brand?: { id: string; name: string } | null
}

export interface AuthSession {
  accessToken: string
  user: AuthUser
}

export interface LoginResponse {
  access_token: string
  user: AuthUser
}
