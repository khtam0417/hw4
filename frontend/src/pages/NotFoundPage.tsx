import { Link } from 'react-router'
import Notice from '../components/Notice.tsx'

export default function NotFoundPage() {
  return (
    <div className="container page">
      <title>Page not found | Campus Customs</title>
      <Notice
        title="Page not found"
        action={
          <div className="notice-actions">
            <Link to="/" className="button button-primary">
              Go home
            </Link>
            <Link to="/products" className="button button-secondary">
              Browse products
            </Link>
          </div>
        }
      >
        The page you're looking for doesn't exist or has moved.
      </Notice>
    </div>
  )
}
