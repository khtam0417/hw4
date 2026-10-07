import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router'
import { useAuth } from '../auth.ts'
import Crest from './Crest.tsx'
import { CloseIcon, MenuIcon, UserIcon } from './Icons.tsx'

const MAIN_LINKS = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, checking, logOut } = useAuth()
  const location = useLocation()
  const closeMenu = () => setMenuOpen(false)
  // Log in and Create account remember this page, so people come back to it afterwards.
  const returnState = { from: location.pathname + location.search }

  let account
  if (checking) {
    account = <span className="nav-account-placeholder" aria-hidden="true" />
  } else if (user) {
    account = (
      <>
        <span className="nav-user">
          <span className="nav-avatar" aria-hidden="true">
            {(user.first_name || user.email).charAt(0).toUpperCase()}
          </span>
          Hi, {user.first_name}
        </span>
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={() => {
            closeMenu()
            void logOut()
          }}
        >
          Log out
        </button>
      </>
    )
  } else {
    account = (
      <>
        <NavLink to="/login" state={returnState} className="nav-login" onClick={closeMenu}>
          <UserIcon /> Log in
        </NavLink>
        <NavLink to="/create-account" state={returnState} className="button button-primary button-small" onClick={closeMenu}>
          Create account
        </NavLink>
      </>
    )
  }

  return (
    <header className="site-header">
      <p className="announcement">
        Officially licensed Yale apparel
        <span className="announcement-extra"> · 57 Broadway, New Haven · Every style in XS to XXL</span>
      </p>
      <nav className="container navbar" aria-label="Main">
        <Link to="/" className="wordmark" onClick={closeMenu}>
          <Crest />
          <span className="wordmark-text">
            <span className="wordmark-top">Campus Customs</span>
            <span className="wordmark-bottom">Yale Bulldog Blue</span>
          </span>
        </Link>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="site-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <CloseIcon /> : <MenuIcon />}
          <span className="sr-only">{menuOpen ? 'Close menu' : 'Open menu'}</span>
        </button>

        <div id="site-menu" className={menuOpen ? 'nav-menu open' : 'nav-menu'}>
          <ul className="nav-links">
            {MAIN_LINKS.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.to === '/'} onClick={closeMenu}>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav-actions">{account}</div>
        </div>
      </nav>
    </header>
  )
}
