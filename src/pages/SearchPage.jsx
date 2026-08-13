import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  MagnifyingGlass, Sliders, MapTrifold, List, X,
  SortAscending, CaretDown, Globe, Storefront,
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import FilterSidebar from '../components/FilterSidebar'
import ListingCard from '../components/ListingCard'
import MapView from '../components/MapView'
import { getListings } from '../lib/supabase'
import { hasActiveScan } from '../lib/scan'
import { toUSD } from '../lib/currency'
import { useIsMobile } from '../lib/useIsMobile'

const TEAL = '#006B7D'
const INK = '#09090B'

const SORT_OPTIONS = [
  { value: 'default', label: 'Standaard' },
  { value: 'price_asc', label: 'Prijs laag–hoog' },
  { value: 'price_desc', label: 'Prijs hoog–laag' },
  { value: 'newest', label: 'Nieuwste eerst' },
]

function BuyRentToggle({ value, onChange }) {
  return (
    <div style={{ background: '#F4F4F5', padding: 3 }} className="flex items-center rounded-lg">
      {['Kopen', 'Huren'].map((label) => {
        const val = label === 'Kopen' ? 'sale' : 'rent'
        const active = value === val
        return (
          <button key={val} onClick={() => onChange(val)}
            style={{
              background: active ? 'white' : 'transparent',
              color: active ? INK : '#71717A',
              fontWeight: active ? 600 : 500,
              boxShadow: active ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              transition: 'background-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease',
            }}
            className="px-4 py-1.5 rounded-md text-sm">
            {label}
          </button>
        )
      })}
    </div>
  )
}

export default function SearchPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const isMobile = useIsMobile()
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [hoveredId, setHoveredId] = useState(null)
  const [view, setView] = useState(() => {
    const v = searchParams.get('view')
    const requested = ['split', 'list', 'map'].includes(v) ? v : 'split'
    // 'split' (twee kolommen naast elkaar) past niet op een telefoonscherm —
    // begin daar altijd met de lijst, ook als de URL split expliciet vraagt.
    if (typeof window !== 'undefined' && window.innerWidth < 768 && requested === 'split') return 'list'
    return requested
  })
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [sortOpen, setSortOpen] = useState(false)
  const [sort, setSort] = useState('default')
  const [filters, setFilters] = useState(() => ({
    listingType: 'sale', priceMin: 0, priceMax: 2500000,
    bedrooms: 0, bathrooms: 0, type: '', neighborhood: searchParams.get('neighborhood') || '',
    searchQuery: searchParams.get('q') || '',
    scanOnly: searchParams.get('scan') === '1',
    source: searchParams.get('source') || '',
  }))
  const [sourceLabel] = useState(() => searchParams.get('sourceLabel') || '')

  const sortRef = useRef(null)
  const cardRefs = useRef({})        // { [listing.id]: DOM element }
  const cardsContainerRef = useRef(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const data = await getListings()
      setListings(data)
      setLoading(false)
    }
    load()
  }, [])

  useEffect(() => {
    function handleClick(e) {
      if (sortRef.current && !sortRef.current.contains(e.target)) setSortOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Vangnet: als het venster tijdens de sessie smaller wordt dan 768px terwijl
  // 'split' actief staat (bv. tablet die gedraaid wordt), val terug op lijst.
  useEffect(() => {
    if (isMobile && view === 'split') setView('list')
  }, [isMobile, view])

  const filtered = useMemo(() => {
    let result = listings.filter((l) => {
      if (l.listing_type !== filters.listingType) return false
      // Filterbereik is altijd USD — reken de listing-prijs (kan XCG of USD
      // zijn) om zodat XCG-huizen ook correct meetellen.
      const priceUSD = toUSD(l.price, l.currency)
      if (priceUSD < filters.priceMin || priceUSD > filters.priceMax) return false
      if (filters.bedrooms && l.bedrooms < filters.bedrooms) return false
      if (filters.type && l.property_type !== filters.type) return false
      if (filters.neighborhood && l.neighborhood !== filters.neighborhood) return false
      if (filters.source && l.source_id !== filters.source) return false
      if (filters.scanOnly && !hasActiveScan(l)) return false
      if (filters.searchQuery) {
        const q = filters.searchQuery.toLowerCase()
        const s = `${l.title} ${l.neighborhood} ${l.address || ''}`.toLowerCase()
        if (!s.includes(q)) return false
      }
      return true
    })
    if (sort === 'price_asc') result = [...result].sort((a, b) => toUSD(a.price, a.currency) - toUSD(b.price, b.currency))
    else if (sort === 'price_desc') result = [...result].sort((a, b) => toUSD(b.price, b.currency) - toUSD(a.price, a.currency))
    else if (sort === 'newest') result = [...result].filter(l => l.is_new).concat(result.filter(l => !l.is_new))
    else {
      // Standaard: actieve 3D-scans eerst, dan uitgelicht, dan op quality_score
      result = [...result].sort((a, b) => {
        const aScan = hasActiveScan(a) ? 1 : 0
        const bScan = hasActiveScan(b) ? 1 : 0
        if (aScan !== bScan) return bScan - aScan
        if (a.is_featured !== b.is_featured) return (b.is_featured ? 1 : 0) - (a.is_featured ? 1 : 0)
        return (b.quality_score || 0) - (a.quality_score || 0)
      })
    }
    return result
  }, [listings, filters, sort])

  // "Bekijk details →" in de kaart-popup → naar de listingpagina navigeren.
  // Was eerder alleen een lijst-selectie zonder navigatie, waardoor de knop
  // niets leek te doen.
  const handleMarkerClick = useCallback((listing) => {
    navigate(`/listing/${listing.id}`)
  }, [navigate])

  const activeFilterCount = [
    filters.type, filters.neighborhood, filters.source,
    filters.bedrooms > 0 && '1',
    filters.priceMin > 0 && '1',
    filters.priceMax < 2500000 && '1',
  ].filter(Boolean).length

  const clearSourceFilter = useCallback(() => {
    setFilters(f => ({ ...f, source: '' }))
    const next = new URLSearchParams(searchParams)
    next.delete('source')
    next.delete('sourceLabel')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  return (
    <div style={{ paddingTop: '72px', height: '100dvh', display: 'flex', flexDirection: 'column' }}>

      {/* ── Toolbar ── */}
      <div style={{
        background: 'white', borderBottom: '1px solid #E4E4E7', height: 56,
        display: 'flex', alignItems: 'center', gap: 12, padding: '0 16px',
        flexShrink: 0, position: 'sticky', top: 72, zIndex: 30,
      }}>
        <BuyRentToggle value={filters.listingType} onChange={(v) => setFilters(f => ({ ...f, listingType: v }))} />

        <div className="flex-1 hidden sm:flex items-center gap-2 max-w-[320px]"
          style={{ background: '#F4F4F5', borderRadius: 8, padding: '6px 12px' }}>
          <MagnifyingGlass size={14} weight="bold" style={{ color: '#A1A1AA', flexShrink: 0 }} />
          <input placeholder="Wijk, adres, referentie..."
            value={filters.searchQuery}
            onChange={(e) => setFilters(f => ({ ...f, searchQuery: e.target.value }))}
            style={{ background: 'transparent', border: 'none', outline: 'none', color: INK, width: '100%' }}
            className="text-sm placeholder:text-zinc-400" />
          {filters.searchQuery && (
            <button onClick={() => setFilters(f => ({ ...f, searchQuery: '' }))}>
              <X size={13} style={{ color: '#A1A1AA' }} />
            </button>
          )}
        </div>

        <button onClick={() => setFiltersOpen(true)}
          style={{
            border: activeFilterCount ? `1.5px solid ${TEAL}` : '1px solid #E4E4E7',
            color: activeFilterCount ? TEAL : '#3F3F46',
            background: activeFilterCount ? '#E6F2F4' : 'white',
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all">
          <Sliders size={14} weight={activeFilterCount ? 'bold' : 'regular'} />
          Filters
          {activeFilterCount > 0 && (
            <span style={{ background: TEAL, color: 'white' }}
              className="w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </button>

        <div className="relative" ref={sortRef}>
          <button onClick={() => setSortOpen(o => !o)} aria-label="Sorteren"
            style={{ border: '1px solid #E4E4E7', color: '#3F3F46' }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-white">
            <SortAscending size={14} />
            <span className="hidden md:inline">{SORT_OPTIONS.find(o => o.value === sort)?.label}</span>
            <CaretDown size={11} style={{ color: '#A1A1AA' }} />
          </button>
          <AnimatePresence>
            {sortOpen && (
              <motion.div initial={{ opacity: 0, y: -4, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.97 }} transition={{ duration: 0.12 }}
                style={{ top: 'calc(100% + 6px)', right: 0, background: 'white', border: '1px solid #E4E4E7', borderRadius: 10, minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.1)' }}
                className="absolute z-50 overflow-hidden">
                {SORT_OPTIONS.map(opt => (
                  <button key={opt.value} onClick={() => { setSort(opt.value); setSortOpen(false) }}
                    style={{ background: sort === opt.value ? '#E6F2F4' : 'transparent', color: sort === opt.value ? TEAL : '#3F3F46', fontWeight: sort === opt.value ? 600 : 400 }}
                    className="w-full text-left px-4 py-2.5 text-sm hover:bg-zinc-50 transition-colors">
                    {opt.label}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <span style={{ color: '#71717A', marginLeft: 'auto' }} className="text-sm hidden sm:block">
          <span style={{ color: INK, fontWeight: 600 }}>{filtered.length}</span> woningen
        </span>

        {/* Desktop view toggle */}
        <div style={{ background: '#F4F4F5', padding: 3 }} className="hidden md:flex items-center rounded-lg">
          {[
            { key: 'split', icon: <span className="text-[11px] font-bold">⊟</span>, label: 'Split' },
            { key: 'list', icon: <List size={14} />, label: 'Lijst' },
            { key: 'map', icon: <MapTrifold size={14} />, label: 'Kaart' },
          ].map(({ key, icon, label }) => (
            <button key={key} onClick={() => setView(key)}
              style={{ background: view === key ? 'white' : 'transparent', color: view === key ? INK : '#71717A', fontWeight: view === key ? 600 : 500, boxShadow: view === key ? '0 1px 3px rgba(0,0,0,0.08)' : 'none', transition: 'background-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease' }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs">
              {icon} {label}
            </button>
          ))}
          <button onClick={() => navigate('/kaart')} aria-label="Open de 3D-kaart van Curaçao"
            style={{ color: TEAL, fontWeight: 600, transition: 'background-color 0.15s ease, color 0.15s ease' }}
            className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs hover:bg-white">
            <Globe size={14} weight="fill" /> 3D
          </button>
        </div>
      </div>

      {/* ── Makelaar-filter banner ── */}
      {filters.source && (
        <div style={{
          background: '#E6F2F4', borderBottom: '1px solid #CFE6E9',
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', flexShrink: 0,
        }}>
          <Storefront size={15} weight="fill" style={{ color: TEAL, flexShrink: 0 }} />
          <span style={{ color: INK, fontSize: 13 }}>
            Alle listings van <strong>{sourceLabel || filters.source}</strong>
          </span>
          <button onClick={clearSourceFilter}
            style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, color: TEAL, fontSize: 12, fontWeight: 600 }}
            className="hover:opacity-80 transition-opacity">
            <X size={12} weight="bold" /> Filter wissen
          </button>
        </div>
      )}

      {/* ── Main content ── */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, position: 'relative' }}>

        {/* Cards kolom */}
        {(view === 'split' || view === 'list') && (
          <div ref={cardsContainerRef}
            style={{
              width: view === 'split' && !isMobile ? '50%' : '100%',
              height: '100%', overflowY: 'auto', background: '#FAFAFA',
              borderRight: view === 'split' && !isMobile ? '1px solid #E4E4E7' : 'none', flexShrink: 0,
            }}>
            <div style={{ padding: '16px', display: 'grid', gap: 12,
              gridTemplateColumns: view === 'list'
                ? 'repeat(auto-fill, minmax(260px, 1fr))'
                : 'repeat(auto-fill, minmax(240px, 1fr))',
            }}>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-white rounded-2xl overflow-hidden border border-zinc-100 animate-pulse">
                      <div style={{ aspectRatio: '4/3', background: '#E4E4E7' }} />
                      <div className="p-4 space-y-2">
                        <div style={{ height: 20, background: '#E4E4E7', borderRadius: 6, width: '60%' }} />
                        <div style={{ height: 14, background: '#F4F4F5', borderRadius: 6, width: '80%' }} />
                      </div>
                    </div>
                  ))
                : filtered.length === 0
                  ? (
                    <div className="col-span-full py-20 text-center">
                      <MapTrifold size={40} style={{ color: '#D4D4D8', margin: '0 auto 12px' }} />
                      <p style={{ color: '#71717A', fontWeight: 500 }}>Geen woningen gevonden</p>
                      <button onClick={() => setFilters(f => ({ ...f, type: '', neighborhood: '', bedrooms: 0, priceMin: 0, priceMax: 2500000 }))}
                        style={{ color: TEAL, fontWeight: 600, marginTop: 12 }} className="text-sm hover:underline">
                        Filters wissen
                      </button>
                    </div>
                  )
                  : filtered.map((listing) => (
                    <div key={listing.id}
                      ref={el => { cardRefs.current[listing.id] = el }}
                      onMouseEnter={() => setHoveredId(listing.id)}
                      onMouseLeave={() => setHoveredId(null)}>
                      <ListingCard
                        listing={listing}
                        highlighted={hoveredId === listing.id}
                      />
                    </div>
                  ))
              }
            </div>
          </div>
        )}

        {/* Map kolom */}
        {(view === 'split' || view === 'map') && (
          <div style={{ flex: 1, height: '100%', overflow: 'hidden' }}>
            <MapView
              key={view}
              listings={filtered}
              selectedId={hoveredId}
              onMarkerClick={handleMarkerClick}
            />
          </div>
        )}
      </div>

      {/* ── Mobile floating map/list toggle ── */}
      <motion.button
        className="flex md:hidden fixed z-[1000]"
        style={{
          bottom: 24, left: '50%', transform: 'translateX(-50%)',
          background: INK, color: 'white',
          padding: '12px 28px', borderRadius: 999,
          boxShadow: '0 8px 24px rgba(0,0,0,0.28)',
          alignItems: 'center', gap: 8,
          fontSize: 14, fontWeight: 600,
        }}
        whileTap={{ scale: 0.94 }}
        onClick={() => setView(v => v === 'map' ? 'list' : 'map')}
      >
        {view === 'map'
          ? <><List size={16} weight="bold" /> Lijst</>
          : <><MapTrifold size={16} weight="bold" /> Kaart</>
        }
      </motion.button>

      {/* ── Filter drawer ── */}
      <AnimatePresence>
        {filtersOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setFiltersOpen(false)}
              style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', zIndex: 50 }} />
            <motion.div
              initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 34 }}
              style={{
                position: 'fixed', top: 0, left: 0, bottom: 0,
                width: 340, maxWidth: '90vw', background: 'white', zIndex: 51,
                boxShadow: '4px 0 24px rgba(0,0,0,0.12)',
                display: 'flex', flexDirection: 'column',
              }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #E4E4E7' }}>
                <span style={{ fontWeight: 700, color: INK }}>Filters</span>
                <button onClick={() => setFiltersOpen(false)} style={{ color: '#71717A' }} className="hover:text-zinc-900">
                  <X size={20} weight="bold" />
                </button>
              </div>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <FilterSidebar filters={filters} onFilterChange={setFilters} resultCount={filtered.length} />
              </div>
              <div style={{ padding: '16px 20px', borderTop: '1px solid #E4E4E7' }}>
                <button onClick={() => setFiltersOpen(false)}
                  style={{ background: TEAL, color: 'white', width: '100%' }}
                  className="py-3 rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity">
                  {filtered.length} woningen tonen
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
