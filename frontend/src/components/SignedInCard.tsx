import { Link } from 'react-router'
import type { User } from '../types.ts'
import Crest from './Crest.tsx'

/** Shown on Log in and Create account when someone is already logged in. */
export default function SignedInCard({ user, onLogOut }: { user: User; onLogOut: () => void }) {
  return (
    <div className="auth-card">
      <Crest className="auth-crest" />
      <h1>You're logged in</h1>
      <p className="auth-lead">
        You're logged in as {user.first_name} {user.last_name} ({user.email}).
      </p>
      <div className="auth-actions">
        <Link to="/products" className="button button-primary">
          Continue shopping
        </Link>
        <button type="button" className="button button-secondary" onClick={onLogOut}>
          Log out
        </button>
      </div>
    </div>
  )
}
