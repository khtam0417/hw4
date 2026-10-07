import { Link } from 'react-router'
import { LOW_STOCK, SIZE_ORDER, formatPrice, quantityIn, sizeAvailability, sizesNote, stockLabel } from '../format.ts'
import type { Product } from '../types.ts'

/**
 * A catalogue card. The row of size boxes shows at a glance which sizes are in stock, low or sold out.
 * With a size (the Products page's size filter), that size's box is filled in, the card also says how
 * many are left in it, and its link carries the size so the product page can highlight it.
 */
export default function ProductCard({ product, size = '' }: { product: Product; size?: string }) {
  const { inStock, low } = sizeAvailability(product)
  const quantity = size ? quantityIn(product, size) : 0
  return (
    <Link to={`/products/${product.product_id}${size ? `?size=${size}` : ''}`} className="product-card">
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" decoding="async" />
      </div>
      <div className="product-card-body">
        <p className="eyebrow">{product.category}</p>
        <h3 className="product-card-name">{product.name}</h3>
        <p className="product-card-description">{product.description}</p>
        <div className="product-card-footer">
          <span className="price">{formatPrice(product.price)}</span>
          <SizeRow inStock={inStock} low={low} chosen={size} />
          {size ? (
            <span className={quantity <= LOW_STOCK ? 'stock-note low' : 'stock-note'}>
              Size {size}: {stockLabel(quantity)}
            </span>
          ) : (
            <span className="sr-only">{sizesNote(inStock)}</span>
          )}
        </div>
      </div>
    </Link>
  )
}

/** XS to XXL as small boxes: in stock, low (orange) or sold out (struck through). The card's text says the
 * same for screen readers, so the boxes themselves are hidden from them. */
export function SizeRow({ inStock, low = [], chosen = '' }: { inStock: string[]; low?: string[]; chosen?: string }) {
  return (
    <ul
      className="size-row"
      aria-hidden="true"
      title="Sizes in stock. Orange: only a few left. Crossed out: sold out."
    >
      {SIZE_ORDER.map((label) => {
        const state = !inStock.includes(label) ? 'out' : low.includes(label) ? 'low' : ''
        const className = [state, label === chosen ? 'chosen' : ''].filter(Boolean).join(' ')
        return (
          <li key={label} className={className || undefined}>
            {label}
          </li>
        )
      })}
    </ul>
  )
}

export function ProductCardSkeleton() {
  return (
    <div className="product-card is-loading" aria-hidden="true">
      <div className="product-card-image skeleton" />
      <div className="product-card-body">
        <div className="skeleton skeleton-line short" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line medium" />
      </div>
    </div>
  )
}
