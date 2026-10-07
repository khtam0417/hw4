import type { Product } from './types.ts'

/** A size with this many units or fewer is shown as "Only N left". */
export const LOW_STOCK = 5

/** Every size the shop makes, in order. */
export const SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

const priceFormat = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export function formatPrice(price: number): string {
  return priceFormat.format(price)
}

export function sizesInStock(product: Product): number {
  return product.inventory.filter((size) => size.quantity > 0).length
}

/** Units in stock in one size (0 if sold out). */
export function quantityIn(product: Product, size: string): number {
  return product.inventory.find((level) => level.size === size)?.quantity ?? 0
}

/** A size from the address bar ("M"), or '' when it's missing or not a size the shop makes. */
export function toSize(value: string | null): string {
  const size = value?.toUpperCase() ?? ''
  return SIZE_ORDER.includes(size) ? size : ''
}

export function stockLabel(quantity: number): string {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

/** A size with this many units or more fills its stock bar on the product page. */
export const FULL_STOCK = 20

/** Sizes that are in stock, and those with only a few left, for a card's row of size boxes. */
export function sizeAvailability(product: Product): { inStock: string[]; low: string[] } {
  const inStock = product.inventory.filter((level) => level.quantity > 0)
  return {
    inStock: inStock.map((level) => level.size),
    low: inStock.filter((level) => level.quantity <= LOW_STOCK).map((level) => level.size),
  }
}

// A dot of color beside each color name on the product page. Covers every color name in the catalogue;
// anything else gets a neutral dot, and the name is always written out.
const SWATCHES: Record<string, string> = {
  navy: '#1d2b4f',
  'navy blue': '#1d2b4f',
  'royal blue': '#2d5bd3',
  blue: '#1f5fbf',
  'light blue': '#a9c6ec',
  white: '#ffffff',
  ivory: '#f8f3e3',
  cream: '#f1e7cf',
  'light gray': '#d6d8db',
  gray: '#8d9196',
  'heather gray': 'linear-gradient(135deg, #c5c8cc, #a7abb0)',
  'dark heather gray': 'linear-gradient(135deg, #7a7e84, #5f6369)',
  'charcoal gray': '#4a4e54',
  'heather charcoal gray': 'linear-gradient(135deg, #63676d, #4b4f55)',
  'dark heather charcoal': 'linear-gradient(135deg, #565a60, #3e4247)',
  black: '#141414',
  red: '#b3261e',
  'dusty coral': '#d98b7a',
  yellow: '#f2c230',
  gold: '#c9a227',
  green: '#2e7d4f',
  multicolor: 'conic-gradient(#b3261e, #f2c230, #2e7d4f, #1f5fbf, #b3261e)',
}

export function swatchFor(color: string): string {
  return SWATCHES[color.trim().toLowerCase()] ?? 'linear-gradient(135deg, #e8e1d4, #cfc7b8)'
}

/** "All sizes in stock", "In stock: S, M" or "Sold out", from a card's list of sizes in stock. */
export function sizesNote(sizesInStock: string[]): string {
  if (sizesInStock.length === SIZE_ORDER.length) return 'All sizes in stock'
  return sizesInStock.length > 0 ? `In stock: ${sizesInStock.join(', ')}` : 'Sold out'
}
