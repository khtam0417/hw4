import type { ReactNode } from 'react'

/** A centered message for empty results, missing pages and loading errors. */
export default function Notice({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="notice" role="status">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}
