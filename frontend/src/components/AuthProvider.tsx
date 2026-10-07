import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as api from '../api.ts'
import { AuthContext, type Auth } from '../auth.ts'
import type { RegisterForm, User } from '../types.ts'

const NOTICE_MS = 6000

/**
 * Keeps track of who is logged in. The session is an HttpOnly cookie the page can't read, so on load
 * it asks the backend (GET /api/auth/me); that is what keeps people logged in as they browse.
 */
export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api
      .fetchCurrentUser()
      .then(
        (current) => active && setUser(current),
        () => active && setUser(null), // backend unreachable: treat as logged out
      )
      .finally(() => active && setChecking(false))
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), NOTICE_MS)
    return () => window.clearTimeout(timer)
  }, [notice])

  const logIn = useCallback(async (email: string, password: string) => {
    const loggedIn = await api.logIn(email, password)
    setUser(loggedIn)
    setNotice(`Welcome back, ${loggedIn.first_name}!`)
    return loggedIn
  }, [])

  const createAccount = useCallback(async (form: RegisterForm) => {
    const created = await api.createAccount(form)
    setUser(created)
    setNotice(`Welcome to Campus Customs, ${created.first_name}! Your account is ready.`)
    return created
  }, [])

  const logOut = useCallback(async () => {
    try {
      await api.logOut()
      setUser(null)
      setNotice("You've been logged out.")
    } catch {
      setNotice("We couldn't log you out. Please try again.")
    }
  }, [])

  const dismissNotice = useCallback(() => setNotice(null), [])

  const auth = useMemo<Auth>(
    () => ({ user, checking, notice, dismissNotice, logIn, createAccount, logOut }),
    [user, checking, notice, dismissNotice, logIn, createAccount, logOut],
  )
  return <AuthContext value={auth}>{children}</AuthContext>
}
