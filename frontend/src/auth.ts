import { createContext, useContext } from 'react'
import type { RegisterForm, User } from './types.ts'

export interface Auth {
  /** The logged-in user, or null when logged out. */
  user: User | null
  /** True until the backend has said who is logged in, so the nav doesn't flash "Log in". */
  checking: boolean
  /** A short message shown under the header, such as "Welcome back, Test!". */
  notice: string | null
  dismissNotice: () => void
  logIn: (email: string, password: string) => Promise<User>
  createAccount: (form: RegisterForm) => Promise<User>
  logOut: () => Promise<void>
}

export const AuthContext = createContext<Auth | null>(null)

export function useAuth(): Auth {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth must be used inside <AuthProvider>')
  return auth
}

/** Where to go after logging in: back to the page the visitor came from (state.from), or home. */
export function returnPath(state: unknown): string {
  const from = (state as { from?: unknown } | null)?.from
  if (typeof from !== 'string' || !from.startsWith('/') || from.startsWith('//')) return '/'
  const path = from.split(/[?#]/)[0]
  return path === '/login' || path === '/create-account' ? '/' : from
}
