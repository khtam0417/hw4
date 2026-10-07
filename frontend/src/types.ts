/** Shapes returned by the FastAPI backend (backend/main.py). */

export interface StockLevel {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  /** Shop category the backend derives from garment_type (for example "Hoodies"). */
  category: string
  description: string
  colors: string[]
  search_tags: string[]
  /** Path stored in the database, relative to data/ (for example "products/x.jpg"). */
  image_file_path: string
  /** URL the backend serves that image from: "/media/" + image_file_path. */
  image_url: string
  price: number
  inventory: StockLevel[]
  total_stock: number
}

/** A logged-in shopper as the backend returns them. The API never sends a password or its hash. */
export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

/** What the Create account form sends to POST /api/auth/register. */
export interface RegisterForm {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

/** A product card (under a chat reply or on the results page). The backend builds it from the database. */
export interface ProductCard {
  product_id: string
  name: string
  category: string
  price: number
  image_url: string
  short_description: string
  sizes_in_stock: string[]
}

/** A catalogue search for the results page: from a chat reply, or from GET /api/search. */
export interface PageResults {
  title: string
  query: string
  category: string | null
  max_price: number | null
  size: string | null
  total_matches: number
  note: string | null
  products: ProductCard[]
}

/** The page the customer is on when they send a chat message (product_id is set on a product page). */
export interface PageContext {
  path: string
  product_id: string | null
}

/** A logged-in customer's saved conversation from GET /api/chat/history (saved is false for guests). */
export interface ChatHistory {
  saved: boolean
  messages: { role: 'user' | 'assistant'; content: string; products: ProductCard[]; created_at: string }[]
}

/**
 * One chat turn: who said it, the text and, for the assistant, the product cards shown with it and
 * the search it put on the results page (if it searched).
 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ProductCard[]
  pageResults?: PageResults
}
