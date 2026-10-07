import { useEffect, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router'
import { fetchSearchResults } from '../api.ts'
import { ChatIcon } from '../components/Icons.tsx'
import Notice from '../components/Notice.tsx'
import { ProductCardSkeleton } from '../components/ProductCard.tsx'
import SearchResultCard from '../components/SearchResultCard.tsx'
import type { PageResults } from '../types.ts'

/**
 * The results of the shop assistant's latest catalogue search, in the main page area. The chat opens
 * this page with its results in the navigation state; a reloaded or shared /search link fetches the
 * same search from GET /api/search.
 */
export default function SearchResultsPage() {
  const location = useLocation()
  const [params] = useSearchParams()
  const search = params.toString()
  const fromChat = (location.state as { results?: PageResults } | null)?.results ?? null
  const [fetched, setFetched] = useState<{ search: string; results: PageResults | null } | null>(null)

  useEffect(() => {
    if (fromChat || !search) return
    let active = true
    fetchSearchResults(new URLSearchParams(search)).then(
      (results) => active && setFetched({ search, results }),
      () => active && setFetched({ search, results: null }),
    )
    return () => {
      active = false
    }
  }, [search, fromChat])

  const results = fromChat ?? (fetched?.search === search ? fetched.results : undefined)

  let content
  if (!search && !fromChat) {
    content = (
      <Notice
        title="Ask the shop assistant to find something"
        action={
          <Link to="/products" className="button button-primary">
            Browse all products
          </Link>
        }
      >
        Open the chat in the corner and ask, for example, “What hoodies do you have?”. The matching products will show
        up here.
      </Notice>
    )
  } else if (results === undefined) {
    content = (
      <div className="product-grid" aria-busy="true">
        {Array.from({ length: 8 }, (_, index) => (
          <ProductCardSkeleton key={index} />
        ))}
      </div>
    )
  } else if (results === null) {
    content = (
      <Notice
        title="We couldn't load these results"
        action={
          <Link to="/products" className="button button-primary">
            Browse all products
          </Link>
        }
      >
        Check that the backend is running, then try the search again.
      </Notice>
    )
  } else if (results.total_matches === 0) {
    content = (
      <Notice
        title={`No products match ${results.title}`}
        action={
          <Link to="/products" className="button button-primary">
            Browse all products
          </Link>
        }
      >
        {results.note ?? 'Try asking the assistant with different words, like a color, a team or a type of garment.'}
      </Notice>
    )
  } else {
    content = (
      <div className="product-grid">
        {results.products.map((product) => (
          <SearchResultCard key={product.product_id} product={product} />
        ))}
      </div>
    )
  }

  const count = results?.total_matches ?? 0
  return (
    <div className="container page">
      <title>{`${results?.title ?? 'Search results'} | Campus Customs`}</title>
      <header className="page-header">
        <p className="eyebrow eyebrow-with-icon">
          <ChatIcon /> Chat search
        </p>
        <h1>{results?.title ?? 'Search results'}</h1>
        {results && count > 0 && (
          <p className="page-lead">
            {count} {count === 1 ? 'product matches' : 'products match'} your search with the shop assistant. Open a card
            for photos, sizes and stock.
          </p>
        )}
      </header>
      {content}
    </div>
  )
}
