import { Link } from 'react-router'
import { ArrowRightIcon, PinIcon, ShieldIcon, ShirtIcon } from '../components/Icons.tsx'
import Notice from '../components/Notice.tsx'
import ProductCard, { ProductCardSkeleton } from '../components/ProductCard.tsx'
import VisitCard from '../components/VisitCard.tsx'
import { matchesSearch, pickProducts, summarizeCategories } from '../catalogue.ts'
import { formatPrice } from '../format.ts'
import { useProducts } from '../hooks.ts'

// Most product photos have black backgrounds; the hero and category covers use ones shot on white.
const HERO_IDS = [
  'champion-reverse-weave-hoodie-1',
  'district-vit-crewneck-vintage-bulldog',
  '2025-yale-vs-harvard-t-shirt',
  'district-vit-hoodie-vintage-sailor-bulldog',
]

const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  'boola-boola-t-shirt',
  'yale-mom-crewneck',
  'brooks-brothers-bomber-jacket-yale',
  'davenport-college-crewneck',
  'yale-sports-hoodie-hockey',
  'school-of-art-1-4-zip',
  't-felt-y-heavyweight',
]

const CATEGORY_COVERS: Record<string, string> = {
  Hoodies: 'champion-full-zip-hood',
  Crewnecks: 'district-vit-crewneck-vintage-standing-bulldog',
  'T-Shirts': 'yale-bowl-t-shirt',
  'Quarter-Zips': 'school-of-medicine-1-4-zip',
  'Jackets & Fleece': 'benjamin-franklin-fleece-jacket',
  'Long Sleeves': 'ua-mens-tech-l-s-2-0',
}

const QUICK_SEARCHES = [
  { query: 'bulldog', title: 'Bulldog designs', text: 'Vintage bulldog graphics and other mascot favorites.' },
  { query: 'sports', title: 'Sports teams', text: 'Back the Bulldogs on the field, the court and the water.' },
  { query: 'school', title: 'Graduate & professional schools', text: 'Crests and logos from the School of Art to Yale Law School.' },
  { query: 'fleece', title: 'Fleece & layers', text: 'Warm layers for chilly New Haven days.' },
]

const VALUES = [
  { Icon: ShieldIcon, title: 'Officially licensed', text: 'Yale apparel and gifts made under official license.' },
  { Icon: ShirtIcon, title: 'Six sizes, live stock', text: 'Every style runs XS to XXL, with stock shown for each size.' },
  { Icon: PinIcon, title: 'Steps from campus', text: 'Stop by 57 Broadway to try things on in person.' },
]

export default function HomePage() {
  const { products, failed, retry } = useProducts()
  const heroProducts = pickProducts(products, HERO_IDS)
  const featured = pickProducts(products, FEATURED_IDS)
  const categories = products ? summarizeCategories(products) : []

  return (
    <>
      <title>Campus Customs | Yale Bulldog Blue apparel in New Haven</title>

      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow eyebrow-light">Yale Bulldog Blue by Campus Customs</p>
            <h1>
              Bulldog pride you can wear <em>every day.</em>
            </h1>
            <p className="hero-lead">
              Hoodies, crewnecks, tees and quarter-zips for Yale students, alumni, families and fans, from our shop at
              57 Broadway in New Haven.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="button button-light">
                Shop all products <ArrowRightIcon />
              </Link>
              <Link to="/about" className="button button-outline-light">
                Our story
              </Link>
            </div>
          </div>
          <div className="hero-collage">
            {heroProducts.length > 0
              ? heroProducts.map((product) => (
                  <Link key={product.product_id} to={`/products/${product.product_id}`} className="hero-tile">
                    <img src={product.image_url} alt="" />
                    <span className="hero-tile-caption">
                      <span className="hero-tile-name">{product.name}</span>
                      <span className="hero-tile-price">{formatPrice(product.price)}</span>
                    </span>
                  </Link>
                ))
              : HERO_IDS.map((id) => <div key={id} className="hero-tile skeleton" aria-hidden="true" />)}
          </div>
        </div>
      </section>

      <section className="value-strip" aria-label="Why shop with us">
        <div className="container value-grid">
          {VALUES.map(({ Icon, title, text }) => (
            <div key={title} className="value-item">
              <span className="value-icon">
                <Icon />
              </span>
              <div>
                <p className="value-title">{title}</p>
                <p className="value-text">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {failed && (
        <div className="container section-tight">
          <Notice
            title="Products are unavailable right now"
            action={
              <button type="button" className="button button-primary" onClick={retry}>
                Try again
              </button>
            }
          >
            We couldn't reach the product list. Check that the backend is running.
          </Notice>
        </div>
      )}

      <section className="section">
        <div className="container">
          <div className="section-header">
            <div>
              <h2 className="section-title">Shop by category</h2>
              <p className="section-lead">From everyday tees to fleece for cold New Haven mornings.</p>
            </div>
            <Link to="/products" className="text-link">
              View all <ArrowRightIcon />
            </Link>
          </div>
          <div className="category-grid">
            {products
              ? categories.map(({ name, count }) => {
                  const cover =
                    pickProducts(products, [CATEGORY_COVERS[name] ?? ''])[0] ?? products.find((p) => p.category === name)
                  return (
                    <Link key={name} to={`/products?category=${encodeURIComponent(name)}`} className="category-tile">
                      <div className="category-tile-image">{cover && <img src={cover.image_url} alt="" loading="lazy" />}</div>
                      <div className="category-tile-body">
                        <span className="category-tile-name">{name}</span>
                        <span className="category-tile-count">{count} styles</span>
                      </div>
                    </Link>
                  )
                })
              : Object.keys(CATEGORY_COVERS).map((name) => (
                  <div key={name} className="category-tile" aria-hidden="true">
                    <div className="category-tile-image skeleton" />
                    <div className="category-tile-body">
                      <div className="skeleton skeleton-line" />
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <div>
              <h2 className="section-title">Featured styles</h2>
              <p className="section-lead">A mix of everyday classics and game-day favorites to start with.</p>
            </div>
            <Link to="/products" className="text-link">
              Shop all products <ArrowRightIcon />
            </Link>
          </div>
          <div className="product-grid">
            {products
              ? featured.map((product) => <ProductCard key={product.product_id} product={product} />)
              : FEATURED_IDS.slice(0, 4).map((id) => <ProductCardSkeleton key={id} />)}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-header">
            <div>
              <h2 className="section-title">Find your corner of Yale</h2>
              <p className="section-lead">Jump straight to the styles that match your team, your school or your mood.</p>
            </div>
          </div>
          <div className="quick-grid">
            {QUICK_SEARCHES.map(({ query, title, text }) => {
              const count = products?.filter((product) => matchesSearch(product, query)).length
              return (
                <Link key={query} to={`/products?q=${encodeURIComponent(query)}`} className="quick-card">
                  <span className="quick-card-title">{title}</span>
                  <span className="quick-card-text">{text}</span>
                  <span className="quick-card-count">
                    {count === undefined ? 'Browse' : `${count} styles`} <ArrowRightIcon />
                  </span>
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      <section className="section section-tight-top">
        <div className="container">
          <VisitCard />
        </div>
      </section>
    </>
  )
}
