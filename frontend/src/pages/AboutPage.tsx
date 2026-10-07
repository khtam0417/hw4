import { Link } from 'react-router'
import VisitCard from '../components/VisitCard.tsx'
import { useProducts } from '../hooks.ts'

const CORNERS = [
  {
    title: 'Residential colleges',
    text: 'Crests and logos for the colleges students call home, from Benjamin Franklin to Trumbull.',
  },
  {
    title: 'Varsity sports',
    text: 'Gear for Bulldog teams, from football and hockey to sailing, squash and fencing.',
  },
  {
    title: 'Graduate and professional schools',
    text: 'Pieces for the Schools of Art, Music and Medicine, Yale Law School and more.',
  },
  {
    title: 'Family and fans',
    text: 'Yale Mom, Dad, Grandma, Grandpa, Aunt and Uncle styles for the people cheering you on.',
  },
]

export default function AboutPage() {
  const { products } = useProducts()

  return (
    <>
      <title>About Us | Campus Customs</title>

      <section className="about-hero">
        <div className="container about-hero-inner">
          <div>
            <p className="eyebrow">About us</p>
            <h1>Yale spirit, sold right on Broadway</h1>
            <p className="page-lead">
              Campus Customs is the team behind Yale Bulldog Blue, a shop for officially licensed Yale apparel and gifts
              at 57 Broadway in New Haven.
            </p>
          </div>
          <dl className="about-facts">
            <div className="fact">
              <dt>Styles online</dt>
              <dd>{products ? products.length : '—'}</dd>
            </div>
            <div className="fact">
              <dt>Sizes in every style</dt>
              <dd>XS–XXL</dd>
            </div>
            <div className="fact">
              <dt>Find us at</dt>
              <dd>57 Broadway</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="section">
        <div className="container about-body">
          <div className="prose">
            <h2 className="section-title">Who we are</h2>
            <p>
              We dress the Yale community. First-years buying their first hoodie, seniors choosing something for
              graduation, alumni back for a reunion and families cheering from the stands all find their way to us, so we
              keep our range wide.
            </p>
            <p>
              On our shelves and on this site you'll find tees, crewnecks, hoodies, quarter-zips and fleece, in classic
              Yale blue and plenty of other colors.
            </p>
            <h2 className="section-title">How we can help</h2>
            <p>
              Every product page lists each size and how many are left, so you can check availability before you visit.
              Questions about an order? Email <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>.
              Our chat assistant, in the bottom-right corner of every page, can check sizes and stock for you
              any time.
            </p>
            <Link to="/products" className="button button-primary">
              Browse the catalogue
            </Link>
          </div>
          <div>
            <h2 className="section-title">Something for every corner of Yale</h2>
            <ul className="feature-list">
              {CORNERS.map(({ title, text }) => (
                <li key={title}>
                  <strong>{title}</strong>
                  <span>{text}</span>
                </li>
              ))}
            </ul>
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
