import { SIZE_ORDER, quantityIn } from './format.ts'
import type { PageResults, Product } from './types.ts'

/** Display order for the category filters (the backend groups garment_type into these). */
const CATEGORY_ORDER = ['Hoodies', 'Crewnecks', 'T-Shirts', 'Quarter-Zips', 'Jackets & Fleece', 'Long Sleeves']

export const SORT_OPTIONS = [
  { value: 'name', label: 'Name (A–Z)' },
  { value: 'price-asc', label: 'Price: low to high' },
  { value: 'price-desc', label: 'Price: high to low' },
] as const

export type SortKey = (typeof SORT_OPTIONS)[number]['value']

export function toSortKey(value: string | null): SortKey {
  return SORT_OPTIONS.find((option) => option.value === value)?.value ?? 'name'
}

export function summarizeCategories(products: Product[]): { name: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const product of products) counts.set(product.category, (counts.get(product.category) ?? 0) + 1)
  const rank = (name: string) => {
    const index = CATEGORY_ORDER.indexOf(name)
    return index === -1 ? CATEGORY_ORDER.length : index
  }
  return [...counts]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name))
}

function searchText(product: Product): string {
  return [product.name, product.garment_type, product.category, product.description, ...product.colors, ...product.search_tags]
    .join(' ')
    .toLowerCase()
}

/** Every word must appear somewhere in the product's text; a trailing "s" is dropped so "hoodies" finds "hoodie". */
export function matchesSearch(product: Product, query: string): boolean {
  const words = query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => (word.length > 3 && word.endsWith('s') ? word.slice(0, -1) : word))
  if (words.length === 0) return true
  const text = searchText(product)
  return words.every((word) => text.includes(word))
}

const COMPARE: Record<SortKey, (a: Product, b: Product) => number> = {
  name: (a, b) => a.name.localeCompare(b.name),
  'price-asc': (a, b) => a.price - b.price || a.name.localeCompare(b.name),
  'price-desc': (a, b) => b.price - a.price || a.name.localeCompare(b.name),
}

export interface ProductFilters {
  query: string
  category: string
  /** Only products with this size in stock ('' for any size). */
  size: string
  sort: SortKey
}

export function filterProducts(products: Product[], { query, category, size, sort }: ProductFilters): Product[] {
  return products
    .filter(
      (product) =>
        (!category || product.category === category) &&
        (!size || quantityIn(product, size) > 0) &&
        matchesSearch(product, query),
    )
    .sort(COMPARE[sort])
}

/** For each size, how many of the products that match the search and category have it in stock. */
export function countInStockBySize(products: Product[], filters: Omit<ProductFilters, 'size' | 'sort'>): Map<string, number> {
  const matching = filterProducts(products, { ...filters, size: '', sort: 'name' })
  return new Map(SIZE_ORDER.map((size) => [size, matching.filter((product) => quantityIn(product, size) > 0).length]))
}

/** The products with these ids, in this order (ids missing from the catalogue are skipped). */
export function pickProducts(products: Product[] | null, ids: string[]): Product[] {
  if (!products) return []
  const byId = new Map(products.map((product) => [product.product_id, product]))
  return ids.flatMap((id) => byId.get(id) ?? [])
}

/** The results page's address for a search, e.g. /search?q=bulldog&size=M (q is always set, even if empty). */
export function resultsPath(results: Pick<PageResults, 'query' | 'category' | 'max_price' | 'size'>): string {
  const search = new URLSearchParams({ q: results.query })
  if (results.category) search.set('category', results.category)
  if (results.max_price !== null) search.set('max_price', String(results.max_price))
  if (results.size) search.set('size', results.size)
  return `/search?${search}`
}
