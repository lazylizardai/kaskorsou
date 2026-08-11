import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Map as MaplibreMap, Popup as MaplibrePopup, Marker as MaplibreMarker, NavigationControl, addProtocol, setWorkerUrl } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'

// Vite kan maplibre's dynamische worker-URL niet statisch emitten;
// zonder dit serveert de SPA-fallback index.html als worker-script.
setWorkerUrl(maplibreWorkerUrl)
import { Cube, MapPin, Stack, ArrowRight, MapTrifold } from '@phosphor-icons/react'
import { getListings } from '../lib/supabase'
import { hasActiveScan } from '../lib/scan'
import { hasVideoTour, buildVideoStreamUrl } from '../lib/video'
import { useVideoTour } from '../context/VideoTourContext'
import { formatPrice } from '../lib/currency'

const TEAL = '#006B7D'
const INK = '#09090B'

// Eiland-bounds: alleen coördinaten op/rond Curaçao
const LAT_MIN = 11.9, LAT_MAX = 12.45, LNG_MIN = -69.25, LNG_MAX = -68.6
const MAX_BOUNDS = [[-69.35, 11.85], [-68.55, 12.5]]
const ISLAND_CENTER = [-68.93, 12.19]

const SPOTS = [
  { label: 'Willemstad', center: [-68.935, 12.104] },
  { label: 'Jan Thiel', center: [-68.887, 12.077] },
  { label: 'Blue Bay', center: [-69.007, 12.135] },
  { label: 'Westpunt', center: [-69.153, 12.373] },
]

const nf = new Intl.NumberFormat('nl-NL')

function fmtPrice(price, type, currency) {
  return formatPrice(price, currency, type)
}

function esc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

const CUBE_SVG = `<svg width="16" height="16" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M223.68,66.15,135.68,18a15.94,15.94,0,0,0-15.36,0l-88,48.17A16,16,0,0,0,24,80.21v95.58a16,16,0,0,0,8.32,14L120.32,238a15.91,15.91,0,0,0,15.36,0l88-48.17a16,16,0,0,0,8.32-14V80.21A16,16,0,0,0,223.68,66.15ZM128,32l80.34,44L128,120,47.66,76ZM40,90l80,43.78v85.79L40,175.78Zm96,129.57V133.78L216,90v85.78Z"/></svg>`

const HOUSE_SVG = `<svg width="36" height="36" viewBox="0 0 256 256" fill="rgba(255,255,255,0.65)" aria-hidden="true"><path d="M218.83,103.77l-80-75.48a1.14,1.14,0,0,1-.11-.11,16,16,0,0,0-21.53,0l-.11.11L37.17,103.77A16,16,0,0,0,32,115.55V208a16,16,0,0,0,16,16H96a16,16,0,0,0,16-16V160h32v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V115.55A16,16,0,0,0,218.83,103.77ZM208,208H160V160a16,16,0,0,0-16-16H112a16,16,0,0,0-16,16v48H48V115.55l.11-.1L128,40l79.9,75.43.11.1Z"/></svg>`

function popupHTML(p) {
  const price = fmtPrice(p.price, p.listing_type, p.currency)
  const facts = [
    p.bedrooms ? `${p.bedrooms} slpk` : null,
    p.bathrooms ? `${p.bathrooms} badk` : null,
    p.area_sqm ? `${p.area_sqm} m²` : null,
  ].filter(Boolean).join(' · ')
  const media = p.image
    ? `<img src="${esc(p.image)}" alt="" style="width:100%;height:130px;object-fit:cover;display:block" loading="lazy" onerror="this.outerHTML='<div style=&quot;width:100%;height:130px;background:linear-gradient(135deg,#0E4A5C,#06333F);display:flex;align-items:center;justify-content:center&quot;>${HOUSE_SVG.replace(/"/g, '&quot;')}</div>'"/>`
    : `<div style="width:100%;height:130px;background:linear-gradient(135deg,#0E4A5C,#06333F);display:flex;align-items:center;justify-content:center">${HOUSE_SVG}</div>`
  const scanBadge = p.scan === 'true' || p.scan === true
    ? `<div style="position:absolute;top:10px;left:10px;display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#E8B547,#B5862E);color:#1F1407;font-size:11px;font-weight:800;padding:4px 9px;border-radius:99px;box-shadow:0 2px 8px rgba(0,0,0,0.25)">${CUBE_SVG.replace('width="16" height="16"', 'width="11" height="11"')} 3D-tour</div>`
    : ''
  const hasVideo = p.video === 'true' || p.video === true
  const videoBadgeLeft = scanBadge ? 96 : 10
  const videoBadge = hasVideo
    ? `<div style="position:absolute;top:10px;left:${videoBadgeLeft}px;display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#F0805A,#E8672A);color:white;font-size:11px;font-weight:800;padding:4px 9px;border-radius:99px;box-shadow:0 2px 8px rgba(0,0,0,0.25)"><svg width="10" height="10" viewBox="0 0 256 256" fill="currentColor"><path d="M232.4,114.49,88.32,26.35a16,16,0,0,0-16.2-.3A15.86,15.86,0,0,0,64,39.87V216.13A15.94,15.94,0,0,0,80,232a16.07,16.07,0,0,0,8.36-2.35L232.4,141.51a15.81,15.81,0,0,0,0-27ZM80,215.94V40l143.83,88Z"/></svg> Video</div>`
    : ''
  const videoButton = hasVideo
    ? `<button data-kk-video-url="${esc(p.video_url)}"
          style="width:100%;margin-top:8px;padding:9px 12px;background:linear-gradient(135deg,#F0805A,#E8672A);color:white;border:none;border-radius:9px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px">
          <svg width="12" height="12" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M232.4,114.49,88.32,26.35a16,16,0,0,0-16.2-.3A15.86,15.86,0,0,0,64,39.87V216.13A15.94,15.94,0,0,0,80,232a16.07,16.07,0,0,0,8.36-2.35L232.4,141.51a15.81,15.81,0,0,0,0-27ZM80,215.94V40l143.83,88Z"/></svg>
          Video Tour bekijken
        </button>`
    : ''
  return `
    <div style="font-family:Geist,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;width:240px;overflow:hidden;border-radius:14px;background:white">
      <div style="position:relative">${media}${scanBadge}${videoBadge}</div>
      <div style="padding:12px 14px 14px">
        <div style="font-size:17px;font-weight:800;color:${INK};letter-spacing:-0.02em;line-height:1.2">${esc(price)}</div>
        <div style="font-size:12.5px;font-weight:600;color:#3F3F46;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(p.title)}</div>
        ${facts ? `<div style="font-size:11.5px;color:#71717A;margin-top:4px">${esc(facts)}</div>` : ''}
        <button data-kk-id="${esc(p.id)}"
          style="width:100%;margin-top:10px;padding:9px 12px;background:${TEAL};color:white;border:none;border-radius:9px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px">
          Bekijk woning
          <svg width="12" height="12" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M221.66,133.66l-72,72a8,8,0,0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,8,0,0,1,221.66,133.66Z"/></svg>
        </button>
        ${videoButton}
      </div>
    </div>`
}

// Herkleur de liberty-basestyle naar de KasKorsou-identiteit
function applyBrandColors(map) {
  const style = map.getStyle()
  if (!style || !style.layers) return
  for (const layer of style.layers) {
    const id = layer.id
    const sl = layer['source-layer'] || ''
    const name = `${id} ${sl}`.toLowerCase()
    const t = layer.type
    try {
      if (t === 'background') {
        map.setPaintProperty(id, 'background-color', '#F5F0E8')
      } else if (t === 'fill' && /water|ocean|sea/.test(name) && !/waterway|water[-_ ]?name/.test(name)) {
        map.setPaintProperty(id, 'fill-color', [
          'interpolate', ['linear'], ['zoom'],
          7, '#06333F', 10, '#0B4152', 13, '#0E4A5C',
        ])
        map.setPaintProperty(id, 'fill-outline-color', '#0E4A5C')
      } else if (t === 'fill' && /(park|grass|wood|forest|golf|cemetery|garden|scrub|landcover|vegetation)/.test(name)) {
        map.setPaintProperty(id, 'fill-color', '#D3DABE')
        map.setPaintProperty(id, 'fill-opacity', 0.65)
      } else if (t === 'fill' && /(sand|beach)/.test(name)) {
        map.setPaintProperty(id, 'fill-color', '#F0E6CE')
      } else if (t === 'fill' && sl === 'building') {
        map.setPaintProperty(id, 'fill-color', '#E4D9C2')
        map.setPaintProperty(id, 'fill-outline-color', '#D3C5A6')
      } else if (t === 'fill' && /(landuse|residential|industrial|commercial|aeroway|pier)/.test(name)) {
        map.setPaintProperty(id, 'fill-color', '#EFE8D8')
      } else if (t === 'line' && /(waterway|river|stream|canal)/.test(name)) {
        map.setPaintProperty(id, 'line-color', '#2E7C91')
      } else if (t === 'line' && /(motorway|trunk|primary|secondary|tertiary|minor|service|road|street|highway|path|track|transportation|bridge|tunnel|rail)/.test(name)) {
        if (/(casing|outline)/.test(name)) map.setPaintProperty(id, 'line-color', '#DCD1B8')
        else map.setPaintProperty(id, 'line-color', '#FDFBF4')
      } else if (t === 'symbol') {
        if (/water|ocean|sea|marine/.test(name)) {
          map.setPaintProperty(id, 'text-color', '#BFE0E8')
          map.setPaintProperty(id, 'text-halo-color', 'rgba(6,51,63,0.55)')
        } else {
          map.setPaintProperty(id, 'text-color', '#44514F')
          map.setPaintProperty(id, 'text-halo-color', 'rgba(245,240,232,0.92)')
        }
      }
    } catch { /* sommige layers ondersteunen deze property niet — overslaan */ }
  }
}

const PLAY_SVG = `<svg width="14" height="14" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true"><path d="M232.4,114.49,88.32,26.35a16,16,0,0,0-16.2-.3A15.86,15.86,0,0,0,64,39.87V216.13A15.94,15.94,0,0,0,80,232a16.07,16.07,0,0,0,8.36-2.35L232.4,141.51a15.81,15.81,0,0,0,0-27ZM80,215.94V40l143.83,88Z"/></svg>`

function makePinEl() {
  const el = document.createElement('div')
  el.className = 'kk3d-pin'
  el.setAttribute('role', 'button')
  el.setAttribute('tabindex', '0')
  el.setAttribute('aria-label', 'Woning met 3D-tour')
  el.innerHTML = `
    <span class="kk3d-pin-pulse" aria-hidden="true"></span>
    <span class="kk3d-pin-body">${CUBE_SVG}</span>
    <span class="kk3d-pin-tip" aria-hidden="true"></span>`
  return el
}

// Oranje variant voor video-tour-listings (zelfde merkkleur als de Video Tour-badges)
function makeVideoPinEl() {
  const el = document.createElement('div')
  el.className = 'kk3d-pin video-pin'
  el.setAttribute('role', 'button')
  el.setAttribute('tabindex', '0')
  el.setAttribute('aria-label', 'Woning met Video Tour')
  el.innerHTML = `
    <span class="kk3d-pin-pulse" aria-hidden="true"></span>
    <span class="kk3d-pin-body">${PLAY_SVG}</span>
    <span class="kk3d-pin-tip" aria-hidden="true"></span>`
  return el
}

export default function Kaart3DPage() {
  const navigate = useNavigate()
  const { openVideo } = useVideoTour()
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const popupRef = useRef(null)
  const pinMarkersRef = useRef([])
  const videoPinMarkersRef = useRef([])
  const navigateRef = useRef(navigate)
  navigateRef.current = navigate
  const openVideoRef = useRef(openVideo)
  openVideoRef.current = openVideo

  const [listings, setListings] = useState([])
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [mapReady, setMapReady] = useState(false)
  const [is3D, setIs3D] = useState(true)
  const [tourOnly, setTourOnly] = useState(false)
  const [activeSpot, setActiveSpot] = useState(null)

  // Alleen listings met échte coördinaten op het eiland
  const mapListings = useMemo(() =>
    listings.filter(l =>
      l.latitude != null && l.longitude != null &&
      l.latitude >= LAT_MIN && l.latitude <= LAT_MAX &&
      l.longitude >= LNG_MIN && l.longitude <= LNG_MAX
    ), [listings])

  const tourListings = useMemo(() => mapListings.filter(l => hasActiveScan(l)), [mapListings])
  // Video-tour listings zonder 3D-scan krijgen hun eigen oranje pin (net als
  // de gouden 3D-tour-pins) i.p.v. te verdwijnen in de gewone teal-cluster.
  const videoListings = useMemo(() => mapListings.filter(l => !hasActiveScan(l) && hasVideoTour(l)), [mapListings])
  const normalListings = useMemo(() => mapListings.filter(l => !hasActiveScan(l) && !hasVideoTour(l)), [mapListings])

  useEffect(() => {
    let alive = true
    getListings({}).then(data => { if (alive) setListings(data || []) })
    return () => { alive = false }
  }, [])

  const openPopup = useCallback((props, lngLat) => {
    const map = mapRef.current
    if (!map) return
    if (popupRef.current) { popupRef.current.remove(); popupRef.current = null }
    const popup = new MaplibrePopup({
      offset: 20, closeButton: true, maxWidth: '260px', className: 'kk3d-popup',
    })
      .setLngLat(lngLat)
      .setHTML(popupHTML(props))
      .addTo(map)
    popupRef.current = popup
    const btn = popup.getElement()?.querySelector('[data-kk-id]')
    if (btn) btn.addEventListener('click', () => navigateRef.current(`/listing/${props.id}`))
    const videoBtn = popup.getElement()?.querySelector('[data-kk-video-url]')
    if (videoBtn) videoBtn.addEventListener('click', (e) => {
      e.stopPropagation()
      openVideoRef.current({ url: props.video_url, title: props.title })
    })
  }, [])
  const openPopupRef = useRef(openPopup)
  openPopupRef.current = openPopup

  // ── Map init ──
  useEffect(() => {
    if (mapRef.current || !mapEl.current) return
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // Test-hook: in headless test-omgevingen zonder worker-netwerk kunnen
    // tile-requests via de main thread lopen. Nooit actief in productie.
    const tileRelay = window.__KK_TILE_MAIN === true
    if (tileRelay) {
      addProtocol('kkrelay', async ({ url }) => {
        const r = await fetch(url.replace(/^kkrelay:\/\//, 'https://'))
        if (!r.ok) throw new Error(`kkrelay ${r.status}`)
        return { data: await r.arrayBuffer() }
      })
    }

    const map = new MaplibreMap({
      container: mapEl.current,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: reducedMotion ? ISLAND_CENTER : [-68.95, 11.98],
      zoom: reducedMotion ? 11 : 8.5,
      pitch: reducedMotion ? 58 : 0,
      bearing: reducedMotion ? -15 : 0,
      attributionControl: { compact: true },
      transformRequest: tileRelay
        ? (url, type) => (type === 'Tile' && url.startsWith('https://') ? { url: url.replace('https://', 'kkrelay://') } : undefined)
        : undefined,
    })
    mapRef.current = map
    map.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-right')

    const failTimer = setTimeout(() => {
      setStatus(s => (s === 'loading' ? 'error' : s))
    }, 12000)

    if (import.meta.env.DEV) {
      map.on('error', e => console.warn('[kk3d] map error:', e?.error?.message || e))
    }

    map.on('load', () => {
      clearTimeout(failTimer)

      // Merk-kleuren over de liberty-style
      applyBrandColors(map)

      // Terrain (Christoffelberg mag imponeren)
      try {
        map.addSource('kk-terrain', {
          type: 'raster-dem',
          tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
          encoding: 'terrarium',
          tileSize: 256,
          maxzoom: 12,
        })
        map.setTerrain({ source: 'kk-terrain', exaggeration: 2.2 })
      } catch { /* terrain optioneel */ }

      // Sky/atmosfeer voor horizon-diepte
      try {
        map.setSky({
          'sky-color': '#A8D4E0',
          'horizon-color': '#EDF3EE',
          'fog-color': '#DCE9E5',
          'sky-horizon-blend': 0.6,
          'horizon-fog-blend': 0.55,
          'fog-ground-blend': 0.85,
          'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 10, 1, 13, 0.3],
        })
      } catch { /* sky optioneel */ }

      // 3D-gebouwen als de tiles een building-sourcelayer hebben
      try {
        const bl = map.getStyle().layers.find(l => l['source-layer'] === 'building' && l.type === 'fill')
        if (bl) {
          map.addLayer({
            id: 'kk-buildings-3d',
            type: 'fill-extrusion',
            source: bl.source,
            'source-layer': 'building',
            minzoom: 14,
            paint: {
              'fill-extrusion-color': '#DCCFB2',
              'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 8],
              'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
              'fill-extrusion-opacity': 0.82,
            },
          })
        }
      } catch { /* gebouwen optioneel */ }

      setStatus('ready')
      setMapReady(true)

      // Intro-choreografie: van open zee naar het eiland
      if (!reducedMotion) {
        map.flyTo({
          center: ISLAND_CENTER, zoom: 11, pitch: 58, bearing: -15,
          duration: 4000, essential: true,
        })
        map.once('moveend', () => {
          map.setMinZoom(9)
          map.setMaxBounds(MAX_BOUNDS)
        })
      } else {
        map.setMinZoom(9)
        map.setMaxBounds(MAX_BOUNDS)
      }
    })

    return () => {
      clearTimeout(failTimer)
      pinMarkersRef.current.forEach(m => m.remove())
      pinMarkersRef.current = []
      videoPinMarkersRef.current.forEach(m => m.remove())
      videoPinMarkersRef.current = []
      if (popupRef.current) { popupRef.current.remove(); popupRef.current = null }
      map.remove()
      mapRef.current = null
    }
  }, [])

  // ── Data-lagen: geclusterde teal punten ──
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return

    const geojson = {
      type: 'FeatureCollection',
      features: normalListings.map(l => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [l.longitude, l.latitude] },
        properties: {
          id: l.id, title: l.title || 'Woning', price: l.price || 0,
          listing_type: l.listing_type || 'sale',
          bedrooms: l.bedrooms || 0, bathrooms: l.bathrooms || 0, area_sqm: l.area_sqm || 0,
          image: (l.images && l.images[0]) || '', scan: 'false',
          video: hasVideoTour(l) ? 'true' : 'false', video_url: buildVideoStreamUrl(l.video_url) || '',
        },
      })),
    }

    if (map.getSource('kk-listings')) {
      map.getSource('kk-listings').setData(geojson)
      return
    }

    map.addSource('kk-listings', {
      type: 'geojson', data: geojson,
      cluster: true, clusterRadius: 45, clusterMaxZoom: 15,
    })

    map.addLayer({
      id: 'kk-clusters', type: 'circle', source: 'kk-listings',
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': TEAL,
        'circle-radius': ['step', ['get', 'point_count'], 16, 10, 20, 30, 26],
        'circle-stroke-width': 2.5,
        'circle-stroke-color': 'rgba(255,255,255,0.95)',
      },
    })
    map.addLayer({
      id: 'kk-cluster-count', type: 'symbol', source: 'kk-listings',
      filter: ['has', 'point_count'],
      layout: {
        'text-field': ['get', 'point_count_abbreviated'],
        'text-font': ['Noto Sans Bold'],
        'text-size': 13,
      },
      paint: { 'text-color': '#FFFFFF' },
    })
    map.addLayer({
      id: 'kk-point', type: 'circle', source: 'kk-listings',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': TEAL,
        'circle-radius': 7,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#FFFFFF',
      },
    })

    map.on('click', 'kk-clusters', async (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      const zoom = await map.getSource('kk-listings').getClusterExpansionZoom(feature.properties.cluster_id)
      map.easeTo({ center: feature.geometry.coordinates, zoom: Math.min(zoom + 0.5, 17), duration: 600 })
    })
    map.on('click', 'kk-point', (e) => {
      const feature = e.features?.[0]
      if (!feature) return
      openPopupRef.current(feature.properties, feature.geometry.coordinates)
    })
    for (const layerId of ['kk-clusters', 'kk-point']) {
      map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = '' })
    }
  }, [normalListings, mapReady])

  // ── 3D-tour pins: aparte DOM-markers, nooit geclusterd ──
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    pinMarkersRef.current.forEach(m => m.remove())
    pinMarkersRef.current = []

    tourListings.forEach(l => {
      const el = makePinEl()
      const props = {
        id: l.id, title: l.title || 'Woning', price: l.price || 0,
        listing_type: l.listing_type || 'sale',
        bedrooms: l.bedrooms || 0, bathrooms: l.bathrooms || 0, area_sqm: l.area_sqm || 0,
        image: (l.images && l.images[0]) || '', scan: 'true',
        video: hasVideoTour(l) ? 'true' : 'false', video_url: buildVideoStreamUrl(l.video_url) || '',
      }
      const open = (e) => { e.stopPropagation?.(); openPopupRef.current(props, [l.longitude, l.latitude]) }
      el.addEventListener('click', open)
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e) } })
      const marker = new MaplibreMarker({ element: el, anchor: 'bottom' })
        .setLngLat([l.longitude, l.latitude])
        .addTo(map)
      pinMarkersRef.current.push(marker)
    })
  }, [tourListings, mapReady])

  // ── Video-tour pins: zelfde aparte-marker-aanpak, oranje i.p.v. goud ──
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    videoPinMarkersRef.current.forEach(m => m.remove())
    videoPinMarkersRef.current = []

    videoListings.forEach(l => {
      const el = makeVideoPinEl()
      const props = {
        id: l.id, title: l.title || 'Woning', price: l.price || 0,
        listing_type: l.listing_type || 'sale',
        bedrooms: l.bedrooms || 0, bathrooms: l.bathrooms || 0, area_sqm: l.area_sqm || 0,
        image: (l.images && l.images[0]) || '', scan: 'false',
        video: 'true', video_url: buildVideoStreamUrl(l.video_url) || '',
      }
      const open = (e) => { e.stopPropagation?.(); openPopupRef.current(props, [l.longitude, l.latitude]) }
      el.addEventListener('click', open)
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(e) } })
      const marker = new MaplibreMarker({ element: el, anchor: 'bottom' })
        .setLngLat([l.longitude, l.latitude])
        .addTo(map)
      videoPinMarkersRef.current.push(marker)
    })
  }, [videoListings, mapReady])

  // ── Toggle "Alleen 3D-tours": verberg de normale lagen ──
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const vis = tourOnly ? 'none' : 'visible'
    for (const layerId of ['kk-clusters', 'kk-cluster-count', 'kk-point']) {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', vis)
    }
  }, [tourOnly, mapReady])

  function flyToSpot(spot) {
    const map = mapRef.current
    if (!map) return
    setActiveSpot(spot.label)
    map.flyTo({ center: spot.center, zoom: 13.4, pitch: is3D ? 58 : 0, bearing: is3D ? -15 : 0, duration: 2200, essential: true })
  }

  function toggle3D() {
    const map = mapRef.current
    if (!map) return
    const next = !is3D
    setIs3D(next)
    map.easeTo({ pitch: next ? 58 : 0, bearing: next ? -15 : 0, duration: 900, essential: true })
  }

  const glass = {
    background: 'rgba(255,255,255,0.86)',
    backdropFilter: 'blur(14px) saturate(160%)',
    WebkitBackdropFilter: 'blur(14px) saturate(160%)',
    border: '1px solid rgba(255,255,255,0.6)',
    boxShadow: '0 8px 28px rgba(9,42,52,0.14), inset 0 1px 0 rgba(255,255,255,0.7)',
  }

  return (
    <div style={{ minHeight: '100dvh', paddingTop: 72, background: '#F5F0E8', overflowX: 'hidden' }}>
      <style>{`
        .kk3d-pin { position: relative; width: 44px; height: 52px; display: flex; align-items: flex-start; justify-content: center; cursor: pointer; z-index: 30; }
        .kk3d-pin:focus-visible { outline: 2px solid ${TEAL}; outline-offset: 2px; border-radius: 12px; }
        .kk3d-pin-body {
          position: relative; z-index: 2; width: 34px; height: 34px; border-radius: 50%;
          background: linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%);
          color: #1F1407; display: flex; align-items: center; justify-content: center;
          box-shadow: 0 3px 10px rgba(181,134,46,0.55), inset 0 1px 0 rgba(255,255,255,0.45);
          border: 2px solid rgba(255,255,255,0.9);
        }
        .kk3d-pin-tip {
          position: absolute; z-index: 1; top: 30px; left: 50%; transform: translateX(-50%);
          width: 0; height: 0; border-left: 7px solid transparent; border-right: 7px solid transparent;
          border-top: 12px solid #B5862E;
          filter: drop-shadow(0 2px 3px rgba(0,0,0,0.25));
        }
        .kk3d-pin-pulse {
          position: absolute; z-index: 0; top: 1px; left: 50%; margin-left: -16px;
          width: 32px; height: 32px; border-radius: 50%;
          background: rgba(232,181,71,0.5);
          animation: kk3d-pulse 2.4s ease-out infinite;
        }
        @keyframes kk3d-pulse {
          0% { transform: scale(1); opacity: 0.7; }
          70% { transform: scale(2); opacity: 0; }
          100% { transform: scale(2); opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) { .kk3d-pin-pulse { animation: none; opacity: 0; } }
        /* Video-tour pins — oranje merkkleur i.p.v. het 3D-tour-goud */
        .kk3d-pin.video-pin .kk3d-pin-body {
          background: linear-gradient(135deg, #F0805A 0%, #E8672A 50%, #C24E13 100%);
          color: white;
          box-shadow: 0 3px 10px rgba(200,78,19,0.55), inset 0 1px 0 rgba(255,255,255,0.45);
        }
        .kk3d-pin.video-pin .kk3d-pin-tip { border-top-color: #C24E13; }
        .kk3d-pin.video-pin .kk3d-pin-pulse { background: rgba(232,103,42,0.5); }
        .kk3d-popup .maplibregl-popup-content {
          padding: 0; border-radius: 14px; overflow: hidden;
          box-shadow: 0 14px 44px rgba(9,42,52,0.28);
          border: none;
        }
        .kk3d-popup .maplibregl-popup-close-button {
          width: 26px; height: 26px; border-radius: 50%;
          background: rgba(255,255,255,0.9); color: #3F3F46;
          font-size: 16px; line-height: 1; top: 8px; right: 8px;
          display: flex; align-items: center; justify-content: center;
        }
        .kk3d-popup .maplibregl-popup-tip { border-top-color: #FFFFFF; border-bottom-color: #FFFFFF; }
        .kk3d-chips::-webkit-scrollbar { display: none; }
        .kk3d-chips { scrollbar-width: none; }
        @keyframes kk3d-textpulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }
      `}</style>

      <div style={{ position: 'relative', height: 'calc(100dvh - 72px)' }}>
        <div ref={mapEl} style={{ position: 'absolute', inset: 0 }} aria-label="3D-kaart van Curaçao" />

        {/* ── Topbar overlay ── */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, padding: '14px 16px', display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10, pointerEvents: 'none', zIndex: 20 }}>
          <div style={{ ...glass, pointerEvents: 'auto', borderRadius: 14, padding: '10px 16px' }}>
            <h1 style={{ fontSize: 16, fontWeight: 800, color: INK, letterSpacing: '-0.02em', lineHeight: 1.2, display: 'flex', alignItems: 'center', gap: 8 }}>
              <MapTrifold size={17} weight="fill" style={{ color: TEAL }} aria-hidden="true" />
              Curaçao in 3D
            </h1>
            <p style={{ fontSize: 12, color: '#52525B', marginTop: 2 }}>
              {mapListings.length} woningen{tourListings.length > 0 ? ` · ${tourListings.length} met 3D-tour` : ''}
            </p>
          </div>

          <div className="kk3d-chips" style={{ pointerEvents: 'auto', display: 'flex', gap: 8, alignItems: 'center', overflowX: 'auto', maxWidth: '100%', paddingBottom: 2 }}>
            {SPOTS.map(spot => {
              const active = activeSpot === spot.label
              return (
                <button key={spot.label} onClick={() => flyToSpot(spot)}
                  style={{
                    ...(!active ? glass : {}),
                    background: active ? TEAL : glass.background,
                    color: active ? 'white' : INK,
                    border: active ? `1px solid ${TEAL}` : glass.border,
                    minHeight: 44, padding: '0 16px', borderRadius: 999,
                    fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0,
                    boxShadow: active ? '0 6px 18px rgba(0,107,125,0.35)' : glass.boxShadow,
                    transition: 'background-color 0.2s ease, color 0.2s ease',
                  }}>
                  {spot.label}
                </button>
              )
            })}
            <button onClick={toggle3D} aria-label={is3D ? 'Schakel naar 2D-weergave' : 'Schakel naar 3D-weergave'}
              style={{
                ...glass, minHeight: 44, minWidth: 52, padding: '0 14px', borderRadius: 999,
                fontSize: 13, fontWeight: 800, color: TEAL, flexShrink: 0,
                display: 'inline-flex', alignItems: 'center', gap: 6,
                transition: 'background-color 0.2s ease',
              }}>
              <Stack size={15} weight="fill" aria-hidden="true" />
              {is3D ? '2D' : '3D'}
            </button>
            <button onClick={() => setTourOnly(o => !o)} aria-pressed={tourOnly}
              style={{
                ...(!tourOnly ? glass : {}),
                background: tourOnly ? 'linear-gradient(135deg, #E8B547 0%, #B5862E 100%)' : glass.background,
                color: tourOnly ? '#1F1407' : INK,
                border: tourOnly ? '1px solid rgba(181,134,46,0.7)' : glass.border,
                boxShadow: tourOnly ? '0 6px 18px rgba(181,134,46,0.4)' : glass.boxShadow,
                minHeight: 44, padding: '0 14px', borderRadius: 999,
                fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0,
                display: 'inline-flex', alignItems: 'center', gap: 6,
                transition: 'background-color 0.2s ease, color 0.2s ease',
              }}>
              <Cube size={15} weight="fill" aria-hidden="true" />
              Alleen 3D-tours
            </button>
          </div>
        </div>

        {/* ── Legenda ── */}
        <div style={{ ...glass, position: 'absolute', left: 16, bottom: 24, zIndex: 20, borderRadius: 12, padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 7 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, color: '#3F3F46' }}>
            <span aria-hidden="true" style={{ width: 12, height: 12, borderRadius: '50%', background: TEAL, border: '2px solid white', boxShadow: '0 1px 3px rgba(0,0,0,0.2)', flexShrink: 0 }} />
            Woning
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, color: '#3F3F46' }}>
            <span aria-hidden="true" style={{ width: 14, height: 14, borderRadius: '50%', background: 'linear-gradient(135deg, #E8B547 0%, #B5862E 100%)', border: '2px solid white', boxShadow: '0 1px 3px rgba(0,0,0,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Cube size={8} weight="fill" style={{ color: '#1F1407' }} />
            </span>
            3D-tour
          </div>
        </div>

        {/* ── Loading state ── */}
        {status === 'loading' && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 30, background: 'linear-gradient(180deg, #EAF2F0 0%, #F5F0E8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: 56, height: 56, margin: '0 auto 16px', borderRadius: 18, background: 'linear-gradient(135deg, #0E4A5C, #06333F)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 12px 32px rgba(14,74,92,0.3)' }}>
                <MapPin size={26} weight="fill" style={{ color: '#5EEAD4' }} aria-hidden="true" />
              </div>
              <p style={{ fontSize: 15, fontWeight: 700, color: INK, letterSpacing: '-0.01em', animation: 'kk3d-textpulse 1.6s ease-in-out infinite' }}>
                Curaçao laden…
              </p>
              <p style={{ fontSize: 12.5, color: '#71717A', marginTop: 4 }}>Terrein en woningen worden opgebouwd</p>
            </div>
          </div>
        )}

        {/* ── Error state ── */}
        {status === 'error' && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 30, background: '#F5F0E8', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
            <div style={{ ...glass, borderRadius: 18, padding: '32px 28px', maxWidth: 400, textAlign: 'center' }}>
              <div style={{ width: 48, height: 48, margin: '0 auto 14px', borderRadius: 14, background: 'rgba(0,107,125,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <MapTrifold size={24} style={{ color: TEAL }} aria-hidden="true" />
              </div>
              <h2 style={{ fontSize: 17, fontWeight: 800, color: INK, letterSpacing: '-0.02em' }}>De 3D-kaart laadt niet</h2>
              <p style={{ fontSize: 13.5, color: '#52525B', marginTop: 8, lineHeight: 1.55 }}>
                De kaarttegels konden niet worden geladen. Controleer je verbinding of bekijk de woningen op de gewone kaart.
              </p>
              <Link to="/search"
                style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 18, background: TEAL, color: 'white', fontWeight: 700, fontSize: 13.5, padding: '12px 20px', borderRadius: 10 }}>
                Naar de 2D-kaart <ArrowRight size={14} weight="bold" aria-hidden="true" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
