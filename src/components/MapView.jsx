import { useEffect, useRef, useState, useMemo } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const CURACAO_CENTER = [12.1696, -68.9900]
const CURACAO_BOUNDS = [[11.90, -69.30], [12.50, -68.60]]
const CLUSTER_ZOOM = 13

const NB = {
  'jan thiel':      [12.0556, -68.8637],
  'blue bay':       [12.1047, -69.0214],
  'pietermaai':     [12.1001, -68.9228],
  'coral estate':   [12.1500, -69.0500],
  'piscadera':      [12.1297, -68.9808],
  'willemstad':     [12.1084, -68.9322],
  'otrobanda':      [12.1076, -68.9369],
  'punda':          [12.1059, -68.9289],
  'seru fortuna':   [12.1200, -68.9500],
  'salina':         [12.0919, -68.8928],
  'saliña':         [12.0919, -68.8928],
  'julianadorp':    [12.1625, -68.9672],
  'jan sofat':      [12.0856, -68.9100],
  'barber':         [12.1800, -69.0500],
  'emmastad':       [12.1100, -68.9200],
  'sabana':         [12.1200, -68.9400],
  'westpunt':       [12.3717, -69.1533],
  'lagun':          [12.3317, -69.1297],
  'mahuma':         [12.1400, -68.9600],
  'bapor kibra':    [12.0850, -68.9050],
  'soto':           [12.2600, -69.0800],
  'rif':            [12.1200, -68.9650],
  'mundo nobo':     [12.1150, -68.9450],
  'brievengat':     [12.1350, -68.9150],
  'scharloo':       [12.1020, -68.9200],
  'groot kwartier': [12.1600, -68.9550],
  'sta catarina':   [12.1750, -68.9700],
  'sta maria':      [12.2300, -69.0300],
  'buena vista':    [12.0900, -68.8800],
  'parasasa':       [12.1600, -69.0100],
  'sun valley':     [12.0820, -68.8900],
  'suffisant':      [12.1050, -68.9250],
  'vredenberg':     [12.1180, -68.9480],
  'rooi catootje':  [12.0700, -68.8600],
  'boca gentil':    [12.0600, -68.8500],
  'santa rosa':     [12.1750, -68.9550],
  'girouette':      [12.1900, -68.9000],
  'cas grandi':     [12.1300, -68.9800],
}

// Island bounding box — filter listings that fall in the sea
const LAT_MIN = 12.01, LAT_MAX = 12.42, LNG_MIN = -69.22, LNG_MAX = -68.75

function jitter(d) { return (Math.random() - 0.5) * d }

function getCoords(listing) {
  if (listing.latitude && listing.longitude) {
    const lat = Number(listing.latitude), lng = Number(listing.longitude)
    // Only use real coords if they're plausibly on the island
    if (lat >= LAT_MIN && lat <= LAT_MAX && lng >= LNG_MIN && lng <= LNG_MAX) {
      return [lat, lng]
    }
  }
  const nb = (listing.neighborhood || listing.address || '').toLowerCase()
  for (const [k, c] of Object.entries(NB)) {
    if (nb.includes(k)) return [c[0] + jitter(0.003), c[1] + jitter(0.003)]
  }
  return null
}

function fmtPrice(price, type) {
  if (!price) return '—'
  const n = Number(price)
  if (type === 'rent') return `ANG ${Math.round(n).toLocaleString()}/mnd`
  if (n >= 1000000) return `ANG ${(n / 1000000).toFixed(2)}M`
  return `ANG ${Math.round(n).toLocaleString()}`
}

function capitalize(s) {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()
}

function buildPopupHTML(listing) {
  const typeLabel = listing.listing_type === 'rent' ? 'Te huur' : 'Te koop'
  const propType = capitalize(listing.property_type || 'Woning')
  const price = fmtPrice(listing.price, listing.listing_type)
  const neighborhood = capitalize(listing.neighborhood || listing.address || '')
  const beds = listing.bedrooms ? `<span style="display:flex;align-items:center;gap:4px">
    <svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor"><path d="M236,112V80a20,20,0,0,0-20-20H40A20,20,0,0,0,20,80v32a12,12,0,0,0-4,22.63V208a12,12,0,0,0,24,0V196H216v12a12,12,0,0,0,24,0V134.63A12,12,0,0,0,236,112ZM44,84H212v28H44ZM216,172H40V160H216Z"/></svg>
    ${listing.bedrooms} slpk
  </span>` : ''
  const baths = listing.bathrooms ? `<span style="display:flex;align-items:center;gap:4px">
    <svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor"><path d="M236,112H212V40a20,20,0,0,0-20-20H100A20,20,0,0,0,80,40V64H44A12,12,0,0,0,32,76V112H20a12,12,0,0,0,0,24h4.29A84.13,84.13,0,0,0,92,210.69V232a12,12,0,0,0,24,0V216h24v16a12,12,0,0,0,24,0V210.69A84.13,84.13,0,0,0,231.71,136H236a12,12,0,0,0,0-24ZM104,44h104V112H104ZM56,88H80v24H56ZM128,196a60,60,0,0,1-59.48-52H187.48A60.09,60.09,0,0,1,128,196Z"/></svg>
    ${listing.bathrooms} badk
  </span>` : ''
  const sqm = listing.area_sqm ? `<span style="display:flex;align-items:center;gap:4px">
    <svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor"><path d="M216,36H40A20,20,0,0,0,20,56V200a20,20,0,0,0,20,20H216a20,20,0,0,0,20-20V56A20,20,0,0,0,216,36Zm-4,160H44V60H212Z"/></svg>
    ${listing.area_sqm} m²
  </span>` : ''

  return `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:200px;max-width:240px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
        <div>
          <div style="font-size:11px;font-weight:600;color:#006B7D;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px">${typeLabel} · ${propType}</div>
          <div style="font-size:17px;font-weight:700;color:#09090b;line-height:1.2">${price}</div>
        </div>
      </div>
      ${neighborhood ? `<div style="font-size:12px;color:#64748b;margin-bottom:8px;display:flex;align-items:center;gap:4px">
        <svg width="12" height="12" viewBox="0 0 256 256" fill="currentColor"><path d="M128,16a96,96,0,1,0,96,96A96.11,96.11,0,0,0,128,16Zm0,168a72,72,0,1,1,72-72A72.08,72.08,0,0,1,128,184Zm0-112a40,40,0,1,0,40,40A40,40,0,0,0,128,72Zm0,56a16,16,0,1,1,16-16A16,16,0,0,1,128,128Z"/></svg>
        ${neighborhood}
      </div>` : ''}
      <div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#374151;margin-bottom:12px">
        ${beds}${baths}${sqm}
      </div>
      <button 
        data-listing-id="${listing.id}"
        style="width:100%;padding:7px 12px;background:#09090b;color:white;border:none;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit"
        onmouseover="this.style.background='#006B7D'"
        onmouseout="this.style.background='#09090b'"
      >Bekijk details →</button>
    </div>
  `
}

// Simple teardrop pin SVG
function makePinIcon(color = '#09090b', size = 28, selected = false) {
  const s = selected ? size * 1.35 : size
  const svg = `<svg width="${s}" height="${s * 1.3}" viewBox="0 0 30 39" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M15 0C6.716 0 0 6.716 0 15c0 10.5 15 24 15 24S30 25.5 30 15C30 6.716 23.284 0 15 0z" fill="${color}"/>
    <circle cx="15" cy="15" r="6" fill="white" fill-opacity="0.9"/>
  </svg>`
  const el = document.createElement('div')
  el.style.cssText = `filter:drop-shadow(0 2px 4px rgba(0,0,0,0.35));cursor:pointer;`
  el.innerHTML = svg
  return el
}

export default function MapView({ listings = [], selectedId, onMarkerClick }) {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const coordsRef = useRef({})
  const activePopupRef = useRef(null)
  const [zoom, setZoom] = useState(11)
  const [ready, setReady] = useState(false)

  // Buurt-clusters voor lage zoom
  const clusters = useMemo(() => {
    if (zoom >= CLUSTER_ZOOM) return []
    const groups = {}
    listings.forEach((l) => {
      const key = (l.neighborhood || 'overig').toLowerCase().split(' ').slice(0, 2).join(' ')
      if (!groups[key]) groups[key] = { key, items: [] }
      groups[key].items.push(l)
    })
    return Object.values(groups).map((g) => {
      let coords = null
      for (const [k, c] of Object.entries(NB)) {
        if (g.key.includes(k) || k.includes(g.key)) { coords = c; break }
      }
      if (!coords) {
        const pts = g.items.filter(l => l.latitude && l.longitude)
        if (pts.length) coords = [
          pts.reduce((s, l) => s + Number(l.latitude), 0) / pts.length,
          pts.reduce((s, l) => s + Number(l.longitude), 0) / pts.length,
        ]
      }
      return { ...g, coords }
    }).filter(g => g.coords)
  }, [listings, zoom])

  // Init map
  useEffect(() => {
    if (mapRef.current) return
    const map = L.map(mapContainer.current, {
      center: CURACAO_CENTER, zoom: 11,
      maxBounds: CURACAO_BOUNDS, maxBoundsViscosity: 0.85,
      zoomControl: false,
    })
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '©OpenStreetMap ©CARTO', subdomains: 'abcd', maxZoom: 19,
    }).addTo(map)
    L.control.zoom({ position: 'topright' }).addTo(map)
    map.on('zoomend', () => setZoom(map.getZoom()))
    mapRef.current = map
    setReady(true)
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // Markers
  useEffect(() => {
    if (!mapRef.current || !ready) return
    markersRef.current.forEach(m => m.remove())
    markersRef.current = []
    if (activePopupRef.current) { activePopupRef.current.remove(); activePopupRef.current = null }

    if (zoom < CLUSTER_ZOOM) {
      // Cluster bubbles per buurt
      clusters.forEach(({ key, items, coords }) => {
        const el = document.createElement('div')
        el.style.cssText = `
          background:#006B7D;color:white;padding:6px 13px;border-radius:20px;
          font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;
          box-shadow:0 2px 10px rgba(0,107,125,0.45);
          border:2px solid rgba(255,255,255,0.6);
          display:flex;align-items:center;gap:5px;white-space:nowrap;
        `
        const badge = document.createElement('span')
        badge.style.cssText = `background:rgba(255,255,255,0.25);border-radius:8px;padding:1px 6px;font-size:11px;`
        badge.textContent = items.length
        const label = document.createElement('span')
        label.textContent = key.charAt(0).toUpperCase() + key.slice(1)
        el.appendChild(badge)
        el.appendChild(label)
        el.addEventListener('click', () => mapRef.current.setView(coords, CLUSTER_ZOOM))
        const m = L.marker(coords, {
          icon: L.divIcon({ html: el, className: '', iconAnchor: [40, 16] }),
        }).addTo(mapRef.current)
        markersRef.current.push(m)
      })
    } else {
      // Individuele pins
      listings.forEach((listing) => {
        const coords = getCoords(listing)
        if (!coords) return
        coordsRef.current[listing.id] = coords
        const isSelected = listing.id === selectedId

        const el = makePinIcon(isSelected ? '#006B7D' : '#09090b', 28, isSelected)

        el.addEventListener('click', (e) => {
          e.stopPropagation()
          // Close existing popup
          if (activePopupRef.current) { activePopupRef.current.remove(); activePopupRef.current = null }

          const popup = L.popup({
            offset: [0, -28],
            closeButton: true,
            className: 'kk-popup',
            maxWidth: 260,
            minWidth: 220,
          })
            .setLatLng(coords)
            .setContent(buildPopupHTML(listing))
            .addTo(mapRef.current)

          activePopupRef.current = popup

          // Wire up the "Bekijk details" button after popup opens
          popup.on('add', () => {
            const btn = popup.getElement()?.querySelector('[data-listing-id]')
            if (btn) btn.addEventListener('click', () => onMarkerClick?.(listing))
          })
        })

        // Hover highlight
        el.addEventListener('mouseenter', () => {
          el.querySelector('path').setAttribute('fill', '#006B7D')
        })
        el.addEventListener('mouseleave', () => {
          el.querySelector('path').setAttribute('fill', isSelected ? '#006B7D' : '#09090b')
        })

        const pinH = isSelected ? 38 : 28
        const m = L.marker(coords, {
          icon: L.divIcon({
            html: el,
            className: '',
            iconAnchor: [pinH * 0.5, pinH * 1.3],
            iconSize: [pinH, pinH * 1.3],
          }),
          zIndexOffset: isSelected ? 1000 : 0,
        }).addTo(mapRef.current)
        markersRef.current.push(m)
      })
    }
  }, [listings, selectedId, zoom, ready, clusters, onMarkerClick])

  // FlyTo geselecteerde listing
  useEffect(() => {
    if (!mapRef.current || !ready || !selectedId) return
    const c = coordsRef.current[selectedId]
    if (c) mapRef.current.flyTo(c, Math.max(mapRef.current.getZoom(), 14), { duration: 0.8 })
  }, [selectedId, ready])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <style>{`
        .kk-popup .leaflet-popup-content-wrapper {
          border-radius: 12px !important;
          box-shadow: 0 8px 32px rgba(0,0,0,0.18) !important;
          padding: 0 !important;
          overflow: hidden;
          border: 1px solid #e2e8f0;
        }
        .kk-popup .leaflet-popup-content {
          margin: 16px !important;
        }
        .kk-popup .leaflet-popup-tip-container {
          margin-top: -2px;
        }
        .kk-popup .leaflet-popup-close-button {
          top: 8px !important;
          right: 8px !important;
          color: #64748b !important;
          font-size: 18px !important;
        }
      `}</style>
      <div ref={mapContainer} style={{ position: 'absolute', inset: 0 }} />
      {!ready && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f1f5f9' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 36, height: 36, border: '3px solid #006B7D', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 12px' }} />
            <p style={{ color: '#64748b', fontSize: 13 }}>Kaart laden…</p>
          </div>
        </div>
      )}
    </div>
  )
}
