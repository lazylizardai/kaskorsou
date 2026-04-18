import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Heart } from '@phosphor-icons/react'
import { useAuth } from '../context/AuthContext'
import { getFavorites } from '../lib/supabase'
import ListingCard from '../components/ListingCard'
import AuthModal from '../components/AuthModal'

const TEAL = '#006B7D'

export default function FavoritesPage() {
  const { user, favoriteIds } = useAuth()
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(false)
  const [showAuth, setShowAuth] = useState(false)

  useEffect(() => {
    if (!user) return
    setLoading(true)
    getFavorites(user.id)
      .then(data => setListings(data.map(r => r.kas_listings).filter(Boolean)))
      .finally(() => setLoading(false))
  }, [user, favoriteIds.size]) // re-fetch when count changes

  if (!user) {
    return (
      <div className="min-h-[100dvh] pt-[72px] flex flex-col items-center justify-center gap-6"
        style={{ background: '#F9FAFB' }}>
        <Heart size={48} style={{ color: '#E4E4E7' }} />
        <div className="text-center">
          <h2 style={{ color: '#09090B', fontWeight: 700 }} className="text-xl mb-1">Jouw favorieten</h2>
          <p className="text-sm text-zinc-500 mb-5">Log in om je bewaarde woningen te bekijken.</p>
          <button onClick={() => setShowAuth(true)}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
            style={{ background: TEAL }}>
            Inloggen
          </button>
        </div>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </div>
    )
  }

  return (
    <div className="min-h-[100dvh] pt-[72px]" style={{ background: '#F9FAFB' }}>
      <div className="max-w-6xl mx-auto px-5 py-8">
        <div className="flex items-center gap-3 mb-7">
          <Heart size={22} weight="fill" style={{ color: '#E8672A' }} />
          <h1 style={{ color: '#09090B', fontWeight: 700, letterSpacing: '-0.03em' }} className="text-2xl">
            Bewaarde woningen
          </h1>
          {listings.length > 0 && (
            <span className="text-sm text-zinc-400 font-medium">{listings.length} woning{listings.length !== 1 ? 'en' : ''}</span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-24 text-zinc-400 text-sm">Laden...</div>
        ) : listings.length === 0 ? (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="text-center py-24">
            <Heart size={48} className="mx-auto mb-4" style={{ color: '#E4E4E7' }} />
            <p style={{ color: '#3F3F46', fontWeight: 600 }} className="text-lg mb-1">Nog geen woningen bewaard</p>
            <p className="text-sm text-zinc-500">Klik op het hartje bij een woning om deze te bewaren.</p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {listings.map(l => <ListingCard key={l.id} listing={l} />)}
          </div>
        )}
      </div>
    </div>
  )
}
