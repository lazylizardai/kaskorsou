import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster'
import { hasActiveScan } from '../lib/scan'
import { hasVideoTour, buildVideoStreamUrl } from '../lib/video'
import { useVideoTour } from '../context/VideoTourContext'
import { formatPrice } from '../lib/currency'

const CURACAO_CENTER = [12.1696, -68.9900]
const CURACAO_BOUNDS = [[11.90, -69.30], [12.50, -68.60]]

// Buurt-centra voor de fallback-plaatsing wanneer een listing geen (bruikbare)
// eigen coördinaten heeft — geldt voor de MEERDERHEID van de listings (geen
// lat/lng gescraped), dus fouten hier raken heel veel pins tegelijk.
// Gecontroleerd/gecorrigeerd 13 aug tegen OSM place-nodes (Overpass) + Nominatim
// — een flink deel van de oorspronkelijke schattingen bleek 3-14 km mis te
// zitten, wat precies verklaart waarom er clusters listings in zee/verkeerd
// terechtkwamen. Enkele namen zijn eerder bewust NIET aangepast ondanks een
// afwijkende Nominatim-treffer, omdat die trof een ander object met dezelfde
// naam (bv. "Rif" → Riffort-ruïne, "Piscadera" → een verweg gelegen baai,
// "Sabana" → een piek).
// 13 aug (2e ronde): "blue bay" bleek TOCH fout — Peter zag een cluster
// listings (century21 + sunset_realtors, neighborhood="Blue Bay") in open
// zee. De oude waarde (12.1047,-69.0214) reverse-geocodet naar NIETS
// (alleen "Curaçao, Nederland" als kaal land-resultaat — een sterk signaal
// voor "in zee"), terwijl de golfresort-coördinaat wél een echte straat in
// de Blue Bay Golf & Beach Resort-wijk oplevert ("Section D, Blauw"). De
// listings zijn van gevestigde makelaars (century21/sunset_realtors) die
// vrijwel zeker de resort-community bedoelen, niet een gelijknamig
// strandje elders — gecorrigeerd naar de resort-locatie.
// 13 aug (3e ronde): de zee-plaatsingen zijn opgelost, maar de 3 destijds
// "bewust ongewijzigd" gelaten entries zijn alsnog uitgezocht, dieper dan de
// eerdere "trof een ander object"-conclusie:
// - "rif" bleek in de praktijk altijd "Rif St. Marie" te zijn (7 remax-
//   listings, geen eigen coördinaten) — een echte plek bij Jan Kok/Sint
//   Willibrordus, west-Curaçao, ~9-10 km van de oude schatting. Nominatim-
//   wegtreffers (Kaminda San Willibrordus) bevestigen de nieuwe locatie.
// - "piscadera" had de oude schatting ~2 km naast waar de echte Piscadera-
//   listings zitten: 11 van de 16 met eigen coördinaten clusteren rond
//   Royal Palm Resort / La Vista / The View (Piscadera Harbour Village).
//   Nieuwe waarde = gemiddelde van dat cluster, reverse-geocodet naar
//   "Royal Palm Resort, Zakitó, Wanapa".
// - "sabana" wordt momenteel door geen enkele listing gebruikt (0 treffers
//   in de live data), maar voor de zekerheid toch gecorrigeerd naar het
//   dichtstbijzijnde OSM-neighbourhood-object "Sabana Hundu" i.p.v. de
//   oude ballpark-schatting.
const NB = {
  'jan thiel':      [12.0852, -68.8766],
  'blue bay':       [12.1364, -68.9855],
  'pietermaai':     [12.1001, -68.9228],
  'coral estate':   [12.2028, -69.0784],
  'piscadera':      [12.1184, -68.9625],
  'willemstad':     [12.1084, -68.9322],
  'otrobanda':      [12.1076, -68.9369],
  'punda':          [12.1059, -68.9289],
  'seru fortuna':   [12.1757, -68.9274],
  'salina':         [12.1064, -68.9036],
  'saliña':         [12.1064, -68.9036],
  'julianadorp':    [12.1625, -68.9672],
  'jan sofat':      [12.0878, -68.8516],
  'barber':         [12.2791, -69.0789],
  'emmastad':       [12.1366, -68.9114],
  'sabana':         [12.1602, -68.9134],
  'westpunt':       [12.3717, -69.1533],
  'lagun':          [12.3317, -69.1297],
  'mahuma':         [12.1673, -68.9543],
  'bapor kibra':    [12.0850, -68.9050],
  'soto':           [12.2790, -69.1101],
  'rif':            [12.2149, -69.0586],
  'mundo nobo':     [12.1150, -68.9450],
  'brievengat':     [12.1350, -68.9150],
  'scharloo':       [12.1020, -68.9200],
  'groot kwartier': [12.1410, -68.9097],
  'sta catarina':   [12.1421, -68.8345],
  'santa catharina':[12.1421, -68.8345],
  'sint joris':     [12.1421, -68.8345],
  'st. joris':      [12.1421, -68.8345],
  'sta maria':      [12.1580, -68.9433],
  'buena vista':    [12.1442, -68.9344],
  'parasasa':       [12.1213, -68.9662],
  'sun valley':     [12.1569, -68.9089],
  'suffisant':      [12.1532, -68.9259],
  'vredenberg':     [12.1180, -68.9480],
  'rooi catootje':  [12.1247, -68.9055],
  'boca gentil':    [12.0728, -68.8754],
  'santa rosa':     [12.1222, -68.8698],
  'girouette':      [12.1158, -68.8947],
  'cas grandi':     [12.0964, -68.8531],
}

// Island bounding box — grove eerste filter. Curaçao is een smal, diagonaal
// eiland, dus een rechthoekige bbox laat nog altijd veel open zee toe
// (bevestigd: scraped listings die met geldige-maar-foute coördinaten in zee
// uitkwamen). Vang dat af met een tweede check hieronder tegen de bekende
// buurt-centra — die liggen verspreid over het hele bewoonde deel van het
// eiland, dus een punt dat ver van ALLE buurten ligt, ligt zo goed als zeker
// in zee.
const LAT_MIN = 12.01, LAT_MAX = 12.42, LNG_MIN = -69.22, LNG_MAX = -68.75

// Max. afstand (km) die een scraped coördinaat van de dichtstbijzijnde bekende
// buurt mag liggen om als betrouwbaar te gelden. Gekalibreerd op de werkelijke
// spreiding van NB hierboven (grootste onderlinge afstand tussen naburige
// buurten is ~6,4 km, bv. westpunt/lagun/blue bay/sta maria/soto aan de
// uiteinden) plus wat marge voor een woning die net buiten een buurtcentrum ligt.
const MAX_KM_FROM_KNOWN_AREA = 8

function jitter(d) { return (Math.random() - 0.5) * d }

function haversineKm(a, b) {
  const R = 6371
  const toRad = (d) => (d * Math.PI) / 180
  const [lat1, lon1] = a, [lat2, lon2] = b
  const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1)
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(x))
}

const NB_CENTERS = Object.values(NB)

function nearestKnownAreaKm(coord) {
  let min = Infinity
  for (const c of NB_CENTERS) {
    const d = haversineKm(coord, c)
    if (d < min) min = d
  }
  return min
}

function getCoords(listing) {
  const nb = (listing.neighborhood || listing.address || '').toLowerCase()
  const nbMatch = Object.entries(NB).find(([k]) => nb.includes(k))

  if (listing.latitude && listing.longitude) {
    const lat = Number(listing.latitude), lng = Number(listing.longitude)
    if (lat >= LAT_MIN && lat <= LAT_MAX && lng >= LNG_MIN && lng <= LNG_MAX) {
      if (nearestKnownAreaKm([lat, lng]) <= MAX_KM_FROM_KNOWN_AREA) {
        return [lat, lng]
      }
      // Coördinaat ligt binnen de bbox maar te ver van elke bekende buurt —
      // vermoedelijk een foute/gegokte geocode uit de bronsite die in zee
      // uitkomt. Val terug op de buurtnaam als die bekend is; anders liever
      // helemaal geen pin tonen dan een pin in zee.
    }
  }
  if (nbMatch) {
    const [, c] = nbMatch
    return [c[0] + jitter(0.003), c[1] + jitter(0.003)]
  }
  return null
}

function fmtPriceBadge(price, listingType, currency) {
  if (!price) return formatPrice(null, currency, listingType)
  return formatPrice(price, currency, listingType).replace('/mnd', '')
}

function fmtPrice(price, type, currency) {
  if (!price) return '–'
  return formatPrice(price, currency, type)
}

function capitalize(s) {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()
}

function buildPopupHTML(listing) {
  const typeLabel = listing.listing_type === 'rent' ? 'Te huur' : 'Te koop'
  const propType = capitalize(listing.property_type || 'Woning')
  const price = fmtPrice(listing.price, listing.listing_type, listing.currency)
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
      ${hasVideoTour(listing) ? `
      <button
        data-video-url="${listing.video_url}"
        style="width:100%;padding:7px 12px;margin-bottom:6px;background:linear-gradient(135deg,#F0805A,#E8672A);color:white;border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:6px"
      ><svg width="11" height="11" viewBox="0 0 256 256" fill="currentColor"><path d="M232.4,114.49,88.32,26.35a16,16,0,0,0-16.2-.3A15.86,15.86,0,0,0,64,39.87V216.13A15.94,15.94,0,0,0,80,232a16.07,16.07,0,0,0,8.36-2.35L232.4,141.51a15.81,15.81,0,0,0,0-27ZM80,215.94V40l143.83,88Z"/></svg>Video Tour bekijken</button>` : ''}
      <button
        data-listing-id="${listing.id}"
        style="width:100%;padding:7px 12px;background:#09090b;color:white;border:none;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit"
        onmouseover="this.style.background='#006B7D'"
        onmouseout="this.style.background='#09090b'"
      >Bekijk details →</button>
    </div>
  `
}

// Price badge marker element
function makePriceBadgeEl(listing, isSelected) {
  const label = fmtPriceBadge(listing.price, listing.listing_type, listing.currency)
  const hasScan = hasActiveScan(listing) || listing.is_premium_scan === true
  const hasVideo = hasVideoTour(listing)
  const el = document.createElement('div')
  const classes = ['kk-price-marker']
  if (isSelected) classes.push('selected')
  if (hasScan) classes.push('premium-scan')
  // Video-tour valt visueel op met de oranje merkkleur — alleen als er geen
  // 3D-scan-styling (goud) al actief is, om kleur-strijd op één badge te voorkomen.
  if (hasVideo && !hasScan) classes.push('has-video')
  el.className = classes.join(' ')
  const cube = hasScan
    ? `<svg width="11" height="11" viewBox="0 0 256 256" fill="currentColor" style="margin-right:4px;flex-shrink:0">
         <path d="M223.68,66.15,135.68,18a15.94,15.94,0,0,0-15.36,0l-88,48.17A16,16,0,0,0,24,80.21v95.58a16,16,0,0,0,8.32,14L120.32,238a15.91,15.91,0,0,0,15.36,0l88-48.17a16,16,0,0,0,8.32-14V80.21A16,16,0,0,0,223.68,66.15ZM128,32l80.34,44L128,120,47.66,76ZM40,90l80,43.78v85.79L40,175.78Zm96,129.57V133.78L216,90v85.78Z"/>
       </svg>`
    : (hasVideo
      ? `<svg width="11" height="11" viewBox="0 0 256 256" fill="currentColor" style="margin-right:4px;flex-shrink:0">
           <path d="M232.4,114.49,88.32,26.35a16,16,0,0,0-16.2-.3A15.86,15.86,0,0,0,64,39.87V216.13A15.94,15.94,0,0,0,80,232a16.07,16.07,0,0,0,8.36-2.35L232.4,141.51a15.81,15.81,0,0,0,0-27ZM80,215.94V40l143.83,88Z"/>
         </svg>`
      : '')
  el.innerHTML = `<div class="kk-price-badge">${cube}${label}</div>`
  return el
}

// Cluster badge — teal circle with count, gold ring if it bundles a 3D-tour
// listing, oranje ring als het (alleen) een video-tour-listing bundelt.
function makeClusterIcon(cluster) {
  const count = cluster.getChildCount()
  const members = cluster.getAllChildMarkers()
  const hasScan = members.some(m => m._kkHasScan)
  const hasVideo = members.some(m => m._kkHasVideo)
  const size = count < 10 ? 38 : count < 30 ? 46 : count < 80 ? 54 : 62
  const ringClass = hasScan ? ' has-scan' : hasVideo ? ' has-video' : ''
  return L.divIcon({
    html: `<div class="kk-cluster-badge${ringClass}" style="width:${size}px;height:${size}px">${count}</div>`,
    className: '',
    iconSize: [size, size],
  })
}

export default function MapView({ listings = [], selectedId, onMarkerClick }) {
  const { openVideo } = useVideoTour()
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const clusterGroupRef = useRef(null)
  const markersRef = useRef([])
  const coordsRef = useRef({})
  const activePopupRef = useRef(null)
  const [ready, setReady] = useState(false)

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

    const clusterGroup = L.markerClusterGroup({
      iconCreateFunction: makeClusterIcon,
      maxClusterRadius: 65,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      animate: true,
    })
    clusterGroup.addTo(map)
    clusterGroupRef.current = clusterGroup

    mapRef.current = map
    setReady(true)
    return () => { map.remove(); mapRef.current = null; clusterGroupRef.current = null }
  }, [])

  // Render individual price badge markers, grouped into clusters when crowded
  useEffect(() => {
    if (!mapRef.current || !ready || !clusterGroupRef.current) return

    // Clear existing markers + popup
    clusterGroupRef.current.clearLayers()
    markersRef.current = []
    if (activePopupRef.current) { activePopupRef.current.remove(); activePopupRef.current = null }

    const newMarkers = []

    listings.forEach((listing) => {
      const coords = getCoords(listing)
      if (!coords) return
      coordsRef.current[listing.id] = coords

      const isSelected = listing.id === selectedId
      const hasScan = hasActiveScan(listing) || listing.is_premium_scan === true
      const hasVideo = hasVideoTour(listing)
      const el = makePriceBadgeEl(listing, isSelected)

      // Click: open popup + notify parent
      el.addEventListener('click', (e) => {
        e.stopPropagation()
        if (activePopupRef.current) { activePopupRef.current.remove(); activePopupRef.current = null }

        const popup = L.popup({
          offset: [0, -10],
          closeButton: true,
          className: 'kk-popup',
          maxWidth: 260,
          minWidth: 220,
        })
          .setLatLng(coords)
          .setContent(buildPopupHTML(listing))
          .addTo(mapRef.current)

        activePopupRef.current = popup

        popup.on('add', () => {
          const btn = popup.getElement()?.querySelector('[data-listing-id]')
          if (btn) btn.addEventListener('click', () => onMarkerClick?.(listing))
          const videoBtn = popup.getElement()?.querySelector('[data-video-url]')
          if (videoBtn) videoBtn.addEventListener('click', (ev) => {
            ev.stopPropagation()
            openVideo({ url: buildVideoStreamUrl(listing.video_url), title: listing.title })
          })
        })
      })

      const m = L.marker(coords, {
        icon: L.divIcon({
          html: el,
          className: '',
          iconAnchor: [0, 0],
          iconSize: [0, 0],
        }),
        zIndexOffset: isSelected ? 1000 : hasScan ? 500 : 0,
      })
      m._kkHasScan = hasScan
      m._kkHasVideo = hasVideo
      newMarkers.push(m)
    })

    clusterGroupRef.current.addLayers(newMarkers)
    markersRef.current = newMarkers
  }, [listings, selectedId, ready, onMarkerClick])

  // FlyTo selected listing
  useEffect(() => {
    if (!mapRef.current || !ready || !selectedId) return
    const c = coordsRef.current[selectedId]
    if (c) mapRef.current.flyTo(c, Math.max(mapRef.current.getZoom(), 14), { duration: 0.8 })
  }, [selectedId, ready])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <style>{`
        /* Price badge markers */
        .kk-price-marker {
          cursor: pointer;
          transform: translate(-50%, -50%);
          display: inline-flex;
        }
        .kk-price-badge {
          background: #09090b;
          color: white;
          padding: 5px 13px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 700;
          white-space: nowrap;
          box-shadow: 0 2px 8px rgba(0,0,0,0.28);
          transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          user-select: none;
        }
        .kk-price-marker:hover .kk-price-badge {
          background: #006B7D;
          transform: scale(1.1);
          box-shadow: 0 4px 12px rgba(0,107,125,0.45);
        }
        .kk-price-marker.selected .kk-price-badge {
          background: #006B7D;
          transform: scale(1.15);
          box-shadow: 0 4px 16px rgba(0,107,125,0.55);
        }
        /* Premium 3D-tour markers — gold gradient + subtle pulse */
        .kk-price-marker.premium-scan .kk-price-badge {
          background: linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%);
          color: #1F1407;
          padding: 5px 13px 5px 9px;
          font-weight: 800;
          box-shadow: 0 3px 10px rgba(212,162,76,0.55), inset 0 1px 0 rgba(255,255,255,0.4);
          display: inline-flex;
          align-items: center;
          animation: kk-pulse 2.6s ease-in-out infinite;
        }
        .kk-price-marker.premium-scan:hover .kk-price-badge {
          background: linear-gradient(135deg, #F1C76A 0%, #E8B547 50%, #C9942F 100%);
          color: #1F1407;
          transform: scale(1.12);
          box-shadow: 0 5px 16px rgba(212,162,76,0.7), inset 0 1px 0 rgba(255,255,255,0.5);
          animation: none;
        }
        .kk-price-marker.premium-scan.selected .kk-price-badge {
          background: linear-gradient(135deg, #F1C76A 0%, #E8B547 50%, #C9942F 100%);
          color: #1F1407;
          transform: scale(1.18);
          box-shadow: 0 6px 20px rgba(212,162,76,0.75), inset 0 1px 0 rgba(255,255,255,0.55);
          animation: none;
        }
        @keyframes kk-pulse {
          0%, 100% { box-shadow: 0 3px 10px rgba(212,162,76,0.55), inset 0 1px 0 rgba(255,255,255,0.4); }
          50%      { box-shadow: 0 4px 16px rgba(212,162,76,0.85), inset 0 1px 0 rgba(255,255,255,0.5); }
        }
        /* Video-tour markers — oranje merkkleur, zelfde gradient als de Video Tour-badges */
        .kk-price-marker.has-video .kk-price-badge {
          background: linear-gradient(135deg, #F0805A 0%, #E8672A 100%);
          color: white;
          box-shadow: 0 3px 10px rgba(232,103,42,0.5), inset 0 1px 0 rgba(255,255,255,0.3);
        }
        .kk-price-marker.has-video:hover .kk-price-badge {
          background: linear-gradient(135deg, #F3946F 0%, #EE7638 100%);
          transform: scale(1.1);
          box-shadow: 0 4px 14px rgba(232,103,42,0.65), inset 0 1px 0 rgba(255,255,255,0.35);
        }
        .kk-price-marker.has-video.selected .kk-price-badge {
          background: linear-gradient(135deg, #F3946F 0%, #EE7638 100%);
          transform: scale(1.15);
          box-shadow: 0 4px 18px rgba(232,103,42,0.7), inset 0 1px 0 rgba(255,255,255,0.4);
        }
        /* Cluster badges — vervangen losse prijs-pills zodra ze te dicht op elkaar staan */
        .kk-cluster-badge {
          display: flex; align-items: center; justify-content: center;
          border-radius: 50%;
          background: #006B7D;
          color: white;
          font-weight: 800;
          font-size: 13px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          box-shadow: 0 3px 10px rgba(0,107,125,0.45), inset 0 1px 0 rgba(255,255,255,0.25);
          border: 2.5px solid rgba(255,255,255,0.92);
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .kk-cluster-badge.has-scan {
          box-shadow: 0 3px 10px rgba(0,107,125,0.45), 0 0 0 3px rgba(232,181,71,0.6);
        }
        .kk-cluster-badge.has-video {
          box-shadow: 0 3px 10px rgba(0,107,125,0.45), 0 0 0 3px rgba(232,103,42,0.65);
        }
        .marker-cluster:hover .kk-cluster-badge {
          transform: scale(1.08);
          box-shadow: 0 5px 16px rgba(0,107,125,0.6), inset 0 1px 0 rgba(255,255,255,0.3);
        }
        /* Popup styles */
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
