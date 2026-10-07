import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api.ts'
import { returnPath, useAuth } from '../auth.ts'
import Crest from '../components/Crest.tsx'
import FormField from '../components/FormField.tsx'
import SignedInCard from '../components/SignedInCard.tsx'
import { EMAIL_MAX, PASSWORD_MAX, checkLogin, type FieldErrors } from '../validation.ts'

export default function LoginPage() {
  const { user, checking, logIn, logOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const problems = checkLogin(email, password)
    setErrors(problems)
    setFormError('')
    if (Object.keys(problems).length > 0) return
    setSubmitting(true)
    try {
      await logIn(email, password)
      navigate(returnPath(location.state), { replace: true })
    } catch (error) {
      setPassword('')
      if (error instanceof ApiError) {
        setFormError(error.message)
        setErrors(error.fields)
      } else {
        setFormError("We couldn't reach the server. Check that the backend is running, then try again.")
      }
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page">
      <title>Log in | Campus Customs</title>
      {user && !submitting ? (
        <SignedInCard user={user} onLogOut={logOut} />
      ) : (
        <div className="auth-card">
          <Crest className="auth-crest" />
          <h1>Log in</h1>
          <p className="auth-lead">Welcome back! Log in to your Campus Customs account.</p>
          <form className="form" onSubmit={handleSubmit} noValidate>
            {formError && (
              <p className="form-error" role="alert">
                {formError}
              </p>
            )}
            <FormField
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              maxLength={EMAIL_MAX}
              value={email}
              onValueChange={setEmail}
              error={errors.email}
            />
            <FormField
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              maxLength={PASSWORD_MAX}
              value={password}
              onValueChange={setPassword}
              error={errors.password}
            />
            <button type="submit" className="button button-primary" disabled={submitting || checking}>
              {submitting ? 'Logging in…' : 'Log in'}
            </button>
          </form>
          <p className="auth-switch">
            New to Campus Customs?{' '}
            <Link to="/create-account" state={location.state}>
              Create an account
            </Link>
          </p>
        </div>
      )}
    </section>
  )
}
