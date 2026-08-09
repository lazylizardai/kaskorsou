import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Heart, ShareNetwork, Bed, Bathtub, ArrowsOut,
  MapPin, Calendar, Buildings, Phone, Envelope,
  CaretLeft, CaretRight, X, CheckCircle, Cube, Image, Play,
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { getListingById } from '../lib/supabase'
import { hasActiveScan, buildScanEmbedUrl } from '../lib/scan'
import { hasVideoTour, buildVideoStreamUrl } from '../lib/video'
import { useAuth } from '../context/AuthContext'
import AuthModal from '../components/AuthModal'
import { formatPrice } from '../lib/currency'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const INK = '#09090B'
const GOLD = '#D4A24C'

function TourSection({ listing, hasScan, hasVideo }) {
  const [tab, setTab] = useState(hasScan ? 'tour' : hasVideo ? 'video' : 'photos')
  const embedUrl = buildScanEmbedUrl(listing.scan_url)
  const hasTour = !!embedUrl

  return (
    <div>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {hasScan && (
          <button onClick={() => setTab('tour')}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px',
              borderRadius: 999, fontSize: 13, fontWeight: 600,
              background: tab === 'tour'
                ? 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)'
                : '#F4F4F5',
              color: tab === 'tour' ? '#1F1407' : '#52525B',
              border: tab === 'tour' ? `1px solid ${GOLD}` : '1px solid #E4E4E7',
              boxShadow: tab === 'tour' ? '0 2px 8px rgba(212,162,76,0.35)' : 'none',
              transition: 'background-color 0.15s, color 0.15s, border-color 0.15s',
            }}>
            <Cube size={13} weight="fill" />3D Tour
          </button>
        )}
        {hasVideo && (
          <button onClick={() => setTab('video')}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px',
              borderRadius: 999, fontSize: 13, fontWeight: 600,
              background: tab === 'video'
                ? 'linear-gradient(135deg, #F0805A 0%, #E8672A 50%, #C24F1B 100%)'
                : '#F4F4F5',
              color: tab === 'video' ? 'white' : '#52525B',
              border: tab === 'video' ? `1px solid ${CORAL}` : '1px solid #E4E4E7',
              boxShadow: tab === 'video' ? '0 2px 8px rgba(232,103,42,0.30)' : 'none',
              transition: 'background-color 0.15s, color 0.15s, border-color 0.15s',
            }}>
            <Play size={13} weight="fill" />Video Tour
          </button>
        )}
        <button onClick={() => setTab('photos')}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px',
            borderRadius: 999, fontSize: 13, fontWeight: 600,
            background: tab === 'photos' ? INK : '#F4F4F5',
            color: tab === 'photos' ? 'white' : '#52525B',
            border: '1px solid ' + (tab === 'photos' ? INK : '#E4E4E7'),
            transition: 'background-color 0.15s, color 0.15s, border-color 0.15s',
          }}>
          <Image size={13} weight="fill" />Foto's ({listing.images?.length || 0})
        </button>
        {tab === 'tour' && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#A1A1AA', alignSelf: 'center' }}>
            Powered by 3D Gaussian Splatting
          </span>
        )}
        {tab === 'video' && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#A1A1AA', alignSelf: 'center' }}>
            AI-gegenereerde cinematische video, geen live 3D-scan
          </span>
        )}
      </div>

      {tab === 'tour' && hasTour ? (
        <div style={{
          position: 'relative', height: 520, borderRadius: 16, overflow: 'hidden',
          boxShadow: `0 0 0 1.5px ${GOLD}, 0 12px 36px rgba(212,162,76,0.20)`,
          background: '#0B1120',
        }}>
          <iframe
            src={embedUrl}
            title={`3D Tour: ${listing.title}`}
            allow="fullscreen; xr-spatial-tracking; gyroscope; accelerometer"
            allowFullScreen
            style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
          />
          <div style={{
            position: 'absolute', top: 12, left: 12,
            background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(8px)',
            border: `1px solid ${GOLD}`, color: 'white', padding: '5px 10px',
            borderRadius: 8, fontSize: 11, fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <Cube size={11} weight="fill" style={{ color: GOLD }} />
            Live 3D Tour
          </div>
        </div>
      ) : tab === 'tour' && !hasTour ? (
        <div style={{
          height: 280, borderRadius: 16, background: '#F4F4F5',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#71717A', fontSize: 13,
        }}>
          3D Tour wordt binnenkort toegevoegd
        </div>
      ) : tab === 'video' && hasVideo ? (
        <div style={{
          position: 'relative', height: 520, borderRadius: 16, overflow: 'hidden',
          boxShadow: `0 0 0 1.5px ${CORAL}, 0 12px 36px rgba(232,103,42,0.20)`,
          background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <video
            key={listing.video_url}
            src={buildVideoStreamUrl(listing.video_url)}
            controls
            playsInline
            poster={listing.images?.[0]}
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', background: '#000' }}
          />
          <div style={{
            position: 'absolute', top: 12, left: 12, pointerEvents: 'none',
            background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(8px)',
            border: `1px solid ${CORAL}`, color: 'white', padding: '5px 10px',
            borderRadius: 8, fontSize: 11, fontWeight: 600,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <Play size={11} weight="fill" style={{ color: CORAL }} />
            Video Tour
          </div>
        </div>
      ) : (
        <Gallery images={listing.images} />
      )}
    </div>
  )
}



function Gallery({ images }) {
  const [current, setCurrent] = useState(0)
  const [lightbox, setLightbox] = useState(false)
  const imgs = images?.length > 0
    ? images
    : ['https://picsum.photos/seed/detail1/1200/800', 'https://picsum.photos/seed/detail2/1200/800', 'https://picsum.photos/seed/detail3/1200/800']

  return (
    <>
      {/* Grid gallery */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 6, height: 480, borderRadius: 16, overflow: 'hidden' }}>
        <div
          style={{ gridRow: '1/3', cursor: 'pointer', overflow: 'hidden', position: 'relative' }}
          onClick={() => { setCurrent(0); setLightbox(true) }}
          className="group"
        >
          <img src={imgs[0]} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 0.5s ease' }}
            className="group-hover:scale-105" />
        </div>
        {imgs.slice(1, 3).map((img, i) => (
          <div key={i} style={{ cursor: 'pointer', overflow: 'hidden', position: 'relative' }}
            onClick={() => { setCurrent(i + 1); setLightbox(true) }}
            className="group">
            <img src={img} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 0.5s ease' }}
              className="group-hover:scale-105" />
            {i === 1 && imgs.length > 3 && (
              <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.42)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ color: 'white', fontWeight: 700, fontSize: 18 }}>+{imgs.length - 3} foto's</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      <AnimatePresence>
        {lightbox && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(0,0,0,0.92)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={() => setLightbox(false)}
          >
            <button aria-label="Sluit foto's" onClick={() => setLightbox(false)}
              style={{ position: 'absolute', top: 20, right: 20, color: 'rgba(255,255,255,0.7)', background: 'rgba(255,255,255,0.1)', width: 40, height: 40, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <X size={20} weight="bold" />
            </button>
            <button aria-label="Vorige foto" onClick={(e) => { e.stopPropagation(); setCurrent(c => (c - 1 + imgs.length) % imgs.length) }}
              style={{ position: 'absolute', left: 20, top: '50%', transform: 'translateY(-50%)', background: 'rgba(255,255,255,0.12)', color: 'white', width: 44, height: 44, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CaretLeft size={22} weight="bold" />
            </button>
            <img src={imgs[current]} alt=""
              style={{ maxWidth: '88vw', maxHeight: '84vh', objectFit: 'contain', borderRadius: 12 }}
              onClick={(e) => e.stopPropagation()} />
            <button aria-label="Volgende foto" onClick={(e) => { e.stopPropagation(); setCurrent(c => (c + 1) % imgs.length) }}
              style={{ position: 'absolute', right: 20, top: '50%', transform: 'translateY(-50%)', background: 'rgba(255,255,255,0.12)', color: 'white', width: 44, height: 44, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CaretRight size={22} weight="bold" />
            </button>
            <div style={{ position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)', color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
              {current + 1} / {imgs.length}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export default function DetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [listing, setListing] = useState(null)
  const [loading, setLoading] = useState(true)
  const [contactSent, setContactSent] = useState(false)
  const [shareToast, setShareToast] = useState(false)
  const [showAuth, setShowAuth] = useState(false)
  const { favoriteIds, toggleFavorite } = useAuth()
  const isFavorite = listing ? favoriteIds.has(listing.id) : false

  function handleFavorite() {
    if (!listing) return
    toggleFavorite(listing.id, () => setShowAuth(true))
  }

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setShareToast(true)
      setTimeout(() => setShareToast(false), 2500)
    })
  }

  useEffect(() => {
    async function load() {
      setLoading(true)
      const data = await getListingById(id)
      setListing(data)
      setLoading(false)
      if (data) {
        const priceStr = formatPrice(data.price, data.currency, data.listing_type)
        const title = `${data.title} — ${priceStr} | KasKorsou`
        const desc = `${data.property_type || 'Woning'} in ${data.neighborhood || 'Curaçao'} voor ${priceStr}.${data.bedrooms ? ' ' + data.bedrooms + ' slaapkamers,' : ''}${data.area_sqm ? ' ' + data.area_sqm + ' m².' : ''} Bekijk op KasKorsou.`
        document.title = title
        document.querySelector('meta[name="description"]')?.setAttribute('content', desc)
        document.querySelector('meta[property="og:title"]')?.setAttribute('content', title)
        document.querySelector('meta[property="og:description"]')?.setAttribute('content', desc)
        document.querySelector('meta[property="og:url"]')?.setAttribute('content', window.location.href)
      }
    }
    load()
    return () => {
      document.title = 'KasKorsou — Vastgoed & Woningen op Curaçao'
    }
  }, [id])

  if (loading) return (
    <div style={{ paddingTop: 72, minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: 36, height: 36, border: `3px solid #E4E4E7`, borderTopColor: TEAL, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )

  if (!listing) return (
    <div style={{ paddingTop: 72, minHeight: '100dvh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
      <Buildings size={40} style={{ color: '#D4D4D8' }} />
      <p style={{ color: '#71717A', fontWeight: 500 }}>Woning niet gevonden</p>
      <Link to="/search" style={{ color: TEAL, fontWeight: 600, fontSize: 14 }}>Terug naar zoeken</Link>
    </div>
  )

  const specs = [
    { icon: Bed, label: 'Slaapkamers', value: listing.bedrooms },
    { icon: Bathtub, label: 'Badkamers', value: listing.bathrooms },
    { icon: ArrowsOut, label: 'Oppervlak', value: listing.area_sqm ? `${listing.area_sqm} m²` : null },
    { icon: Buildings, label: 'Type', value: listing.property_type },
    { icon: Calendar, label: 'Bouwjaar', value: listing.year_built },
  ].filter(s => s.value != null)

  return (
    <>
    <div style={{ paddingTop: 72, minHeight: '100dvh', background: 'white', fontFamily: 'Geist, system-ui, sans-serif' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 20px 80px' }}>

        {/* Back */}
        <button aria-label="Terug" onClick={() => navigate(-1)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#71717A', fontSize: 13, fontWeight: 500, marginBottom: 20 }}
          className="hover:text-zinc-900 transition-colors">
          <ArrowLeft size={15} weight="bold" /> Terug naar zoeken
        </button>

        {/* Tour of gallery */}
        {(hasActiveScan(listing) || hasVideoTour(listing))
          ? <TourSection listing={listing} hasScan={hasActiveScan(listing)} hasVideo={hasVideoTour(listing)} />
          : <Gallery images={listing.images} />}

        {/* Content grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 48, marginTop: 40, alignItems: 'start' }}
          className="block lg:grid">

          {/* Left */}
          <div>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                  {hasActiveScan(listing) && (
                    <span style={{
                      background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
                      color: '#1F1407',
                      boxShadow: '0 2px 6px rgba(212,162,76,0.45), inset 0 1px 0 rgba(255,255,255,0.35)',
                      fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                      letterSpacing: '0.08em', textTransform: 'uppercase',
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                    }}>
                      <Cube size={11} weight="fill" />3D Tour
                    </span>
                  )}
                  {listing.is_new && (
                    <span style={{ background: '#E6F2F4', color: TEAL, fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6, letterSpacing: '0.08em', textTransform: 'uppercase', display: 'inline-block' }}>
                      Nieuw
                    </span>
                  )}
                </div>
                <h1 style={{ fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1, color: INK, fontSize: 28 }}>
                  {listing.title}
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 8 }}>
                  <MapPin size={14} weight="fill" style={{ color: TEAL }} />
                  <span style={{ color: '#71717A', fontSize: 14 }}>
                    {listing.neighborhood}{listing.address ? `, ${listing.address}` : ''} — Curaçao
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexShrink: 0, alignItems: 'center' }}>
                <div style={{ position: 'relative' }}>
                  <button aria-label="Deel woning" onClick={handleShare}
                    style={{ width: 40, height: 40, borderRadius: '50%', border: '1px solid #E4E4E7', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'white' }}
                    className="hover:bg-zinc-50 transition-colors">
                    <ShareNetwork size={16} style={{ color: '#71717A' }} />
                  </button>
                  <AnimatePresence>
                    {shareToast && (
                      <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                        style={{ position: 'absolute', top: 48, right: 0, whiteSpace: 'nowrap', fontSize: 12, fontWeight: 600, color: 'white', background: '#09090B', padding: '6px 12px', borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
                        Link gekopieerd! 🔗
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                <motion.button onClick={handleFavorite} whileTap={{ scale: 0.85 }}
                  style={{ width: 40, height: 40, borderRadius: '50%', border: `1.5px solid ${isFavorite ? CORAL : '#E4E4E7'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', background: isFavorite ? '#FFF5F0' : 'white', transition: 'background-color 0.2s, border-color 0.2s' }}>
                  <Heart size={16} weight={isFavorite ? 'fill' : 'regular'} style={{ color: isFavorite ? CORAL : '#71717A' }} />
                </motion.button>
              </div>
            </div>

            {/* Specs bar */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24, padding: '20px 0', borderTop: '1px solid #F4F4F5', borderBottom: '1px solid #F4F4F5', marginBottom: 32 }}>
              {specs.map(({ icon: Icon, label, value }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: '#E6F2F4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={16} weight="regular" style={{ color: TEAL }} />
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, color: INK, fontSize: 14, lineHeight: 1 }}>{value}</p>
                    <p style={{ color: '#71717A', fontSize: 11, marginTop: 2 }}>{label}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Description */}
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontWeight: 700, fontSize: 17, color: INK, marginBottom: 12 }}>Beschrijving</h2>
              <p style={{ color: '#52525B', lineHeight: 1.7, fontSize: 14 }}>
                {listing.description || 'Geen beschrijving beschikbaar.'}
              </p>
            </div>

            {/* Features */}
            {listing.features?.length > 0 && (
              <div style={{ marginBottom: 32 }}>
                <h2 style={{ fontWeight: 700, fontSize: 17, color: INK, marginBottom: 12 }}>Kenmerken</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
                  {listing.features.map((f, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <CheckCircle size={16} weight="fill" style={{ color: TEAL, flexShrink: 0 }} />
                      <span style={{ color: '#3F3F46', fontSize: 13 }}>{f}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right — price card */}
          <div className="mt-8 lg:mt-0">
            <div style={{
              position: 'sticky', top: 96,
              background: 'white', borderRadius: 20,
              border: '1px solid #E4E4E7',
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              padding: 24,
            }}>
              <p style={{ color: INK, fontWeight: 800, fontSize: 32, letterSpacing: '-0.04em', lineHeight: 1 }}>
                {formatPrice(listing.price, listing.currency, listing.listing_type)}
              </p>
              {listing.listing_type === 'rent' && (
                <p style={{ color: '#71717A', fontSize: 13, marginTop: 4 }}>per maand</p>
              )}

              <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {!contactSent ? (
                  <>
                    <button
                      onClick={() => setContactSent(true)}
                      style={{ background: TEAL, color: 'white', padding: '13px 20px', borderRadius: 12, fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                      className="hover:opacity-90 transition-opacity">
                      <Phone size={16} /> Bel makelaar
                    </button>
                    <button
                      onClick={() => setContactSent(true)}
                      style={{ background: 'white', color: TEAL, padding: '13px 20px', borderRadius: 12, fontWeight: 600, fontSize: 14, border: `1.5px solid ${TEAL}`, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                      className="hover:bg-teal-50 transition-colors">
                      <Envelope size={16} /> Stuur bericht
                    </button>
                  </>
                ) : (
                  <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                    style={{ background: '#E6F2F4', borderRadius: 12, padding: '16px', textAlign: 'center' }}>
                    <CheckCircle size={28} weight="fill" style={{ color: TEAL, margin: '0 auto 8px' }} />
                    <p style={{ fontWeight: 600, color: TEAL, fontSize: 14 }}>Aanvraag ontvangen</p>
                    <p style={{ color: '#71717A', fontSize: 12, marginTop: 4 }}>De makelaar neemt binnen 24u contact op</p>
                  </motion.div>
                )}
              </div>

              {listing.agent_name && (
                <div style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid #F4F4F5' }}>
                  <p style={{ color: '#A1A1AA', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>
                    Aangeboden door
                  </p>
                  <p style={{ fontWeight: 600, color: INK, fontSize: 14 }}>{listing.agent_name}</p>
                  {listing.agent_company && (
                    <p style={{ color: '#71717A', fontSize: 12, marginTop: 2 }}>{listing.agent_company}</p>
                  )}
                </div>
              )}

              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #F4F4F5', display: 'flex', gap: 12 }}>
                <div>
                  <p style={{ color: '#A1A1AA', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 2 }}>Type</p>
                  <p style={{ fontWeight: 600, color: INK, fontSize: 13, textTransform: 'capitalize' }}>{listing.listing_type === 'sale' ? 'Te koop' : 'Te huur'}</p>
                </div>
                {listing.year_built && (
                  <div style={{ borderLeft: '1px solid #F4F4F5', paddingLeft: 12 }}>
                    <p style={{ color: '#A1A1AA', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 2 }}>Bouwjaar</p>
                    <p style={{ fontWeight: 600, color: INK, fontSize: 13 }}>{listing.year_built}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </>
  )
}
