import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, EnvelopeSimple, Lock, User, Phone, Eye, EyeSlash } from '@phosphor-icons/react'
import { signIn, signUp } from '../lib/supabase'

const TEAL = '#006B7D'

export default function AuthModal({ onClose, defaultTab = 'login' }) {
  const [tab, setTab] = useState(defaultTab)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [success, setSuccess] = useState('')

  // form fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (tab === 'login') {
        await signIn({ email, password })
        onClose()
      } else {
        await signUp({ email, password, fullName, phone })
        setSuccess('Account aangemaakt! Check je email om te bevestigen.')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(6px)' }}
      >
        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          onClick={e => e.stopPropagation()}
          className="w-full max-w-md mx-4 rounded-2xl overflow-hidden"
          style={{ background: '#fff', boxShadow: '0 24px 64px rgba(0,0,0,0.22)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4">
            <div>
              <h2 className="text-xl font-semibold text-zinc-900">
                {tab === 'login' ? 'Welkom terug' : 'Account aanmaken'}
              </h2>
              <p className="text-sm text-zinc-500 mt-0.5">
                {tab === 'login' ? 'Log in om verder te gaan' : 'Gratis registreren'}
              </p>
            </div>
            <button onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-zinc-100 text-zinc-400 transition-colors">
              <X weight="bold" size={16} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex mx-6 mb-5 p-1 rounded-xl" style={{ background: '#F4F4F5' }}>
            {['login', 'register'].map(t => (
              <button key={t} onClick={() => { setTab(t); setError(''); setSuccess('') }}
                className="flex-1 py-2 text-sm font-medium rounded-lg transition-all"
                style={{
                  background: tab === t ? '#fff' : 'transparent',
                  color: tab === t ? '#09090B' : '#71717A',
                  boxShadow: tab === t ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}>
                {t === 'login' ? 'Inloggen' : 'Registreren'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-3">
            <AnimatePresence mode="wait">
              {tab === 'register' && (
                <motion.div key="name-phone"
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }} className="space-y-3 overflow-hidden">
                  <Field icon={<User size={16} />} placeholder="Volledige naam"
                    value={fullName} onChange={e => setFullName(e.target.value)} required />
                  <Field icon={<Phone size={16} />} placeholder="Telefoonnummer (optioneel)"
                    value={phone} onChange={e => setPhone(e.target.value)} type="tel" />
                </motion.div>
              )}
            </AnimatePresence>

            <Field icon={<EnvelopeSimple size={16} />} placeholder="E-mailadres"
              value={email} onChange={e => setEmail(e.target.value)} type="email" autoComplete="email" spellCheck={false} required />

            <div className="relative">
              <Field icon={<Lock size={16} />} placeholder="Wachtwoord"
                value={password} onChange={e => setPassword(e.target.value)}
                type={showPw ? 'text' : 'password'} required />
              <button type="button" onClick={() => setShowPw(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600">
                {showPw ? <EyeSlash size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {error && (
              <p className="text-sm text-red-500 px-1">{error}</p>
            )}
            {success && (
              <p className="text-sm px-1" style={{ color: TEAL }}>{success}</p>
            )}

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white transition-opacity"
              style={{ background: TEAL, opacity: loading ? 0.7 : 1 }}>
              {loading ? 'Even wachten...' : tab === 'login' ? 'Inloggen' : 'Account aanmaken'}
            </button>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function Field({ icon, ...props }) {
  return (
    <div className="flex items-center gap-2.5 px-3.5 py-3 rounded-xl border border-zinc-200
      focus-within:border-[#006B7D] focus-within:ring-2 focus-within:ring-[#006B7D]/10 transition-all">
      <span className="text-zinc-400 shrink-0">{icon}</span>
      <input className="flex-1 text-sm text-zinc-900 outline-none placeholder:text-zinc-400 bg-transparent" {...props} />
    </div>
  )
}
