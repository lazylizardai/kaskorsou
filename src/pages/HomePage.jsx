import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  MagnifyingGlass, ArrowRight, MapPin, Buildings,
  Waves, SunHorizon, Anchor, Tree,
  ArrowUpRight, Sparkle, Cube,
} from '@phosphor-icons/react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { getListings } from '../lib/supabase'
import { hasActiveScan } from '../lib/scan'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const SAND = '#F5F0E8'
const INK = '#09090B'
const DARK = '#0B1120'
const DARK2 = '#111827'
const GOLD = '#D4A24C'

/* Reliable Unsplash – Curaçao aerial beach */
const HERO_IMG = 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&w=1920&q=80'

// Fallback-foto's per wijk (voor listings zonder bruikbare afbeeldingen)
const NB_IMAGES = {
  'Jan Thiel': 'https://images.unsplash.com/photo-1571986237692-cf5b892ad4b9?w=800&q=80',
  'Blue Bay': 'https://images.unsplash.com/photo-1562016600-ece13e8ba570?w=800&q=80',
  'Blue Bay Golf & Beach Resort': 'https://images.unsplash.com/photo-1562016600-ece13e8ba570?w=800&q=80',
  Pietermaai: 'https://images.unsplash.com/photo-1590059915548-18e6a95a8d6b?w=800&q=80',
  'Coral Estate': 'https://images.unsplash.com/photo-1519046904884-53103b34b206?w=800&q=80',
  Piscadera: 'https://images.unsplash.com/photo-1600596542815-aa3a76832e02?w=800&q=80',
  Salinja: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&q=80',
  Brievengat: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80',
  Mahuma: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=800&q=80',
  'Boca Gentil': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
  'Jan Sofat': 'https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800&q=80',
  'Toni Kunchi': 'https://images.unsplash.com/photo-1600047509358-9dc75507daeb?w=800&q=80',
  'Groot Davelaar': 'https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&q=80',
  Damacor: 'https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=800&q=80',
  'Seru Fortuna': 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&q=80',
  default: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80',
}

function listingImage(listing) {
  let img = listing?.images?.length ? listing.images[0] : null
  if (img && img.startsWith('//')) img = 'https:' + img
  return img || NB_IMAGES[listing?.neighborhood] || NB_IMAGES.default
}

function neighborhoodFallback(listing) {
  return NB_IMAGES[listing?.neighborhood] || NB_IMAGES.default
}

const slideUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] },
})

function formatPrice(price, type) {
  if (!price) return '—'
  if (type === 'rent') return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}/mnd`
  if (price >= 1000000) return `ANG ${(price / 1000000).toFixed(1)}M`
  return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}`
}

const NEIGHBORHOODS = [
  { name: 'Jan Thiel', region: 'Oost Curaçao', icon: Waves, color: '#0891B2', img: NB_IMAGES['Jan Thiel'] },
  { name: 'Blue Bay', region: 'Zuidwestkust', icon: Anchor, color: '#0284C7', img: NB_IMAGES['Blue Bay'] },
  { name: 'Pietermaai', region: 'Willemstad', icon: Buildings, color: '#7C3AED', img: NB_IMAGES.Pietermaai },
  { name: 'Coral Estate', region: 'Rif St. Marie', icon: Tree, color: '#059669', img: NB_IMAGES['Coral Estate'] },
  { name: 'Piscadera', region: 'West', icon: SunHorizon, color: CORAL, img: NB_IMAGES.Piscadera },
]

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [listingType, setListingType] = useState('sale')
  const [featured, setFeatured] = useState([])
  const [recent, setRecent] = useState([])
  const [scanListings, setScanListings] = useState([])
  const [count, setCount] = useState(null)
  const navigate = useNavigate()
  const heroRef = useRef(null)

  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroImgY = useTransform(scrollYProgress, [0, 1], ['0%', '25%'])

  useEffect(() => {
    getListings({ listing_type: 'sale' }).then(data => {
      setCount(data.length)
      const landKeywords = ['kavel', 'land', 'lot', 'grond', 'perceel', 'bouwkavel']
      const notLand = (l) =>
        !landKeywords.some(k => l.title?.toLowerCase().includes(k)) &&
        !landKeywords.includes(l.property_type?.toLowerCase())
      const top = [...data.filter(l => l.images?.length > 0 && l.price > 0 && notLand(l))]
        .sort((a, b) => (b.price || 0) - (a.price || 0))
        .slice(0, 4)
      if (top.length < 4) {
        const fill = data.filter(l => !top.find(t => t.id === l.id)).slice(0, 4 - top.length)
        setFeatured([...top, ...fill])
      } else {
        setFeatured(top)
      }
    }).catch(() => {})

    getListings({}).then(data => {
      const sorted = [...data].sort((a, b) =>
        new Date(b.last_seen_at || b.created_at || 0) - new Date(a.last_seen_at || a.created_at || 0))
      setRecent(sorted.slice(0, 6))
      const scans = data.filter(hasActiveScan).slice(0, 6)
      setScanListings(scans)
    }).catch(() => {})
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    navigate(`/search?q=${encodeURIComponent(searchQuery)}&type=${listingType}`)
  }

  const stats = [
    { value: count ? `${count}+` : '…', label: 'Actieve woningen' },
    { value: '5', label: 'Makelaarsbronnen' },
    { value: '12', label: 'Wijken gedekt' },
    { value: 'Live', label: 'Dagelijks bijgewerkt' },
  ]

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
              {count ? `${count} woningen op Curaçao` : 'Live woningaanbod Curaçao'}
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
            {stats.map(({ value, label }, i) => (
              <motion.div key={label} {...slideUp(i * 0.05)} className="text-center md:text-left">
                <p style={{ fontWeight: 800, letterSpacing: '-0.03em', color: '#FFFFFF' }} className="text-2xl md:text-3xl">{value}</p>
                <p style={{ color: 'rgba(255,255,255,0.75)' }} className="text-sm mt-0.5">{label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── PREMIUM 3D-TOURS ─────────── */}
      {scanListings.length > 0 && (
        <section style={{ padding: '64px 0 56px', background: DARK, position: 'relative', overflow: 'hidden' }}>
          <div style={{
            position: 'absolute', top: '-30%', left: '50%', transform: 'translateX(-50%)',
            width: '60%', height: '120%',
            background: 'radial-gradient(ellipse at center, rgba(212,162,76,0.10) 0%, transparent 60%)',
            pointerEvents: 'none', zIndex: 0,
          }} />
          <div className="max-w-[1200px] mx-auto px-5 lg:px-8" style={{ position: 'relative', zIndex: 1 }}>
            <div className="flex items-end justify-between mb-8">
              <motion.div {...slideUp(0)}>
                <p style={{ color: GOLD, fontWeight: 600, letterSpacing: '0.1em' }}
                  className="text-xs uppercase mb-2 flex items-center gap-1.5">
                  <Cube size={11} weight="fill" />
                  Premium 3D-tours
                </p>
                <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }}
                  className="text-3xl md:text-4xl">
                  Bekijk woningen <span style={{ color: GOLD }}>zonder afspraak</span>
                </h2>
                <p style={{ color: 'rgba(255,255,255,0.55)' }} className="text-sm md:text-base mt-3 max-w-[520px]">
                  Loop fotorealistisch door de woning vanuit je browser — elke kamer, elke hoek, zonder een makelaar te bellen.
                </p>
              </motion.div>
              <motion.div {...slideUp(0.05)}>
                <Link to="/search?scan=1"
                  style={{ color: GOLD, fontWeight: 600, border: '1.5px solid rgba(212,162,76,0.45)' }}
                  className="hidden md:flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm hover:bg-amber-900/20 transition-colors">
                  Alle 3D-tours <ArrowRight size={13} weight="bold" />
                </Link>
              </motion.div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
              {scanListings.slice(0, 4).map((listing, i) => (
                <motion.div key={listing.id} {...slideUp(i * 0.05)}>
                  <Link to={`/listing/${listing.id}`}
                    className="block group relative overflow-hidden rounded-2xl"
                    style={{
                      aspectRatio: '4/5', background: '#0B1120',
                      boxShadow: '0 0 0 1.5px ' + GOLD + ', 0 8px 28px rgba(212,162,76,0.18)',
                    }}>
                    <img src={listingImage(listing)} alt=""
                      onError={(e) => {
                        if (e.currentTarget.dataset.fb !== '1') {
                          e.currentTarget.dataset.fb = '1'
                          e.currentTarget.src = neighborhoodFallback(listing)
                        }
                      }}
                      referrerPolicy="no-referrer"
                      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
                      className="transition-transform duration-700 group-hover:scale-105" />
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(9,9,11,0.92) 0%, rgba(9,9,11,0.20) 50%, transparent 80%)' }} />
                    <div style={{ position: 'absolute', top: 12, left: 12 }}>
                      <span style={{
                        background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
                        color: '#1F1407',
                        boxShadow: '0 2px 6px rgba(212,162,76,0.45), inset 0 1px 0 rgba(255,255,255,0.35)',
                      }}
                        className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-md tracking-wide flex items-center gap-1">
                        <Cube size={10} weight="fill" />3D Tour
                      </span>
                    </div>
                    <div style={{
                      position: 'absolute', top: 12, right: 12, width: 32, height: 32, borderRadius: '50%',
                      background: 'rgba(9,9,11,0.6)', backdropFilter: 'blur(8px)', border: `1px solid ${GOLD}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <ArrowUpRight size={14} weight="bold" style={{ color: GOLD }} />
                    </div>
                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 14 }}>
                      <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 4 }}>
                        {listing.neighborhood || listing.city || 'Curaçao'}
                      </p>
                      <p style={{ color: 'white', fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em', lineHeight: 1.15, marginBottom: 6 }}>
                        {formatPrice(listing.price, listing.listing_type)}
                      </p>
                      <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12, lineHeight: 1.3 }} className="line-clamp-1">
                        {listing.title}
                      </p>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ─────────── FEATURED LISTINGS ─────────── */}
      <section style={{ padding: '80px 0', background: DARK2 }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8">
          <div className="flex items-end justify-between mb-10">
            <motion.div {...slideUp(0)}>
              <p style={{ color: '#5EEAD4', fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-2">Uitgelichte woningen</p>
              <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-4xl">
                Dagelijks bijgewerkt
              </h2>
            </motion.div>
            <motion.div {...slideUp(0.05)}>
              <Link to="/search" style={{ color: '#5EEAD4', fontWeight: 600, border: '1.5px solid rgba(94,234,212,0.4)' }}
                className="hidden md:flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm hover:bg-teal-900/30 transition-colors">
                Alles zien <ArrowRight size={13} weight="bold" />
              </Link>
            </motion.div>
          </div>
          {/* Bento grid: tall left + 3 stacked right */}
          {featured.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gridTemplateRows: 'repeat(3, 1fr)', gap: 10, height: 620 }}
              className="hidden md:grid">
              {featured[0] && (
                <motion.div {...slideUp(0)} style={{ gridRow: '1 / 4', gridColumn: '1' }}>
                  <FeaturedCard listing={featured[0]} large />
                </motion.div>
              )}
              {featured[1] && (
                <motion.div {...slideUp(0.07)} style={{ gridRow: '1', gridColumn: '2', height: '100%' }}>
                  <FeaturedCard listing={featured[1]} />
                </motion.div>
              )}
              {featured[2] && (
                <motion.div {...slideUp(0.12)} style={{ gridRow: '2', gridColumn: '2', height: '100%' }}>
                  <FeaturedCard listing={featured[2]} />
                </motion.div>
              )}
              {featured[3] && (
                <motion.div {...slideUp(0.17)} style={{ gridRow: '3', gridColumn: '2', height: '100%' }}>
                  <FeaturedCard listing={featured[3]} />
                </motion.div>
              )}
            </div>
          ) : (
            <div style={{ height: 620, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              className="hidden md:flex">
              <p style={{ color: 'rgba(255,255,255,0.3)' }}>Woningen laden…</p>
            </div>
          )}
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
            {recent.length > 0
              ? recent.map((listing, i) => (
                  <motion.div key={listing.id} {...slideUp(i * 0.07)}>
                    <MiniCard listing={listing} />
                  </motion.div>
                ))
              : Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} style={{ height: 260, borderRadius: 14, background: '#161F2E', opacity: 0.4 }} />
                ))}
          </div>
        </div>
      </section>

      {/* ─────────── CTA ─────────── */}
      <section style={{ padding: '80px 0', background: `linear-gradient(135deg, ${TEAL} 0%, #004D5E 100%)` }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8 text-center">
          <motion.div {...slideUp(0)}>
            <p style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-4">Klaar om te zoeken?</p>
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
  const [img, setImg] = useState(() => listingImage(listing))
  const onImgError = () => {
    setImg(NB_IMAGES[listing?.neighborhood] || NB_IMAGES.default)
  }

  return (
    <Link to={`/listing/${listing.id}`}
      className="block relative overflow-hidden rounded-2xl group"
      style={{ width: '100%', height: '100%' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}>
      <img src={img} alt={listing.title} onError={onImgError}
        style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          objectFit: 'cover', objectPosition: 'center',
          transform: hovered ? 'scale(1.04)' : 'scale(1)',
          transition: 'transform 0.7s cubic-bezier(0.22,1,0.36,1)',
        }} />
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.80) 0%, rgba(0,0,0,0.05) 55%)' }} />
      <div style={{ position: 'absolute', top: 12, left: 12 }}>
        <span style={{ background: CORAL, color: 'white', fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Uitgelicht
        </span>
      </div>
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: large ? 24 : 14 }}>
        {listing.neighborhood && (
          <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 4 }}>
            {listing.neighborhood}
          </p>
        )}
        <p style={{ color: 'white', fontWeight: 700, fontSize: large ? 22 : 15, letterSpacing: '-0.02em', lineHeight: 1.2, marginBottom: 8 }}
          className="line-clamp-2">
          {listing.title}
        </p>
        <div className="flex items-center justify-between">
          <p style={{ color: '#5EEAD4', fontWeight: 700, fontSize: large ? 20 : 14, letterSpacing: '-0.02em' }}>
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
  const [img, setImg] = useState(() => listingImage(listing))

  return (
    <Link to={`/listing/${listing.id}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'block', borderRadius: 14, overflow: 'hidden',
        border: '1px solid rgba(255,255,255,0.08)',
        background: '#161F2E',
        boxShadow: hovered
          ? 'inset 0 1px 0 rgba(255,255,255,0.05), 0 12px 32px rgba(0,0,0,0.4)'
          : 'inset 0 1px 0 rgba(255,255,255,0.05), 0 2px 8px rgba(0,0,0,0.2)',
        transition: 'background-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease',
        transform: hovered ? 'translateY(-3px)' : 'none',
      }}>
      <div style={{ aspectRatio: '16/10', overflow: 'hidden' }}>
        <img src={img} alt={listing.title}
          onError={() => setImg(NB_IMAGES[listing?.neighborhood] || NB_IMAGES.default)}
          style={{ width: '100%', height: '100%', objectFit: 'cover',
            transform: hovered ? 'scale(1.06)' : 'scale(1)', transition: 'transform 0.5s ease' }} />
      </div>
      <div style={{ padding: '14px 16px' }}>
        <p style={{ fontWeight: 700, letterSpacing: '-0.03em', color: 'white', fontSize: 17, marginBottom: 4 }}>
          {formatPrice(listing.price, listing.listing_type)}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
          <MapPin size={11} weight="fill" style={{ color: '#5EEAD4' }} />
          <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>{listing.neighborhood || listing.source_id}</span>
        </div>
        <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13, lineHeight: 1.4, marginBottom: 10 }} className="line-clamp-1">
          {listing.title}
        </p>
        <div style={{ display: 'flex', gap: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
          {listing.bedrooms && <span>{listing.bedrooms} bed</span>}
          {listing.bathrooms && <span>{listing.bathrooms} bad</span>}
          {listing.area_sqm && <span>{listing.area_sqm} m²</span>}
          {!listing.bedrooms && !listing.area_sqm && (
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>{listing.source_id}</span>
          )}
        </div>
      </div>
    </Link>
  )
}
