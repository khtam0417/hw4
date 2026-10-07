import { Link } from 'react-router'
import Crest from './Crest.tsx'

const categoryLink = (category: string) => `/products?category=${encodeURIComponent(category)}`
const YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div>
          <p className="footer-brand">
            <Crest className="crest-light" />
            Campus Customs
          </p>
          <p>Yale Bulldog Blue apparel and gifts for students, alumni, families and fans.</p>
        </div>
        <div>
          <h2>Shop</h2>
          <ul>
            <li><Link to="/products">All products</Link></li>
            <li><Link to={categoryLink('Hoodies')}>Hoodies</Link></li>
            <li><Link to={categoryLink('Crewnecks')}>Crewnecks</Link></li>
            <li><Link to={categoryLink('T-Shirts')}>T-shirts</Link></li>
          </ul>
        </div>
        <div>
          <h2>Company</h2>
          <ul>
            <li><Link to="/about">About us</Link></li>
            <li><Link to="/login">Log in</Link></li>
            <li><Link to="/create-account">Create account</Link></li>
          </ul>
        </div>
        <div>
          <h2>Visit</h2>
          <address>
            57 Broadway
            <br />
            New Haven, CT 06511
          </address>
          <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
        </div>
      </div>
      <div className="container footer-bottom">
        <p>© {YEAR} Campus Customs · A class project built on the Campus Customs catalogue.</p>
      </div>
    </footer>
  )
}
