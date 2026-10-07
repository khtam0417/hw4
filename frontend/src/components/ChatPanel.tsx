import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router'
import { ApiError, fetchChatHistory, sendChatMessage } from '../api.ts'
import { useAuth } from '../auth.ts'
import { resultsPath } from '../catalogue.ts'
import { onOpenChat, suggestedQuestions } from '../chat.ts'
import { formatPrice } from '../format.ts'
import type { ChatMessage, PageContext, PageResults, User } from '../types.ts'
import Crest from './Crest.tsx'
import { ChatIcon, CloseIcon, SendIcon } from './Icons.tsx'

const MAX_MESSAGE = 1000 // the backend's limit for one customer message

/** A message in the panel; failed replies are shown but never sent back to the agent. */
type ShownMessage = ChatMessage & { failed?: boolean }

function greeting(firstName?: string): ChatMessage {
  return {
    role: 'assistant',
    content: `Hi${firstName ? ` ${firstName}` : ''}! I'm the Campus Customs assistant. Ask me about our Yale gear, prices or which sizes are in stock.`,
  }
}

function errorReply(error: unknown): ShownMessage {
  // 400, 429 and 503 responses carry a message written for customers; anything else means the backend wasn't reached.
  const content =
    error instanceof ApiError && (error.status === 400 || error.status === 429 || error.status === 503)
      ? error.message
      : "Sorry, I couldn't reach the shop assistant. Please try again in a moment."
  return { role: 'assistant', content, failed: true }
}

function resultsLinkText(results: PageResults): string {
  const count = results.total_matches
  if (count === 0) return 'No matching products. See the page'
  return `Showing ${count} ${count === 1 ? 'product' : 'products'} on the page`
}

/** Shows **bold** (used in some older saved replies) as bold text; everything else stays plain. */
function withBold(text: string): ReactNode {
  return text
    .split('**')
    .map((part, index) => (index % 2 === 1 ? <strong key={index}>{part}</strong> : <Fragment key={index}>{part}</Fragment>))
}

/** The page the customer is on, sent with each message so the agent knows what "this" means. */
function currentPage(pathname: string, search: string): PageContext {
  return { path: pathname + search, product_id: matchPath('/products/:productId', pathname)?.params.productId ?? null }
}

/**
 * Floating chat in the bottom-right corner. Each message goes to the shop agent through POST /api/chat
 * with the page the customer is on. A logged-in customer's conversation is saved on the server and
 * reloaded here (GET /api/chat/history); a guest's chat is kept only in this panel. The panel starts
 * fresh whenever someone logs in or out, so one shopper's chat is never shown to the next. When the
 * agent searches the catalogue, the site opens the results page (/search) with its matches.
 * Suggested questions for the current page sit above the message box until the shopper asks something
 * on that page, and the "Ask about this item" button on product pages opens the panel (chat.ts).
 */
export default function ChatPanel() {
  const { user } = useAuth()
  return <ChatWindow key={user?.id ?? 'guest'} customer={user} />
}

function ChatWindow({ customer }: { customer: User | null }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ShownMessage[]>([])
  const [savedCount, setSavedCount] = useState(0) // messages that came from the saved history
  const [historyState, setHistoryState] = useState<'loading' | 'ready' | 'failed'>(customer ? 'loading' : 'ready')
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [askedOn, setAskedOn] = useState<string | null>(null) // the page of the shopper's latest message
  const navigate = useNavigate()
  const location = useLocation()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLOListElement>(null)
  const firstName = customer?.first_name

  // Reload a logged-in customer's saved conversation.
  useEffect(() => {
    if (!customer) return
    let active = true
    fetchChatHistory().then(
      (history) => {
        if (!active) return
        setMessages(history.messages.map(({ role, content, products }) => ({ role, content, products })))
        setSavedCount(history.messages.length)
        setHistoryState('ready')
      },
      () => active && setHistoryState('failed'),
    )
    return () => {
      active = false
    }
  }, [customer])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  useEffect(
    () =>
      onOpenChat(() => {
        setOpen(true)
        inputRef.current?.focus() // when the panel is already open
      }),
    [],
  )

  useEffect(() => {
    const list = listRef.current
    if (list) list.scrollTop = list.scrollHeight
  }, [messages, sending, open, historyState])

  useEffect(() => {
    if (!open) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])

  const page = location.pathname + location.search
  const suggestions = suggestedQuestions(location.pathname, location.search)
  const showSuggestions =
    suggestions.length > 0 && historyState !== 'loading' && !sending && !draft.trim() && askedOn !== page

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    send(draft.trim())
  }

  async function send(text: string) {
    if (!text || sending || historyState === 'loading') return
    setMessages((current) => [...current, { role: 'user', content: text }])
    setDraft('')
    setAskedOn(page)
    setSending(true)
    try {
      // A guest's conversation travels with the message; a logged-in customer's is read from their saved history.
      const guestHistory = customer ? [] : messages.filter((message) => !message.failed)
      const reply = await sendChatMessage(text, guestHistory, currentPage(location.pathname, location.search))
      setMessages((current) => [...current, reply])
      if (reply.pageResults) {
        navigate(resultsPath(reply.pageResults), { state: { results: reply.pageResults } })
      }
    } catch (error) {
      setMessages((current) => [...current, errorReply(error)])
    } finally {
      setSending(false)
    }
  }

  function renderMessage(message: ShownMessage, key: string | number) {
    return (
      <li key={key} className={`chat-message ${message.role}`}>
        <p>{withBold(message.content)}</p>
        {message.products && message.products.length > 0 && (
          <ul className="chat-products">
            {message.products.map((product) => (
              <li key={product.product_id}>
                <Link to={`/products/${product.product_id}`}>
                  <img src={product.image_url} alt="" />
                  <span className="chat-product-text">
                    <span className="chat-product-name">{product.name}</span>
                    <span className="chat-product-sizes">
                      {product.sizes_in_stock.length > 0 ? `In stock: ${product.sizes_in_stock.join(', ')}` : 'Sold out'}
                    </span>
                  </span>
                  <span className="chat-product-price">{formatPrice(product.price)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        {message.pageResults && (
          <Link
            className="chat-results-link"
            to={resultsPath(message.pageResults)}
            state={{ results: message.pageResults }}
            onClick={() => {
              // On a phone the panel covers the page, so close it to show the results.
              if (window.matchMedia('(max-width: 640px)').matches) setOpen(false)
            }}
          >
            {resultsLinkText(message.pageResults)} →
          </Link>
        )}
      </li>
    )
  }

  return (
    <div className="chat">
      <section id="chat-panel" className="chat-panel" aria-label="Chat with Campus Customs" hidden={!open}>
        <header className="chat-header">
          <Crest className="crest-light chat-avatar" />
          <div className="chat-heading">
            <p className="chat-title">Campus Customs Assistant</p>
            <p className="chat-subtitle">{customer ? 'Online · saved to your account' : 'Online · guest chat, not saved'}</p>
          </div>
          <button type="button" className="chat-close" onClick={() => setOpen(false)}>
            <CloseIcon />
            <span className="sr-only">Close chat</span>
          </button>
        </header>

        <ol className="chat-messages" ref={listRef} aria-live="polite">
          {savedCount === 0 && renderMessage(greeting(firstName), 'greeting')}
          {messages.map((message, index) => (
            <Fragment key={index}>
              {renderMessage(message, index)}
              {index === savedCount - 1 && (
                <li className="chat-note">
                  Welcome back{firstName ? `, ${firstName}` : ''}! Your earlier conversation is above.
                </li>
              )}
            </Fragment>
          ))}
          {historyState === 'loading' && <li className="chat-note">Loading your conversation…</li>}
          {historyState === 'failed' && <li className="chat-note">We couldn't load your earlier conversation.</li>}
          {sending && (
            <li className="chat-message assistant chat-typing">
              <span className="chat-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <span className="chat-typing-text">Checking the catalogue…</span>
            </li>
          )}
        </ol>

        {showSuggestions && (
          <div className="chat-suggestions" role="group" aria-label="Suggested questions">
            {suggestions.map((question) => (
              <button key={question} type="button" className="chat-suggestion" onClick={() => send(question)}>
                {question}
              </button>
            ))}
          </div>
        )}

        <form className="chat-form" onSubmit={handleSubmit}>
          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <input
            id="chat-input"
            ref={inputRef}
            value={draft}
            maxLength={MAX_MESSAGE}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask about products, sizes or stock…"
            autoComplete="off"
          />
          <button type="submit" disabled={!draft.trim() || sending || historyState === 'loading'}>
            <SendIcon />
            <span className="sr-only">Send</span>
          </button>
        </form>
      </section>

      <button
        type="button"
        className="chat-toggle"
        aria-expanded={open}
        aria-controls="chat-panel"
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        {open ? <CloseIcon /> : <ChatIcon />}
        <span className="chat-toggle-label">{open ? 'Close chat' : 'Chat with us'}</span>
      </button>
    </div>
  )
}
