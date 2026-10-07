import { Link, useParams, useSearchParams } from 'react-router'
import { openChat } from '../chat.ts'
import { ArrowLeftIcon, ArrowRightIcon, ChatIcon, PinIcon, ShieldIcon, ShirtIcon } from '../components/Icons.tsx'
import Notice from '../components/Notice.tsx'
import ProductCard from '../components/ProductCard.tsx'
import {
  FULL_STOCK,
  LOW_STOCK,
  formatPrice,
  quantityIn,
  sizesInStock,
  stockLabel,
  swatchFor,
  toSize,
} from '../format.ts'
import { useProduct, useProducts } from '../hooks.ts'

export default function ProductPage() {
  const { productId = '' } = useParams()
  const { state, retry } = useProduct(productId)
  const { products } = useProducts()
  // The size picked with the Products page's size filter, if any (?size=M).
  const [params] = useSearchParams()
  const size = toSize(params.get('size'))

  if (state.status === 'loading') return <ProductDetailSkeleton />

  if (state.status === 'not-found' || state.status === 'error') {
    const notFound = state.status === 'not-found'
    return (
      <div className="container page">
        <title>{`${notFound ? 'Product not found' : 'Product unavailable'} | Campus Customs`}</title>
        <Notice
          title={notFound ? "We couldn't find that product" : "We couldn't load this product"}
          action={
            notFound ? (
              <Link to="/products" className="button button-primary">
                Browse all products
              </Link>
            ) : (
              <button type="button" className="button button-primary" onClick={retry}>
                Try again
              </button>
            )
          }
        >
          {notFound
            ? 'It may have been removed, or the link may be mistyped.'
            : 'Check that the backend is running, then try again.'}
        </Notice>
      </div>
    )
  }

  const { product } = state
  // Links back to the Products page keep the chosen size.
  const productsLink = size ? `/products?size=${size}` : '/products'
  const categoryLink = `/products?category=${encodeURIComponent(product.category)}${size ? `&size=${size}` : ''}`
  const related = (products ?? [])
    .filter(
      (p) => p.category === product.category && p.product_id !== product.product_id && (!size || quantityIn(p, size) > 0),
    )
    .slice(0, 4)
  const quantityInSize = size ? quantityIn(product, size) : 0

  return (
    <div className="container page">
      <title>{`${product.name} | Campus Customs`}</title>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to={productsLink}>Products</Link>
        <span aria-hidden="true">›</span>
        <Link to={categoryLink}>{product.category}</Link>
        <span aria-hidden="true">›</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <article className="product-detail">
        <div className="product-detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="product-detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <div className="product-detail-price-row">
            <p className="product-detail-price">{formatPrice(product.price)}</p>
            {size && (
              <p className={`your-size-stock${quantityInSize === 0 ? ' sold-out' : quantityInSize <= LOW_STOCK ? ' low' : ''}`}>
                Your size, {size}: {quantityInSize === 0 ? 'sold out' : stockLabel(quantityInSize).toLowerCase()}
              </p>
            )}
          </div>
          <p className="product-detail-description">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail-block">
              <h2>Colors</h2>
              <ul className="color-list">
                {product.colors.map((color) => (
                  <li key={color}>
                    <span className="swatch" style={{ background: swatchFor(color) }} aria-hidden="true" />
                    {color}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="detail-block">
            <h2>Sizes and stock</h2>
            <ul className="size-grid">
              {product.inventory.map(({ size: label, quantity }) => (
                <li
                  key={label}
                  className={`size${quantity === 0 ? ' sold-out' : quantity <= LOW_STOCK ? ' low' : ''}${label === size ? ' chosen' : ''}`}
                >
                  {label === size && <span className="size-tag">Your size</span>}
                  <span className="size-label">{label}</span>
                  <span className="size-stock">{stockLabel(quantity)}</span>
                  {/* A bar for how much is left: full at FULL_STOCK or more, empty when sold out. */}
                  <span className="stock-meter" aria-hidden="true">
                    <span style={{ width: `${Math.min(quantity / FULL_STOCK, 1) * 100}%` }} />
                  </span>
                </li>
              ))}
            </ul>
            <p className="stock-summary">
              {product.total_stock} in stock across {sizesInStock(product)} of {product.inventory.length} sizes.
            </p>
          </div>

          <div className="detail-actions">
            <button type="button" className="button button-primary" onClick={openChat}>
              <ChatIcon /> Ask about this item
            </button>
            <Link to={productsLink} className="button button-secondary">
              <ArrowLeftIcon /> Back to all products
            </Link>
          </div>

          <ul className="trust-list">
            <li>
              <ShieldIcon /> Officially licensed Yale apparel
            </li>
            <li>
              <PinIcon /> Try it on at our shop, 57 Broadway, New Haven
            </li>
            <li>
              <ShirtIcon /> Every style in XS to XXL, with stock shown for each size
            </li>
          </ul>
        </div>
      </article>

      {related.length > 0 && (
        <section className="related" aria-labelledby="related-title">
          <div className="section-header">
            <h2 id="related-title" className="section-title">
              More {product.category}
              {size && ` in size ${size}`}
            </h2>
            <Link to={categoryLink} className="text-link">
              See all <ArrowRightIcon />
            </Link>
          </div>
          <div className="product-grid">
            {related.map((item) => (
              <ProductCard key={item.product_id} product={item} size={size} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function ProductDetailSkeleton() {
  return (
    <div className="container page" aria-busy="true">
      <div className="breadcrumbs">
        <div className="skeleton skeleton-line short" />
      </div>
      <div className="product-detail">
        <div className="product-detail-image skeleton" />
        <div className="product-detail-info">
          <div className="skeleton skeleton-line short" />
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-line medium" />
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-line" />
        </div>
      </div>
    </div>
  )
}
