import Crest from './Crest.tsx'
import { MailIcon, PinIcon } from './Icons.tsx'

const MAP_URL = 'https://www.google.com/maps/search/?api=1&query=57+Broadway+New+Haven+CT+06511'

export default function VisitCard() {
  return (
    <section className="visit-card" aria-labelledby="visit-title">
      <Crest className="crest-light visit-crest" />
      <div>
        <p className="eyebrow eyebrow-light">Visit the shop</p>
        <h2 id="visit-title">Come see us on Broadway</h2>
        <p>Try on a few sizes, ask the team for advice, or pick up a gift for someone who loves Yale as much as you do.</p>
        <address>
          <PinIcon /> 57 Broadway, New Haven, CT 06511
        </address>
      </div>
      <div className="visit-actions">
        <a className="button button-light" href={MAP_URL} target="_blank" rel="noreferrer">
          Get directions
        </a>
        <a className="button button-outline-light" href="mailto:orderdept@campuscustoms.com">
          <MailIcon /> Email us
        </a>
      </div>
    </section>
  )
}
