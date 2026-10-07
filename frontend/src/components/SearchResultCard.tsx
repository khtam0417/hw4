import { Link } from 'react-router'
import { formatPrice, sizesNote } from '../format.ts'
import type { ProductCard } from '../types.ts'
import { SizeRow } from './ProductCard.tsx'

/** A chat search result on the results page. Opens the product's own page. */
export default function SearchResultCard({ product }: { product: ProductCard }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" decoding="async" />
      </div>
      <div className="product-card-body">
        <p className="eyebrow">{product.category}</p>
        <h3 className="product-card-name">{product.name}</h3>
        <p className="product-card-description">{product.short_description}</p>
        <div className="product-card-footer">
          <span className="price">{formatPrice(product.price)}</span>
          <SizeRow inStock={product.sizes_in_stock} />
          <span className="sr-only">{sizesNote(product.sizes_in_stock)}</span>
        </div>
      </div>
    </Link>
  )
}
