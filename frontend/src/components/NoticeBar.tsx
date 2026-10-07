import { useAuth } from '../auth.ts'
import { CloseIcon } from './Icons.tsx'

/** Short confirmations under the header, such as "You've been logged out." */
export default function NoticeBar() {
  const { notice, dismissNotice } = useAuth()
  return (
    <div className="notice-bar" role="status">
      {notice && (
        <div className="container notice-bar-inner">
          <p>{notice}</p>
          <button type="button" className="notice-bar-close" onClick={dismissNotice}>
            <CloseIcon />
            <span className="sr-only">Dismiss message</span>
          </button>
        </div>
      )}
    </div>
  )
}
