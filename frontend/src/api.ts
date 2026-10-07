import type { ChatHistory, ChatMessage, PageContext, PageResults, Product, ProductCard, RegisterForm, User } from './types.ts'

/**
 * An error response from the backend. Form errors carry a readable message plus one message per
 * field, for example { email: 'This email is already registered.' }.
 */
export class ApiError extends Error {
  readonly status: number
  readonly fields: Record<string, string>

  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

// Requests go to the same origin (Vite forwards /api), so the HttpOnly session cookie is sent automatically.
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const detail: unknown = await response.json().then(
      (body) => body?.detail,
      () => undefined,
    )
    if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      const { message, fields } = detail as { message: string; fields?: Record<string, string> }
      throw new ApiError(response.status, message, fields ?? {})
    }
    const fallback = `Request to ${url} failed with status ${response.status}`
    throw new ApiError(response.status, typeof detail === 'string' ? detail : fallback)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

function postJson<T>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export function fetchProducts(): Promise<Product[]> {
  return request<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<Product> {
  return request<Product>(`/api/products/${encodeURIComponent(productId)}`)
}

/** The logged-in user, or null when nobody is logged in. */
export function fetchCurrentUser(): Promise<User | null> {
  return request<User | null>('/api/auth/me')
}

export function logIn(email: string, password: string): Promise<User> {
  return postJson<User>('/api/auth/login', { email, password })
}

export function createAccount(form: RegisterForm): Promise<User> {
  return postJson<User>('/api/auth/register', form)
}

export function logOut(): Promise<void> {
  return postJson<void>('/api/auth/logout')
}

/** How many earlier messages a guest's chat sends with each request (logged-in history is kept on the server). */
const CHAT_HISTORY_SENT = 20

interface ChatResponse {
  reply: string
  products: ProductCard[]
  page_results: PageResults | null
  saved: boolean
}

/** The logged-in customer's saved conversation, oldest first (empty for guests). */
export function fetchChatHistory(): Promise<ChatHistory> {
  return request<ChatHistory>('/api/chat/history')
}

/**
 * Sends a new message to the shop agent (POST /api/chat) with the page the customer is on, and returns its
 * reply, the product cards shown with it, and the results of any catalogue search it ran. guestHistory is
 * the conversation so far for a guest; a logged-in customer's history comes from the server.
 */
export async function sendChatMessage(message: string, guestHistory: ChatMessage[], page: PageContext): Promise<ChatMessage> {
  const history = guestHistory.slice(-CHAT_HISTORY_SENT).map(({ role, content }) => ({ role, content }))
  const { reply, products, page_results } = await postJson<ChatResponse>('/api/chat', { message, history, page })
  return { role: 'assistant', content: reply, products, pageResults: page_results ?? undefined }
}

/** The same search the agent runs, for a results page that was opened from a link or reloaded. */
export function fetchSearchResults(search: URLSearchParams): Promise<PageResults> {
  return request<PageResults>(`/api/search?${search}`)
}
