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

function jitter(d) { return (Math.random() - 0.5) * d }

function getCoords(listing) {
  if (listing.latitude && listing.longitude) return [listing.latitude, listing.longitude]
  const nb = (listing.neighborhood || listing.address || '').toLowerCase()
  for (const [k, c] of Object.entries(NB)) {
    if (nb.includes(k)) return [c[0] + jitter(0.004), c[1] + jitter(0.004)]
  }
  return null
}

function fmtPrice(price, type) {
  if (type === 'rent') return `${Math.round(price / 1000)}k/mnd`
  if (price >= 1000000) return `${(price / 1000000).toFixed(1)}M`
  return `${Math.round(price / 1000)}k`
}

export default function MapView({ listings = [], selectedId, onMarkerClick }) {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const coordsRef = useRef({})
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
          pts.reduce((s, l) => s + l.latitude, 0) / pts.length,
          pts.reduce((s, l) => s + l.longitude, 0) / pts.length,
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

    if (zoom < CLUSTER_ZOOM) {
      // Cluster bubbles per buurt
      clusters.forEach(({ key, items, coords }) => {
        const el = document.createElement('div')
        el.style.cssText = `
          background:#006B7D;color:white;padding:7px 14px;border-radius:20px;
          font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;
          box-shadow:0 2px 10px rgba(0,107,125,0.45);
          border:2px solid rgba(255,255,255,0.6);
          display:flex;align-items:center;gap:5px;white-space:nowrap;
        `
        const badge = document.createElement('span')
        badge.style.cssText = `background:rgba(255,255,255,0.2);border-radius:8px;padding:1px 6px;font-size:11px;`
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
      // Individuele prijs-badges
      listings.forEach((listing) => {
        const coords = getCoords(listing)
        if (!coords) return
        coordsRef.current[listing.id] = coords
        const isSelected = listing.id === selectedId

        const el = document.createElement('div')
        el.style.cssText = `
          background:${isSelected ? '#006B7D' : '#09090b'};
          color:white;padding:5px 11px;border-radius:8px;
          font-size:11px;font-weight:700;font-family:inherit;
          white-space:nowrap;cursor:pointer;
          box-shadow:0 2px 8px rgba(0,0,0,0.28);
          border:2px solid ${isSelected ? 'rgba(255,255,255,0.9)' : 'transparent'};
          transform:${isSelected ? 'scale(1.18)' : 'scale(1)'};
          transition:transform 0.15s ease,background 0.15s ease;
        `
        el.textContent = `ANG ${fmtPrice(listing.price, listing.listing_type)}`
        el.addEventListener('click', () => onMarkerClick?.(listing))
        el.addEventListener('mouseenter', () => {
          el.style.background = '#006B7D'
          el.style.transform = 'scale(1.12)'
        })
        el.addEventListener('mouseleave', () => {
          el.style.background = listing.id === selectedId ? '#006B7D' : '#09090b'
          el.style.transform = listing.id === selectedId ? 'scale(1.18)' : 'scale(1)'
        })

        const m = L.marker(coords, {
          icon: L.divIcon({ html: el, className: '', iconAnchor: [30, 14] }),
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
