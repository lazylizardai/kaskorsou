import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  MagnifyingGlass, ArrowRight, MapPin, Buildings,
  Waves, SunHorizon, Anchor, Tree,
  ArrowUpRight, Sparkle,
} from '@phosphor-icons/react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { MOCK_LISTINGS } from '../data/mockListings'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const SAND = '#F5F0E8'
const INK = '#09090B'
const DARK = '#0B1120'
const DARK2 = '#111827'

/* Reliable Unsplash – Curaçao aerial beach */
const HERO_IMG = 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&w=1920&q=80'

const slideUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] },
})

function formatPrice(price, type) {
  if (type === 'rent') return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}/mnd`
  if (price >= 1000000) return `ANG ${(price / 1000000).toFixed(1)}M`
  return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}`
}

const NEIGHBORHOODS = [
  { name: 'Jan Thiel', region: 'Oost Curaçao', listings: 68, icon: Waves, color: '#0891B2', img: 'https://images.unsplash.com/photo-1571986237692-cf5b892ad4b9?w=600&q=80' },
  { name: 'Blue Bay', region: 'Zuidwestkust', listings: 41, icon: Anchor, color: '#0284C7', img: 'https://images.unsplash.com/photo-1562016600-ece13e8ba570?w=600&q=80' },
  { name: 'Pietermaai', region: 'Willemstad', listings: 34, icon: Buildings, color: '#7C3AED', img: 'https://images.unsplash.com/photo-1590059915548-18e6a95a8d6b?w=600&q=80' },
  { name: 'Coral Estate', region: 'Rif St. Marie', listings: 22, icon: Tree, color: '#059669', img: 'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=600&q=80' },
  { name: 'Piscadera', region: 'West', listings: 18, icon: SunHorizon, color: CORAL, img: 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&q=80' },
]

const STATS = [
  { value: '1.063', label: 'Actieve woningen' },
  { value: '45+', label: 'Makelaarskantoren' },
  { value: '12', label: 'Wijken gedekt' },
  { value: 'ANG 485K', label: 'Gemiddelde prijs' },
]

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [listingType, setListingType] = useState('sale')
  const navigate = useNavigate()
  const heroRef = useRef(null)

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroImgY = useTransform(scrollYProgress, [0, 1], ['0%', '25%'])

  const handleSearch = (e) => {
    e.preventDefault()
    navigate(`/search?q=${encodeURIComponent(searchQuery)}&type=${listingType}`)
  }

  const featured = MOCK_LISTINGS.filter(l => l.is_featured).slice(0, 3)
  const recent = MOCK_LISTINGS.filter(l => l.is_new).slice(0, 4)

  return (
    <div style={{ background: DARK, color: 'white', fontFamily: 'Geist, system-ui, sans-serif' }}
      className="min-h-[100dvh] overflow-x-hidden">

      {/* ─────────── HERO ─────────── */}
      <section ref={heroRef}
        style={{ paddingTop: 72, minHeight: '62dvh', display: 'flex', alignItems: 'center', position: 'relative', overflow: 'hidden' }}>

        {/* Background image with parallax — using <img> for reliability */}
        <motion.div
          style={{ y: heroImgY, position: 'absolute', inset: '-15% 0 -15%', zIndex: 0 }}>
          <img
            src={HERO_IMG}
            alt="Curaçao strand"
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        </motion.div>

        {/* Dark gradient overlay */}
        <div style={{
          position: 'absolute', inset: 0, zIndex: 1,
          background: 'linear-gradient(to bottom, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.30) 45%, rgba(11,17,32,0.92) 100%)',
        }} />

        {/* Hero content */}
        <div style={{ position: 'relative', zIndex: 2 }}
          className="max-w-[1200px] mx-auto px-5 lg:px-8 w-full py-16">

          <motion.div {...slideUp(0)} className="flex items-center gap-2 mb-5">
            <span style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.22)', color: 'white' }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm">
              <Sparkle size={11} weight="fill" style={{ color: '#FCD34D' }} />
              1.063 woningen op Curaçao
            </span>
          </motion.div>

          <motion.h1 {...slideUp(0.05)}
            style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.05 }}
            className="text-4xl md:text-6xl lg:text-7xl max-w-[680px] mb-5">
            Vind uw thuis<br />
            op <span style={{ color: '#5EEAD4' }}>Curaçao</span>
          </motion.h1>

          <motion.p {...slideUp(0.10)}
            style={{ color: 'rgba(255,255,255,0.72)', maxWidth: 460 }}
            className="text-base md:text-lg leading-relaxed mb-8">
            Van beachfront villa's tot koloniale panden in Willemstad — alle makelaars op één plek.
          </motion.p>

          {/* ── Search box ── */}
          <motion.div {...slideUp(0.15)}>
            <div style={{
              background: 'white', borderRadius: 16,
              boxShadow: '0 24px 48px -12px rgba(0,0,0,0.5)', overflow: 'hidden', maxWidth: 660,
            }}>
              <div style={{ borderBottom: '1px solid #F4F4F5', padding: '10px 16px 0' }} className="flex gap-1">
                {[{ val: 'sale', label: 'Kopen' }, { val: 'rent', label: 'Huren' }].map(({ val, label }) => (
                  <button key={val} onClick={() => setListingType(val)} style={{
                    borderBottom: listingType === val ? `2px solid ${TEAL}` : '2px solid transparent',
                    color: listingType === val ? TEAL : '#71717A',
                    fontWeight: listingType === val ? 600 : 500, paddingBottom: 10,
                  }} className="px-3 text-sm transition-colors">{label}</button>
                ))}
              </div>
              <form onSubmit={handleSearch} className="flex items-center gap-3 p-3">
                <MagnifyingGlass size={20} weight="bold" style={{ color: '#A1A1AA', flexShrink: 0, marginLeft: 8 }} />
                <input type="text" placeholder="Zoek op wijk, adres of type woning..."
                  value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: INK, fontSize: 15 }}
                  className="placeholder:text-zinc-400" />
                <div className="hidden md:flex items-center gap-2 pr-2 border-r border-zinc-100">
                  {['Villa', 'Appartement'].map(t => (
                    <button key={t} type="button" onClick={() => navigate(`/search?type=${t.toLowerCase()}`)}
                      style={{ color: '#52525B', border: '1px solid #E4E4E7', background: 'white' }}
                      className="px-2.5 py-1 rounded-full text-xs font-medium hover:border-teal-500 hover:text-teal-600 transition-colors">{t}</button>
                  ))}
                </div>
                <button type="submit" style={{ background: TEAL, color: 'white', flexShrink: 0 }}
                  className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity">
                  Zoeken <ArrowRight size={14} weight="bold" />
                </button>
              </form>
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-4">
              <span style={{ color: 'rgba(255,255,255,0.45)' }} className="text-xs">Populair:</span>
              {['Jan Thiel', 'Blue Bay', 'Villa pool', 'Pietermaai', 'Beachfront'].map(tag => (
                <Link key={tag} to={`/search?q=${encodeURIComponent(tag)}`}
                  style={{ background: 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.18)', color: 'white' }}
                  className="px-3 py-1 rounded-full text-xs font-medium backdrop-blur-sm hover:bg-white/20 transition-colors">{tag}</Link>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─────────── STATS STRIP ─────────── */}
      <section style={{ background: `linear-gradient(90deg, ${TEAL} 0%, #004D5E 100%)`, padding: '24px 0' }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map(({ value, label }, i) => (
              <motion.div key={label} {...slideUp(i * 0.05)} className="text-center md:text-left">
                <p style={{ fontWeight: 800, letterSpacing: '-0.03em', color: '#5EEAD4' }} className="text-2xl md:text-3xl">{value}</p>
                <p style={{ color: 'rgba(255,255,255,0.6)' }} className="text-sm mt-0.5">{label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── FEATURED LISTINGS ─────────── */}
      <section style={{ padding: '80px 0', background: DARK2 }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8">
          <div className="flex items-end justify-between mb-10">
            <motion.div {...slideUp(0)}>
              <p style={{ color: '#5EEAD4', fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-2">Uitgelichte woningen</p>
              <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-4xl">
                Curatorisch geselecteerd
              </h2>
            </motion.div>
            <motion.div {...slideUp(0.05)}>
              <Link to="/search" style={{ color: '#5EEAD4', fontWeight: 600, border: '1.5px solid rgba(94,234,212,0.4)' }}
                className="hidden md:flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm hover:bg-teal-900/30 transition-colors">
                Alles zien <ArrowRight size={13} weight="bold" />
              </Link>
            </motion.div>
          </div>
          {/* Bento grid: tall left + 2 stacked right */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gridTemplateRows: 'auto auto', gap: 12 }}
            className="hidden md:grid">
            {featured[0] && <motion.div {...slideUp(0)} style={{ gridRow: '1 / 3' }}><FeaturedCard listing={featured[0]} large /></motion.div>}
            {featured[1] && <motion.div {...slideUp(0.08)}><FeaturedCard listing={featured[1]} /></motion.div>}
            {featured[2] && <motion.div {...slideUp(0.14)}><FeaturedCard listing={featured[2]} /></motion.div>}
          </div>
          <div className="md:hidden flex gap-4 overflow-x-auto pb-4 -mx-5 px-5">
            {featured.map(l => (
              <div key={l.id} style={{ minWidth: 280, flexShrink: 0 }}><FeaturedCard listing={l} /></div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── NEIGHBORHOODS ─────────── */}
      <section style={{ padding: '80px 0', background: SAND }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8">
          <div className="flex items-end justify-between mb-10">
            <motion.div {...slideUp(0)}>
              <p style={{ color: CORAL, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-2">Ontdek per wijk</p>
              <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-4xl">
                Curaçao's beste buurten
              </h2>
            </motion.div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
            {NEIGHBORHOODS.map((n, i) => (
              <motion.div key={n.name} {...slideUp(i * 0.05)}>
                <Link to={`/search?neighborhood=${encodeURIComponent(n.name)}`}
                  className="block group relative overflow-hidden rounded-2xl" style={{ aspectRatio: '3/4' }}>
                  <img src={n.img} alt={n.name}
                    style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
                    className="transition-transform duration-700 group-hover:scale-105" />
                  <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.08) 55%)' }} />
                  <div style={{ position: 'absolute', inset: '14px' }}>
                    <div style={{ background: n.color, color: 'white', width: 30, height: 30, borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <n.icon size={14} weight="fill" />
                    </div>
                  </div>
                  <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '14px' }}>
                    <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: 3 }}>{n.region}</p>
                    <p style={{ color: 'white', fontWeight: 700, fontSize: 19, letterSpacing: '-0.02em', lineHeight: 1.1 }}>{n.name}</p>
                    <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 11, marginTop: 3 }}>{n.listings} woningen</p>
                  </div>
                  <div style={{ position: 'absolute', top: 14, right: 14, width: 28, height: 28, borderRadius: '50%', background: 'rgba(255,255,255,0.12)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0, transition: 'opacity 0.2s' }}
                    className="group-hover:opacity-100">
                    <ArrowUpRight size={13} weight="bold" style={{ color: 'white' }} />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── NEW LISTINGS ─────────── */}
      <section style={{ padding: '80px 0', background: DARK }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8">
          <div className="flex items-end justify-between mb-10">
            <motion.div {...slideUp(0)}>
              <p style={{ color: '#5EEAD4', fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-2">Vers binnen</p>
              <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em' }} className="text-3xl md:text-4xl">Nieuw op de markt</h2>
            </motion.div>
            <Link to="/search" style={{ color: '#5EEAD4', fontWeight: 600, border: '1.5px solid rgba(94,234,212,0.4)' }}
              className="hidden md:flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm hover:bg-teal-900/30 transition-colors">
              Alles zien <ArrowRight size={13} weight="bold" />
            </Link>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16 }}>
            {recent.map((listing, i) => (
              <motion.div key={listing.id} {...slideUp(i * 0.07)}>
                <MiniCard listing={listing} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── CTA ─────────── */}
      <section style={{ padding: '80px 0', background: `linear-gradient(135deg, ${TEAL} 0%, #004D5E 100%)` }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8 text-center">
          <motion.div {...slideUp(0)}>
            <p style={{ color: '#5EEAD4', fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-4">Klaar om te zoeken?</p>
            <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-5xl mb-6">
              Ontdek alle woningen<br />op de interactieve kaart
            </h2>
            <Link to="/search" style={{ background: 'white', color: TEAL, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 8 }}
              className="px-8 py-4 rounded-xl text-base hover:opacity-90 transition-opacity">
              Open kaartoverzicht <ArrowRight size={16} weight="bold" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ─────────── FOOTER ─────────── */}
      <footer style={{ background: '#060D18', borderTop: '1px solid rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.45)', padding: '32px 0' }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div style={{ background: TEAL, width: 28, height: 28, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'white', fontWeight: 700, fontSize: 11 }}>K</span>
            </div>
            <span style={{ color: 'white', fontWeight: 700, fontSize: 14 }}>KasKòrsou</span>
          </div>
          <p className="text-xs">© 2026 KasKòrsou — Curaçao real estate aggregator</p>
          <div className="flex gap-4 text-xs">
            <Link to="/search" className="hover:text-white transition-colors">Zoeken</Link>
            <span>Privacy</span>
            <span>Voorwaarden</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeaturedCard({ listing, large }) {
  const [hovered, setHovered] = useState(false)
  const img = listing.images?.[0] || `https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&q=80`

  return (
    <Link to={`/listing/${listing.id}`}
      className="block relative overflow-hidden rounded-2xl group"
      style={{ aspectRatio: large ? '4/5' : '16/9', height: large ? '100%' : 'auto' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}>
      <div style={{
        background: `url(${img}) center/cover`,
        position: 'absolute', inset: 0,
        transform: hovered ? 'scale(1.04)' : 'scale(1)',
        transition: 'transform 0.7s cubic-bezier(0.22,1,0.36,1)',
      }} />
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.05) 55%)' }} />
      <div style={{ position: 'absolute', top: 12, left: 12 }}>
        <span style={{ background: CORAL, color: 'white', fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Uitgelicht
        </span>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: large ? 24 : 16 }}>
        <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 4 }}>
          {listing.neighborhood}
        </p>
        <p style={{ color: 'white', fontWeight: 700, fontSize: large ? 22 : 16, letterSpacing: '-0.02em', lineHeight: 1.2, marginBottom: 8 }}>
          {listing.title}
        </p>
        <div className="flex items-center justify-between">
          <p style={{ color: '#5EEAD4', fontWeight: 700, fontSize: large ? 20 : 15, letterSpacing: '-0.02em' }}>
            {formatPrice(listing.price, listing.listing_type)}
          </p>
          <div className="flex items-center gap-3">
            {listing.bedrooms && <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>{listing.bedrooms} bed</span>}
            {listing.area_sqm && <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: 12 }}>{listing.area_sqm} m²</span>}
          </div>
        </div>
      </div>
    </Link>
  )
}

function MiniCard({ listing }) {
  const [hovered, setHovered] = useState(false)
  const img = listing.images?.[0] || `https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&q=80`

  return (
    <Link to={`/listing/${listing.id}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'block', borderRadius: 14, overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.08)',
        background: '#161F2E',
        boxShadow: hovered ? '0 12px 32px rgba(0,0,0,0.4)' : '0 2px 8px rgba(0,0,0,0.2)',
        transition: 'all 0.25s ease',
        transform: hovered ? 'translateY(-3px)' : 'none',
      }}>
      <div style={{ aspectRatio: '16/10', overflow: 'hidden' }}>
        <img src={img} alt={listing.title}
          style={{ width: '100%', height: '100%', objectFit: 'cover',
            transform: hovered ? 'scale(1.06)' : 'scale(1)', transition: 'transform 0.5s ease' }} />
      </div>
      <div style={{ padding: '14px 16px' }}>
        <p style={{ fontWeight: 700, letterSpacing: '-0.03em', color: 'white', fontSize: 17, marginBottom: 4 }}>
          {formatPrice(listing.price, listing.listing_type)}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
          <MapPin size={11} weight="fill" style={{ color: '#5EEAD4' }} />
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>{listing.neighborhood}</span>
        </div>
        <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13, lineHeight: 1.4, marginBottom: 10 }} className="line-clamp-1">
          {listing.title}
        </p>
        <div style={{ display: 'flex', gap: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
          {listing.bedrooms && <span>{listing.bedrooms} bed</span>}
          {listing.bathrooms && <span>{listing.bathrooms} bad</span>}
          {listing.area_sqm && <span>{listing.area_sqm} m²</span>}
        </div>
      </div>
    </Link>
  )
}
