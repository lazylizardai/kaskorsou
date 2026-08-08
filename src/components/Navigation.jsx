import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  MagnifyingGlass, Heart, List, X, ArrowRight,
  House, MapTrifold, UserCircle, SignOut, User, CaretDown, Cube,
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { signOut } from '../lib/supabase'
import AuthModal from './AuthModal'

const TEAL = '#006B7D'
const INK = '#09090B'

export default function Navigation() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [authModal, setAuthModal] = useState(null) // null | 'login' | 'register'
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)
  const location = useLocation()
  const { user, favoriteIds } = useAuth()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  useEffect(() => {
    const handler = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setUserMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const isSearch = location.pathname === '/search'
  const favCount = favoriteIds.size
  // Nav zweeft transparant boven een donkere hero op home + makelaars: tekst moet dan licht zijn
  const onDark = !scrolled && !isSearch && ['/', '/makelaars'].includes(location.pathname)

  async function handleSignOut() {
    await signOut()
    setUserMenuOpen(false)
  }

  return (
    <>
      <motion.nav
        initial={{ y: -24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        style={{
          background: scrolled || isSearch ? 'rgba(255,255,255,0.96)' : 'transparent',
          borderBottom: scrolled || isSearch ? '1px solid #E4E4E7' : '1px solid transparent',
          backdropFilter: scrolled ? 'blur(16px) saturate(160%)' : 'none',
          WebkitBackdropFilter: scrolled ? 'blur(16px) saturate(160%)' : 'none',
        }}
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      >
        <div className="max-w-[1400px] mx-auto px-5 lg:px-8 h-[72px] flex items-center justify-between gap-6">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
            <motion.img
              src="/kaskorsou-icon.svg"
              alt="KasKorsou"
              width={36} height={36}
              whileHover={{ scale: 1.05 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              className="w-9 h-9"
            />
            <span className="hidden sm:block text-lg font-bold tracking-tight" style={{ letterSpacing: '-0.02em' }}>
              <span style={{ color: onDark ? '#FFFFFF' : '#003087' }}>Kas</span>
              <span style={{ color: onDark ? '#5EEAD4' : '#0A7EA4' }}>Kòrsou</span>
            </span>
          </Link>

          {/* Center search bar */}
          {!isSearch && (
            <Link to="/search"
              className="hidden md:flex flex-1 max-w-[420px] mx-auto items-center gap-3 px-4 py-2.5 rounded-full border border-zinc-200 bg-white hover:shadow-md transition-all duration-200">
              <MagnifyingGlass size={15} weight="bold" style={{ color: TEAL }} />
              <span style={{ color: '#A1A1AA' }} className="text-sm flex-1">Zoek op wijk, type of referentie...</span>
              <span style={{ background: TEAL, color: 'white' }}
                className="hidden lg:flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 rounded-full">
                <House size={11} weight="fill" /> Kopen
              </span>
            </Link>
          )}

          {/* Right actions */}
          <div className="hidden md:flex items-center gap-2 shrink-0">
            <Link to="/makelaars"
              style={{
                background: location.pathname === '/makelaars'
                  ? 'linear-gradient(135deg, rgba(232,181,71,0.16) 0%, rgba(212,162,76,0.10) 100%)'
                  : 'transparent',
                color: location.pathname === '/makelaars' ? (onDark ? '#E8B547' : '#9C6F1E') : (onDark ? 'rgba(255,255,255,0.85)' : '#52525B'),
                border: location.pathname === '/makelaars' ? '1px solid rgba(212,162,76,0.5)' : '1px solid transparent',
              }}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${onDark ? 'hover:bg-white/10' : 'hover:text-zinc-900 hover:bg-zinc-50'}`}>
              <Cube size={14} weight="fill" style={{ color: '#D4A24C' }} />
              Voor makelaars
            </Link>
            <Link to="/favorites"
              style={{ color: onDark ? 'rgba(255,255,255,0.85)' : undefined }}
              className={`relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${onDark ? 'hover:bg-white/10' : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50'}`}>
              <Heart size={16} weight={favCount > 0 ? 'fill' : 'regular'} style={{ color: favCount > 0 ? '#E8672A' : undefined }} />
              Bewaard
              {favCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 text-[10px] font-bold text-white rounded-full flex items-center justify-center"
                  style={{ background: '#E8672A' }}>{favCount > 9 ? '9+' : favCount}</span>
              )}
            </Link>

            {user ? (
              <div ref={userMenuRef} className="relative">
                <button onClick={() => setUserMenuOpen(o => !o)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-50 border border-zinc-200 transition-all">
                  <UserCircle size={18} style={{ color: TEAL }} />
                  <span className="max-w-[100px] truncate">{user.user_metadata?.full_name?.split(' ')[0] || 'Account'}</span>
                  <CaretDown size={12} style={{ opacity: 0.5 }} />
                </button>
                <AnimatePresence>
                  {userMenuOpen && (
                    <motion.div initial={{ opacity: 0, y: 4, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.97 }} transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-44 rounded-xl border border-zinc-100 bg-white py-1 shadow-xl z-10">
                      <Link to="/account" onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-zinc-700 hover:bg-zinc-50 transition-colors">
                        <User size={15} style={{ color: TEAL }} /> Mijn account
                      </Link>
                      <Link to="/favorites" onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-zinc-700 hover:bg-zinc-50 transition-colors">
                        <Heart size={15} style={{ color: TEAL }} /> Favorieten
                      </Link>
                      <div className="my-1 border-t border-zinc-100" />
                      <button onClick={handleSignOut}
                        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors">
                        <SignOut size={15} /> Uitloggen
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <button onClick={() => setAuthModal('login')}
                style={{ background: TEAL, color: 'white' }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity">
                Inloggen <ArrowRight size={14} weight="bold" />
              </button>
            )}
          </div>

          {/* Mobile toggle */}
          <button onClick={() => setMobileOpen(o => !o)} aria-label="Menu"
            style={{ color: INK, border: '1px solid #E4E4E7' }}
            className="md:hidden w-10 h-10 flex items-center justify-center rounded-lg bg-white">
            {mobileOpen ? <X size={18} weight="bold" /> : <List size={18} weight="bold" />}
          </button>
        </div>
      </motion.nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}
            style={{ background: 'white', borderBottom: '1px solid #E4E4E7' }}
            className="fixed top-[72px] left-0 right-0 z-40 md:hidden shadow-lg">
            <div className="px-5 py-4 space-y-1">
              {[
                { to: '/', label: 'Home', icon: House },
                { to: '/search', label: 'Zoeken', icon: MagnifyingGlass },
                { to: '/favorites', label: 'Bewaard', icon: Heart },
                { to: '/search', label: 'Kaartoverzicht', icon: MapTrifold },
                { to: '/makelaars', label: 'Voor makelaars', icon: Cube, gold: true },
              ].map(({ to, label, icon: Icon, gold }) => (
                <Link key={label} to={to}
                  className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors">
                  <Icon size={18} weight={gold ? 'fill' : 'regular'} style={{ color: gold ? '#D4A24C' : TEAL }} /> {label}
                </Link>
              ))}
              <div className="pt-2 border-t border-zinc-100">
                {user ? (
                  <div className="space-y-1">
                    <Link to="/account"
                      className="flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-50">
                      <User size={18} style={{ color: TEAL }} /> Mijn account
                    </Link>
                    <button onClick={handleSignOut}
                      className="w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50">
                      <SignOut size={18} /> Uitloggen
                    </button>
                  </div>
                ) : (
                  <button onClick={() => { setMobileOpen(false); setAuthModal('login') }}
                    style={{ background: TEAL, color: 'white' }}
                    className="flex items-center justify-center gap-2 w-full py-3 rounded-lg text-sm font-semibold">
                    Inloggen <ArrowRight size={14} weight="bold" />
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Auth Modal */}
      {authModal && (
        <AuthModal defaultTab={authModal} onClose={() => setAuthModal(null)} />
      )}
    </>
  )
}
