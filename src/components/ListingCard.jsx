import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Heart, Bed, Bathtub, ArrowsOut, MapPin,
  CaretLeft, CaretRight, ShareNetwork,
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'

const TEAL = '#006B7D'
const CORAL = '#E8672A'

function formatPrice(price, type) {
  if (!price) return 'Prijs op aanvraag'
  if (type === 'rent') return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}/mnd`
  if (price >= 1000000) return `ANG ${(price / 1000000).toFixed(price % 1000000 === 0 ? 0 : 1)}M`
  return `ANG ${new Intl.NumberFormat('nl-NL').format(price)}`
}

export default function ListingCard({ listing, highlighted, onRequireAuth }) {
  const [imgIndex, setImgIndex] = useState(0)
  const [hovered, setHovered] = useState(false)
  const [shareToast, setShareToast] = useState(false)
  const { favoriteIds, toggleFavorite } = useAuth()

  const isFav = favoriteIds.has(listing.id)

  const FALLBACKS = {
    villa:     'https://images.unsplash.com/photo-1613977257363-707ba9348227?w=800&h=600&fit=crop',
    house:     'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop',
    apartment: 'https://images.unsplash.com/photo-1560448204-603b3fc33ddc?w=800&h=600&fit=crop',
    condo:     'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&h=600&fit=crop',
    land:      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&h=600&fit=crop',
    commercial:'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=600&fit=crop',
  }
  const fallback = FALLBACKS[listing.property_type] || FALLBACKS.house
  const images = listing.images?.length > 0 ? listing.images : [fallback]

  const nextImg = (e) => { e.preventDefault(); e.stopPropagation(); setImgIndex(i => (i + 1) % images.length) }
  const prevImg = (e) => { e.preventDefault(); e.stopPropagation(); setImgIndex(i => (i - 1 + images.length) % images.length) }

  function handleFavorite(e) {
    e.preventDefault(); e.stopPropagation()
    toggleFavorite(listing.id, onRequireAuth)
  }

  function handleShare(e) {
    e.preventDefault(); e.stopPropagation()
    const url = `${window.location.origin}/listing/${listing.id}`
    navigator.clipboard.writeText(url).then(() => {
      setShareToast(true)
      setTimeout(() => setShareToast(false), 2200)
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        boxShadow: highlighted
          ? `0 0 0 2px ${TEAL}, 0 8px 24px rgba(0,107,125,0.18)`
          : hovered ? '0 8px 24px rgba(0,0,0,0.10)' : '0 1px 2px rgba(0,0,0,0.06)',
        transform: highlighted ? 'translateY(-2px)' : 'none',
        transition: 'all 0.2s ease',
      }}
      className="group bg-white rounded-2xl overflow-hidden border border-zinc-100"
    >
      <Link to={`/listing/${listing.id}`} className="block">
        {/* Image */}
        <div className="relative overflow-hidden" style={{ aspectRatio: '4/3' }}>
          <img src={images[imgIndex]} alt={listing.title}
            className="w-full h-full object-cover"
            style={{ transform: hovered ? 'scale(1.04)' : 'scale(1)', transition: 'transform 0.6s cubic-bezier(0.22,1,0.36,1)' }}
            loading="lazy" />
          <div className="absolute inset-0" style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.28) 0%, transparent 50%)' }} />

          {/* Arrows */}
          {images.length > 1 && (<>
            <button onClick={prevImg}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white/90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm hover:bg-white">
              <CaretLeft size={14} weight="bold" style={{ color: '#09090B' }} />
            </button>
            <button onClick={nextImg}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white/90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm hover:bg-white">
              <CaretRight size={14} weight="bold" style={{ color: '#09090B' }} />
            </button>
          </>)}

          {/* Dots */}
          {images.length > 1 && (
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
              {images.slice(0, 5).map((_, i) => (
                <div key={i} className="rounded-full transition-all"
                  style={{ width: i === imgIndex ? 16 : 6, height: 4, background: i === imgIndex ? 'white' : 'rgba(255,255,255,0.5)' }} />
              ))}
            </div>
          )}

          {/* Action buttons top-right */}
          <div className="absolute top-3 right-3 flex gap-1.5">
            {/* Share */}
            <div className="relative">
              <button onClick={handleShare}
                className="w-8 h-8 rounded-full bg-white/90 flex items-center justify-center hover:bg-white transition-colors shadow-sm opacity-0 group-hover:opacity-100">
                <ShareNetwork size={14} style={{ color: '#71717A' }} />
              </button>
              <AnimatePresence>
                {shareToast && (
                  <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="absolute right-0 top-10 whitespace-nowrap text-[11px] font-medium text-white px-2.5 py-1.5 rounded-lg shadow-lg"
                    style={{ background: '#09090B' }}>
                    Link gekopieerd!
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            {/* Favorite */}
            <motion.button onClick={handleFavorite}
              whileTap={{ scale: 0.85 }}
              className="w-8 h-8 rounded-full bg-white/90 flex items-center justify-center hover:bg-white transition-colors shadow-sm">
              <Heart size={15} weight={isFav ? 'fill' : 'regular'} style={{ color: isFav ? CORAL : '#71717A' }} />
            </motion.button>
          </div>

          {/* Badges */}
          <div className="absolute top-3 left-3 flex gap-1.5">
            {listing.is_new && <Badge label="Nieuw" color={TEAL} />}
            {listing.is_featured && <Badge label="Uitgelicht" color={CORAL} />}
            {listing.listing_type === 'rent' && <Badge label="Huur" color="#09090B" />}
          </div>
        </div>

        {/* Content */}
        <div className="p-4">
          <p style={{ color: '#09090B', fontWeight: 700, letterSpacing: '-0.03em' }} className="text-lg leading-tight mb-1">
            {formatPrice(listing.price, listing.listing_type)}
          </p>
          <div className="flex items-center gap-1 mb-2">
            <MapPin size={12} weight="fill" style={{ color: TEAL, flexShrink: 0 }} />
            <span style={{ color: '#71717A' }} className="text-xs truncate">
              {listing.neighborhood}{listing.address ? `, ${listing.address}` : ''}
            </span>
          </div>
          <h3 style={{ color: '#3F3F46', fontWeight: 500 }} className="text-sm leading-snug line-clamp-1 mb-3">
            {listing.title}
          </h3>
          <div className="flex items-center gap-4 pt-3 border-t border-zinc-100">
            {listing.bedrooms != null && (
              <Spec icon={<Bed size={13} />} label={`${listing.bedrooms} bed`} />
            )}
            {listing.bathrooms != null && (
              <Spec icon={<Bathtub size={13} />} label={`${listing.bathrooms} bad`} />
            )}
            {listing.area_sqm != null && (
              <Spec icon={<ArrowsOut size={13} />} label={`${listing.area_sqm} m²`} />
            )}
            <span style={{ color: '#A1A1AA', marginLeft: 'auto' }} className="text-[10px] capitalize font-medium">
              {listing.property_type}
            </span>
          </div>
        </div>
      </Link>
    </motion.div>
  )
}

function Badge({ label, color }) {
  return (
    <span style={{ background: color, color: 'white' }}
      className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-md tracking-wide">
      {label}
    </span>
  )
}

function Spec({ icon, label }) {
  return (
    <div className="flex items-center gap-1.5">
      <span style={{ color: '#A1A1AA' }}>{icon}</span>
      <span style={{ color: '#52525B', fontWeight: 500 }} className="text-xs">{label}</span>
    </div>
  )
}
