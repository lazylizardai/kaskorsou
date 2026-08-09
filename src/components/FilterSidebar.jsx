import { useState, useCallback } from 'react'
import { Sliders, CaretDown, ArrowCounterClockwise, MagnifyingGlass, Cube } from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { USD_TO_XCG } from '../lib/currency'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const INK = '#09090B'
const GOLD = '#D4A24C'

const PROPERTY_TYPES = [
  { value: 'house', label: 'Huis' },
  { value: 'apartment', label: 'Appartement' },
  { value: 'villa', label: 'Villa' },
  { value: 'condo', label: 'Condo' },
  { value: 'land', label: 'Grond' },
  { value: 'commercial', label: 'Commercieel' },
]

const NEIGHBORHOODS = [
  'Willemstad', 'Jan Thiel', 'Blue Bay', 'Pietermaai', 'Punda',
  'Otrobanda', 'Julianadorp', 'Cas Grandi', 'Santa Rosa', 'Boca Gentil',
  'Coral Estate', 'Piscadera', 'Lagun', 'Westpunt', 'Banda Abou',
]

// Canonieke prijsfilter-eenheid is altijd USD (ongeacht wat er getoond wordt) —
// zo tellen XCG-huizen ook correct mee in een USD-bereik en andersom.
// Vaste koppeling: 1 USD = 1,79 XCG.
const PRICE_SLIDER_MAX_USD = 2500000

const PRICE_PRESETS = [
  { label: '< 150k', min: 0, max: 150000 },
  { label: '150k – 300k', min: 150000, max: 300000 },
  { label: '300k – 600k', min: 300000, max: 600000 },
  { label: '600k+', min: 600000, max: PRICE_SLIDER_MAX_USD },
]

function FilterSection({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ borderBottom: '1px solid #F4F4F5', paddingBottom: 16, marginBottom: 4 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '12px 0', color: INK, fontWeight: 600, fontSize: 13 }}
      >
        {title}
        <CaretDown size={14} weight="bold" style={{ color: '#A1A1AA', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ paddingTop: 8 }}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function PriceSlider({ label, min, max, value, onChange, currency = 'USD' }) {
  const pct = ((value - min) / (max - min)) * 100
  const fmt = (v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : `${(v / 1000).toFixed(0)}k`
  const symbol = currency === 'USD' ? '$' : 'XCG'
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ color: '#71717A', fontSize: 12 }}>{label}</span>
        <span style={{ color: TEAL, fontWeight: 600, fontSize: 12 }}>{symbol} {fmt(value)}</span>
      </div>
      <div style={{ position: 'relative', height: 20, display: 'flex', alignItems: 'center' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, height: 4, background: '#E4E4E7', borderRadius: 99 }} />
        <div style={{ position: 'absolute', left: 0, width: `${pct}%`, height: 4, background: TEAL, borderRadius: 99 }} />
        <input type="range" min={min} max={max} value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={{ position: 'absolute', width: '100%', opacity: 0, cursor: 'pointer', height: 20 }}
        />
        <div style={{ position: 'absolute', left: `${pct}%`, transform: 'translateX(-50%)', width: 18, height: 18, borderRadius: '50%', background: 'white', border: `2.5px solid ${TEAL}`, boxShadow: '0 1px 4px rgba(0,107,125,0.3)', pointerEvents: 'none' }} />
      </div>
    </div>
  )
}

export default function FilterSidebar({ filters, onFilterChange, resultCount }) {
  const [displayCcy, setDisplayCcy] = useState('USD')
  const toDisplay = (usd) => displayCcy === 'USD' ? usd : Math.round(usd * USD_TO_XCG)
  const fromDisplay = (v) => displayCcy === 'USD' ? v : Math.round(v / USD_TO_XCG)

  const handleReset = () => {
    onFilterChange({
      listingType: filters.listingType,
      priceMin: 0, priceMax: PRICE_SLIDER_MAX_USD,
      bedrooms: 0, bathrooms: 0,
      type: '', neighborhood: '', searchQuery: '',
      scanOnly: false,
    })
  }

  return (
    <div style={{ padding: '16px 20px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: INK, fontWeight: 700, fontSize: 14 }}>
          <Sliders size={15} weight="bold" style={{ color: TEAL }} />
          Filters
        </div>
        <button onClick={handleReset}
          style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#71717A', fontSize: 12, fontWeight: 500 }}
          className="hover:text-zinc-900 transition-colors">
          <ArrowCounterClockwise size={12} />
          Reset
        </button>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <MagnifyingGlass size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#A1A1AA' }} />
        <input
          type="text"
          placeholder="Zoek op locatie..."
          value={filters.searchQuery || ''}
          onChange={(e) => onFilterChange({ ...filters, searchQuery: e.target.value })}
          style={{ width: '100%', paddingLeft: 32, paddingRight: 12, paddingTop: 8, paddingBottom: 8, background: '#F4F4F5', border: '1px solid #E4E4E7', borderRadius: 8, fontSize: 13, color: INK, outline: 'none' }}
        />
      </div>

      {resultCount !== undefined && (
        <p style={{ color: '#71717A', fontSize: 12, marginBottom: 16 }}>
          <span style={{ color: TEAL, fontWeight: 700 }}>{resultCount}</span> woningen gevonden
        </p>
      )}

      {/* 3D-tours toggle */}
      <button
        onClick={() => onFilterChange({ ...filters, scanOnly: !filters.scanOnly })}
        style={{
          width: '100%', marginBottom: 16, padding: '10px 12px', borderRadius: 10,
          border: filters.scanOnly ? `1.5px solid ${GOLD}` : '1px solid #E4E4E7',
          background: filters.scanOnly
            ? 'linear-gradient(135deg, rgba(232,181,71,0.12) 0%, rgba(212,162,76,0.06) 100%)'
            : 'white',
          display: 'flex', alignItems: 'center', gap: 10,
          textAlign: 'left', cursor: 'pointer', transition: 'background-color 0.15s, color 0.15s, border-color 0.15s, transform 0.15s',
        }}>
        <span style={{
          width: 28, height: 28, borderRadius: 7,
          background: filters.scanOnly
            ? 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)'
            : '#F4F4F5',
          color: filters.scanOnly ? '#1F1407' : '#A1A1AA',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, transition: 'background-color 0.15s, color 0.15s, border-color 0.15s, transform 0.15s',
        }}>
          <Cube size={14} weight="fill" />
        </span>
        <span style={{ flex: 1 }}>
          <span style={{ display: 'block', color: INK, fontWeight: 600, fontSize: 13, lineHeight: 1.2 }}>
            Alleen 3D-tours
          </span>
          <span style={{ display: 'block', color: '#71717A', fontSize: 11, marginTop: 2 }}>
            Bekijk woningen zonder afspraak
          </span>
        </span>
        <span style={{
          width: 32, height: 18, borderRadius: 99, position: 'relative',
          background: filters.scanOnly ? GOLD : '#E4E4E7',
          transition: 'background 0.15s', flexShrink: 0,
        }}>
          <span style={{
            position: 'absolute', top: 2, left: filters.scanOnly ? 16 : 2,
            width: 14, height: 14, borderRadius: '50%', background: 'white',
            transition: 'left 0.18s ease', boxShadow: '0 1px 3px rgba(0,0,0,0.18)',
          }} />
        </span>
      </button>

      {/* Price */}
      <FilterSection title="Prijs">
        <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
          {['USD', 'XCG'].map((c) => (
            <button key={c} onClick={() => setDisplayCcy(c)}
              style={{
                flex: 1, padding: '5px 0', borderRadius: 6, fontSize: 11, fontWeight: 600,
                border: displayCcy === c ? `1.5px solid ${TEAL}` : '1px solid #E4E4E7',
                background: displayCcy === c ? '#E6F2F4' : 'white',
                color: displayCcy === c ? TEAL : '#71717A',
                transition: 'background-color 0.15s, color 0.15s, border-color 0.15s',
              }}>
              {c === 'USD' ? '$ USD' : 'XCG'}
            </button>
          ))}
        </div>
        <PriceSlider label="Minimum" min={0} max={toDisplay(PRICE_SLIDER_MAX_USD)}
          value={toDisplay(filters.priceMin || 0)} currency={displayCcy}
          onChange={(v) => onFilterChange({ ...filters, priceMin: fromDisplay(v) })} />
        <PriceSlider label="Maximum" min={0} max={toDisplay(PRICE_SLIDER_MAX_USD)}
          value={toDisplay(filters.priceMax ?? PRICE_SLIDER_MAX_USD)} currency={displayCcy}
          onChange={(v) => onFilterChange({ ...filters, priceMax: fromDisplay(v) })} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
          {PRICE_PRESETS.map((p) => (
            <button key={p.label}
              onClick={() => onFilterChange({ ...filters, priceMin: p.min, priceMax: p.max })}
              style={{
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 500,
                border: '1px solid #E4E4E7',
                background: filters.priceMin === p.min && filters.priceMax === p.max ? '#E6F2F4' : 'white',
                color: filters.priceMin === p.min && filters.priceMax === p.max ? TEAL : '#52525B',
                transition: 'background-color 0.15s, color 0.15s, border-color 0.15s, transform 0.15s',
              }}>
              {p.label}
            </button>
          ))}
        </div>
      </FilterSection>

      {/* Type */}
      <FilterSection title="Type woning">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {PROPERTY_TYPES.map(({ value, label }) => {
            const active = filters.type === value
            return (
              <button key={value}
                onClick={() => onFilterChange({ ...filters, type: active ? '' : value })}
                style={{
                  padding: '8px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                  border: active ? `1.5px solid ${TEAL}` : '1px solid #E4E4E7',
                  background: active ? '#E6F2F4' : 'white',
                  color: active ? TEAL : '#52525B',
                  transition: 'background-color 0.15s, color 0.15s, border-color 0.15s, transform 0.15s',
                }}>
                {label}
              </button>
            )
          })}
        </div>
      </FilterSection>

      {/* Bedrooms */}
      <FilterSection title="Slaapkamers">
        <div style={{ display: 'flex', gap: 6 }}>
          {[0, 1, 2, 3, 4, 5].map((n) => {
            const active = filters.bedrooms === n
            return (
              <button key={n}
                onClick={() => onFilterChange({ ...filters, bedrooms: n })}
                style={{
                  flex: 1, padding: '7px 4px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                  border: active ? `1.5px solid ${TEAL}` : '1px solid #E4E4E7',
                  background: active ? '#E6F2F4' : 'white',
                  color: active ? TEAL : '#52525B',
                  transition: 'background-color 0.15s, color 0.15s, border-color 0.15s, transform 0.15s',
                }}>
                {n === 0 ? 'Alle' : `${n}+`}
              </button>
            )
          })}
        </div>
      </FilterSection>

      {/* Neighborhood */}
      <FilterSection title="Wijk" defaultOpen={false}>
        <div style={{ maxHeight: 200, overflowY: 'auto' }}>
          {NEIGHBORHOODS.map((n) => {
            const active = filters.neighborhood === n
            return (
              <button key={n}
                onClick={() => onFilterChange({ ...filters, neighborhood: active ? '' : n })}
                style={{
                  display: 'block', width: '100%', textAlign: 'left',
                  padding: '7px 10px', borderRadius: 6, fontSize: 12,
                  fontWeight: active ? 600 : 400,
                  background: active ? '#E6F2F4' : 'transparent',
                  color: active ? TEAL : '#52525B',
                  marginBottom: 2,
                  transition: 'background-color 0.12s, color 0.12s, border-color 0.12s',
                }}>
                {n}
              </button>
            )
          })}
        </div>
      </FilterSection>
    </div>
  )
}
