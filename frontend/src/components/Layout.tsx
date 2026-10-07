import { Outlet, ScrollRestoration } from 'react-router'
import AuthProvider from './AuthProvider.tsx'
import ChatPanel from './ChatPanel.tsx'
import Footer from './Footer.tsx'
import NavBar from './NavBar.tsx'
import NoticeBar from './NoticeBar.tsx'

/** Shared frame for every page: navigation, messages, the page itself, footer and the floating chat. */
export default function Layout() {
  return (
    <AuthProvider>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <NavBar />
      <NoticeBar />
      <main id="main">
        <Outlet />
      </main>
      <Footer />
      <ChatPanel />
      <ScrollRestoration />
    </AuthProvider>
  )
}
