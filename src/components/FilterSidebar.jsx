import { useState, useCallback } from 'react'
import { Sliders, CaretDown, ArrowCounterClockwise, MagnifyingGlass } from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const INK = '#09090B'

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

const PRICE_PRESETS = [
  { label: '< ANG 250k', min: 0, max: 250000 },
  { label: 'ANG 250k – 500k', min: 250000, max: 500000 },
  { label: 'ANG 500k – 1M', min: 500000, max: 1000000 },
  { label: 'ANG 1M+', min: 1000000, max: 10000000 },
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

function PriceSlider({ label, min, max, value, onChange }) {
  const pct = ((value - min) / (max - min)) * 100
  const fmt = (v) => v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : `${(v / 1000).toFixed(0)}k`
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ color: '#71717A', fontSize: 12 }}>{label}</span>
        <span style={{ color: TEAL, fontWeight: 600, fontSize: 12 }}>ANG {fmt(value)}</span>
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
  const handleReset = () => {
    onFilterChange({
      listingType: filters.listingType,
      priceMin: 0, priceMax: 5000000,
      bedrooms: 0, bathrooms: 0,
      type: '', neighborhood: '', searchQuery: '',
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

      {/* Price */}
      <FilterSection title="Prijs">
        <PriceSlider label="Minimum" min={0} max={5000000} value={filters.priceMin || 0}
          onChange={(v) => onFilterChange({ ...filters, priceMin: v })} />
        <PriceSlider label="Maximum" min={0} max={5000000} value={filters.priceMax || 5000000}
          onChange={(v) => onFilterChange({ ...filters, priceMax: v })} />
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
                transition: 'all 0.15s',
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
                  transition: 'all 0.15s',
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
                  transition: 'all 0.15s',
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
                  transition: 'all 0.12s',
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
