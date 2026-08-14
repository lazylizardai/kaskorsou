import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { User, EnvelopeSimple, Phone, Heart, SignOut, Check, ArrowLeft } from '@phosphor-icons/react'
import { useAuth } from '../context/AuthContext'
import { supabase, updateProfile, signOut, getFavorites } from '../lib/supabase'
import ListingCard from '../components/ListingCard'
import Footer from '../components/Footer'

const TEAL = '#006B7D'

export default function AccountPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('profile')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [favorites, setFavorites] = useState([])
  const [favLoading, setFavLoading] = useState(false)

  useEffect(() => {
    if (!user) { navigate('/'); return }
    // load profile
    supabase.from('kas_profiles').select('*').eq('id', user.id).single().then(({ data }) => {
      if (data) { setFullName(data.full_name || ''); setPhone(data.phone || '') }
      else { setFullName(user.user_metadata?.full_name || '') }
    })
  }, [user, navigate])

  useEffect(() => {
    if (tab === 'favorites' && user) {
      setFavLoading(true)
      getFavorites(user.id)
        .then(data => setFavorites(data.map(r => r.kas_listings).filter(Boolean)))
        .finally(() => setFavLoading(false))
    }
  }, [tab, user])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await updateProfile({ fullName, phone })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      console.error(err)
    } finally { setSaving(false) }
  }

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  if (!user) return null

  return (
    <div className="min-h-[100dvh] pt-[72px]" style={{ background: '#F9FAFB' }}>
      <div className="max-w-4xl mx-auto px-5 py-8">
        {/* Back */}
        <button onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-800 mb-6 transition-colors">
          <ArrowLeft size={15} /> Terug
        </button>

        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-white text-xl font-bold"
            style={{ background: TEAL }}>
            {(fullName || user.email)?.[0]?.toUpperCase() || 'U'}
          </div>
          <div>
            <h1 style={{ color: '#09090B', fontWeight: 700, letterSpacing: '-0.03em' }} className="text-2xl">
              {fullName || 'Mijn account'}
            </h1>
            <p className="text-sm text-zinc-500">{user.email}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 rounded-xl mb-6 w-fit" style={{ background: '#E4E4E7' }}>
          {[['profile', <User size={15} />, 'Profiel'], ['favorites', <Heart size={15} />, 'Favorieten']].map(([key, icon, label]) => (
            <button key={key} onClick={() => setTab(key)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ background: tab === key ? 'white' : 'transparent', color: tab === key ? '#09090B' : '#71717A',
                boxShadow: tab === key ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
              {icon} {label}
            </button>
          ))}
        </div>

        {tab === 'profile' && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl border border-zinc-100 p-6 shadow-sm">
            <h2 style={{ color: '#09090B', fontWeight: 600 }} className="text-lg mb-5">Persoonlijke gegevens</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Volledige naam</label>
                <div className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl border border-zinc-200 focus-within:border-[#006B7D] transition-all">
                  <User size={16} className="text-zinc-400" />
                  <input value={fullName} onChange={e => setFullName(e.target.value)}
                    className="flex-1 text-sm text-zinc-900 outline-none bg-transparent" placeholder="Jouw naam" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">E-mailadres</label>
                <div className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl border border-zinc-100 bg-zinc-50">
                  <EnvelopeSimple size={16} className="text-zinc-400" />
                  <span className="text-sm text-zinc-400">{user.email}</span>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-zinc-500 mb-1.5 block">Telefoonnummer</label>
                <div className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl border border-zinc-200 focus-within:border-[#006B7D] transition-all">
                  <Phone size={16} className="text-zinc-400" />
                  <input value={phone} onChange={e => setPhone(e.target.value)} type="tel"
                    className="flex-1 text-sm text-zinc-900 outline-none bg-transparent" placeholder="+599 ..." />
                </div>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button type="submit" disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all"
                  style={{ background: saved ? '#16A34A' : TEAL, opacity: saving ? 0.7 : 1 }}>
                  {saved ? <><Check size={15} weight="bold" /> Opgeslagen</> : saving ? 'Opslaan...' : 'Wijzigingen opslaan'}
                </button>
              </div>
            </form>

            <div className="mt-8 pt-6 border-t border-zinc-100">
              <button onClick={handleSignOut}
                className="flex items-center gap-2 text-sm text-red-500 hover:text-red-600 transition-colors">
                <SignOut size={16} /> Uitloggen
              </button>
            </div>
          </motion.div>
        )}

        {tab === 'favorites' && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            {favLoading ? (
              <div className="flex items-center justify-center py-20 text-zinc-400 text-sm">Laden...</div>
            ) : favorites.length === 0 ? (
              <div className="text-center py-20">
                <Heart size={40} className="mx-auto mb-3" style={{ color: '#E4E4E7' }} />
                <p style={{ color: '#71717A' }} className="text-sm">Nog geen favorieten bewaard.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {favorites.map(l => <ListingCard key={l.id} listing={l} />)}
              </div>
            )}
          </motion.div>
        )}
      </div>
      <Footer />
    </div>
  )
}
