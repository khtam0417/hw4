import { matchPath } from 'react-router'
import { toSize } from './format.ts'

const OPEN_CHAT_EVENT = 'campus-customs:open-chat'

/** Opens the chat panel from anywhere on the site, for example the "Ask about this item" button. */
export function openChat() {
  window.dispatchEvent(new Event(OPEN_CHAT_EVENT))
}

/** Calls `onOpen` whenever something asks for the chat to open. Returns a function that stops listening. */
export function onOpenChat(onOpen: () => void): () => void {
  window.addEventListener(OPEN_CHAT_EVENT, onOpen)
  return () => window.removeEventListener(OPEN_CHAT_EVENT, onOpen)
}

/**
 * One-click questions for the chat panel that fit the page the shopper is on. On a product page they
 * say "this", which the agent reads as that product (the page is sent with every message); with a size
 * chosen on the Products page, the first one asks about that size. On a chat search's results page they
 * narrow the search by size or price, unless it's already narrowed that way.
 */
export function suggestedQuestions(pathname: string, search: string): string[] {
  const params = new URLSearchParams(search)
  if (matchPath('/products/:productId', pathname)) {
    const size = toSize(params.get('size'))
    return [
      size ? `Do you have this in size ${size}?` : 'What sizes are left in this one?',
      'What colors does this come in?',
      'Show me similar items',
    ]
  }
  if (pathname === '/search') {
    return [
      ...(params.get('size') ? [] : ['Which of these come in size M?']),
      ...(params.get('max_price') ? [] : ['Which of these are under $50?']),
    ]
  }
  return ['What hoodies do you have?', 'Gift ideas under $50', "What's in stock in size XL?"]
}
