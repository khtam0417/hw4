import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api.ts'
import { returnPath, useAuth } from '../auth.ts'
import Crest from '../components/Crest.tsx'
import FormField from '../components/FormField.tsx'
import SignedInCard from '../components/SignedInCard.tsx'
import type { RegisterForm } from '../types.ts'
import { EMAIL_MAX, NAME_MAX, PASSWORD_MAX, PASSWORD_MIN, checkRegistration, type FieldErrors } from '../validation.ts'

const EMPTY_FORM: RegisterForm = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function CreateAccountPage() {
  const { user, checking, createAccount, logOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState<RegisterForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState('')
  const [emailTaken, setEmailTaken] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const setField = (field: keyof RegisterForm) => (value: string) => setForm((current) => ({ ...current, [field]: value }))

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const problems = checkRegistration(form)
    setErrors(problems)
    setEmailTaken(false)
    setFormError(Object.keys(problems).length > 0 ? 'Please fix the highlighted fields.' : '')
    if (Object.keys(problems).length > 0) return
    setSubmitting(true)
    try {
      await createAccount(form)
      navigate(returnPath(location.state), { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.message)
        setErrors(error.fields)
        setEmailTaken(error.status === 409)
      } else {
        setFormError("We couldn't reach the server. Check that the backend is running, then try again.")
      }
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page">
      <title>Create account | Campus Customs</title>
      {user && !submitting ? (
        <SignedInCard user={user} onLogOut={logOut} />
      ) : (
        <div className="auth-card">
          <Crest className="auth-crest" />
          <h1>Create account</h1>
          <p className="auth-lead">Set up an account to get personal help from our shopping assistant.</p>
          <form className="form" onSubmit={handleSubmit} noValidate>
            {formError && (
              <p className="form-error" role="alert">
                {formError}{' '}
                {emailTaken && (
                  <Link to="/login" state={location.state}>
                    Log in instead
                  </Link>
                )}
              </p>
            )}
            <div className="form-row">
              <FormField
                label="First name"
                name="first_name"
                autoComplete="given-name"
                maxLength={NAME_MAX}
                value={form.first_name}
                onValueChange={setField('first_name')}
                error={errors.first_name}
              />
              <FormField
                label="Last name"
                name="last_name"
                autoComplete="family-name"
                maxLength={NAME_MAX}
                value={form.last_name}
                onValueChange={setField('last_name')}
                error={errors.last_name}
              />
            </div>
            <FormField
              label="Email"
              name="email"
              type="email"
              autoComplete="email"
              maxLength={EMAIL_MAX}
              value={form.email}
              onValueChange={setField('email')}
              error={errors.email}
            />
            <FormField
              label="Password"
              name="password"
              type="password"
              autoComplete="new-password"
              maxLength={PASSWORD_MAX}
              value={form.password}
              onValueChange={setField('password')}
              error={errors.password}
              hint={`At least ${PASSWORD_MIN} characters.`}
            />
            <FormField
              label="Confirm password"
              name="confirm_password"
              type="password"
              autoComplete="new-password"
              maxLength={PASSWORD_MAX}
              value={form.confirm_password}
              onValueChange={setField('confirm_password')}
              error={errors.confirm_password}
            />
            <button type="submit" className="button button-primary" disabled={submitting || checking}>
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>
          <p className="auth-switch">
            Already have an account?{' '}
            <Link to="/login" state={location.state}>
              Log in
            </Link>
          </p>
        </div>
      )}
    </section>
  )
}
