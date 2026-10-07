import { useMemo, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { SearchIcon } from '../components/Icons.tsx'
import Notice from '../components/Notice.tsx'
import ProductCard, { ProductCardSkeleton } from '../components/ProductCard.tsx'
import { SORT_OPTIONS, countInStockBySize, filterProducts, summarizeCategories, toSortKey } from '../catalogue.ts'
import { SIZE_ORDER, toSize } from '../format.ts'
import { useProducts } from '../hooks.ts'

export default function ProductsPage() {
  const { products, failed, retry } = useProducts()
  // Search, category, size and sort live in the URL, so links and the back button keep them.
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const size = toSize(params.get('size'))
  const sort = toSortKey(params.get('sort'))

  const categories = useMemo(() => (products ? summarizeCategories(products) : []), [products])
  const visible = useMemo(
    () => (products ? filterProducts(products, { query, category, size, sort }) : []),
    [products, query, category, size, sort],
  )
  const inStockBySize = useMemo(
    () => (products ? countInStockBySize(products, { query, category }) : null),
    [products, query, category],
  )

  function updateParams(changes: Record<string, string>) {
    setParams(
      () => {
        // Start from the address bar rather than the last render, so quick successive changes don't undo each other.
        const next = new URLSearchParams(window.location.search)
        for (const [key, value] of Object.entries(changes)) {
          if (value) next.set(key, value)
          else next.delete(key)
        }
        return next
      },
      { replace: true },
    )
  }

  const clearFilters = () => updateParams({ q: '', category: '', size: '' })
  const clearButton = (
    <button type="button" className="button button-secondary" onClick={clearFilters}>
      Clear filters
    </button>
  )

  let results: ReactNode
  if (failed) {
    results = (
      <Notice
        title="We couldn't load the products"
        action={
          <button type="button" className="button button-primary" onClick={retry}>
            Try again
          </button>
        }
      >
        Check that the backend is running, then try again.
      </Notice>
    )
  } else if (!products) {
    results = (
      <div className="product-grid" aria-busy="true">
        {Array.from({ length: 8 }, (_, index) => (
          <ProductCardSkeleton key={index} />
        ))}
      </div>
    )
  } else {
    results = (
      <>
        <div className="result-bar">
          <p className="result-count" aria-live="polite">
            Showing {visible.length} of {products.length} products{size && ` in stock in size ${size}`}
          </p>
          {(query || category || size) && (
            <button type="button" className="link-button" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
        {visible.length > 0 ? (
          <div className="product-grid">
            {visible.map((product) => (
              <ProductCard key={product.product_id} product={product} size={size} />
            ))}
          </div>
        ) : (
          <Notice title="No products match your search" action={clearButton}>
            {size
              ? `Nothing that matches is in stock in size ${size}. Try another size, or clear the filters.`
              : 'Try a different word, like “hoodie”, “navy” or “bulldog”.'}
          </Notice>
        )}
      </>
    )
  }

  return (
    <div className="container page">
      <title>Products | Campus Customs</title>
      <header className="page-header">
        <p className="eyebrow">Shop</p>
        <h1>All products</h1>
        <p className="page-lead">Every style in the Campus Customs catalogue, with sizes and stock for each one.</p>
      </header>

      <div className="toolbar">
        <div className="search-field">
          <SearchIcon />
          <input
            type="search"
            value={query}
            onChange={(event) => updateParams({ q: event.target.value })}
            placeholder="Search hoodies, sports, schools, colors…"
            aria-label="Search products"
          />
        </div>
        <label className="sort-field">
          <span>Sort by</span>
          <select value={sort} onChange={(event) => updateParams({ sort: event.target.value === 'name' ? '' : event.target.value })}>
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chips" role="group" aria-label="Filter by category">
        <button type="button" className="chip" aria-pressed={!category} onClick={() => updateParams({ category: '' })}>
          All <span className="chip-count">{products?.length ?? '–'}</span>
        </button>
        {categories.map(({ name, count }) => (
          <button
            key={name}
            type="button"
            className="chip"
            aria-pressed={category === name}
            onClick={() => updateParams({ category: category === name ? '' : name })}
          >
            {name} <span className="chip-count">{count}</span>
          </button>
        ))}
      </div>

      <div className="size-filter" role="group" aria-labelledby="size-filter-label">
        <span id="size-filter-label" className="size-filter-label">
          In stock in size
        </span>
        <button type="button" className="size-option" aria-pressed={!size} onClick={() => updateParams({ size: '' })}>
          Any
        </button>
        {SIZE_ORDER.map((option) => (
          <button
            key={option}
            type="button"
            className="size-option"
            aria-pressed={size === option}
            title={inStockBySize ? `${inStockBySize.get(option)} styles in stock in ${option}` : undefined}
            onClick={() => updateParams({ size: size === option ? '' : option })}
          >
            {option}
            <span className="size-option-count">{inStockBySize?.get(option) ?? '–'}</span>
          </button>
        ))}
      </div>

      {results}
    </div>
  )
}
