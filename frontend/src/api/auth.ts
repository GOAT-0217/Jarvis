import client from './client'

export interface LoginParams {
  username: string
  password: string
}

export interface RegisterParams {
  username: string
  password: string
  nickname?: string
  email?: string
  role?: string
  admin_code?: string
}

export interface AuthData {
  access_token: string
  token_type: string
  username: string
  role: string
}

export interface CurrentUserData {
  username: string
  role: string
  nickname?: string
  email?: string
}

export function login(params: LoginParams) {
  return client.post<any, { data: AuthData }>('/auth/login', params)
}

export function register(params: RegisterParams) {
  return client.post<any, { data: AuthData }>('/auth/register', params)
}

export function getMe() {
  return client.get<any, { data: CurrentUserData }>('/auth/me')
}

export function changePassword(params: { old_password: string; new_password: string }) {
  return client.put<any, { data: { message: string } }>('/auth/password', params)
}
