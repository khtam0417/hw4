import type { RegisterForm } from './types.ts'

// The same rules the backend enforces (backend/auth.py), checked here first for instant feedback.
export const NAME_MAX = 50
export const EMAIL_MAX = 254
export const PASSWORD_MIN = 8
export const PASSWORD_MAX = 128
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export type FieldErrors = Record<string, string>

export function checkRegistration(form: RegisterForm): FieldErrors {
  const errors: FieldErrors = {}
  if (!form.first_name.trim()) errors.first_name = 'Enter your first name.'
  if (!form.last_name.trim()) errors.last_name = 'Enter your last name.'
  if (!EMAIL_PATTERN.test(form.email.trim())) errors.email = 'Enter a valid email address, like name@example.com.'
  if (form.password.length < PASSWORD_MIN) errors.password = `Use at least ${PASSWORD_MIN} characters.`
  if (form.confirm_password !== form.password) errors.confirm_password = "The passwords don't match."
  return errors
}

export function checkLogin(email: string, password: string): FieldErrors {
  const errors: FieldErrors = {}
  if (!email.trim()) errors.email = 'Enter your email.'
  if (!password) errors.password = 'Enter your password.'
  return errors
}
