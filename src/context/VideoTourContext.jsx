import { createContext, useCallback, useContext, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Play } from '@phosphor-icons/react'
import { AnimatePresence, motion } from 'framer-motion'

const CORAL = '#E8672A'

const VideoTourContext = createContext(null)

// Globale video-lightbox: overal op de site (kaart, cards, detailpagina)
// dezelfde openVideo({ url, title }) aanroepen en de speler verschijnt.
export function VideoTourProvider({ children }) {
  const [state, setState] = useState(null) // { url, title } | null

  const openVideo = useCallback((payload) => setState(payload), [])
  const closeVideo = useCallback(() => setState(null), [])

  return (
    <VideoTourContext.Provider value={{ openVideo, closeVideo }}>
      {children}
      {createPortal(
      <AnimatePresence>
        {state && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'fixed', inset: 0, zIndex: 2147483000, backgroundColor: 'rgba(0,0,0,0.92)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
              isolation: 'isolate',
            }}
            onClick={closeVideo}
          >
            <button aria-label="Sluit video" onClick={closeVideo}
              style={{
                position: 'absolute', top: 20, right: 20, color: 'rgba(255,255,255,0.7)',
                background: 'rgba(255,255,255,0.1)', width: 40, height: 40, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1,
              }}>
              <X size={20} weight="bold" />
            </button>
            <motion.div
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={{ duration: 0.18 }}
              onClick={(e) => e.stopPropagation()}
              style={{
                position: 'relative', maxWidth: '90vw', maxHeight: '86vh',
                borderRadius: 16, overflow: 'hidden', boxShadow: `0 0 0 1.5px ${CORAL}, 0 20px 60px rgba(0,0,0,0.5)`,
                background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <div style={{
                position: 'absolute', top: 12, left: 12, zIndex: 1,
                background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(8px)',
                border: `1px solid ${CORAL}`, color: 'white', padding: '5px 10px',
                borderRadius: 8, fontSize: 11, fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <Play size={11} weight="fill" style={{ color: CORAL }} />
                Video Tour
              </div>
              {/* width/height:auto ipv 100%/100%: de speler volgt nu de echte
                  beeldverhouding van de video (9:16 vandaag, evt. 16:9 later)
                  i.p.v. een vast vierkant-achtig kader op te dringen. */}
              <video
                key={state.url}
                src={state.url}
                controls
                autoPlay
                playsInline
                style={{ width: 'auto', height: 'auto', maxWidth: '90vw', maxHeight: '86vh', display: 'block', background: '#000' }}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>,
      document.body
      )}
    </VideoTourContext.Provider>
  )
}

export function useVideoTour() {
  const ctx = useContext(VideoTourContext)
  if (!ctx) throw new Error('useVideoTour must be used within a VideoTourProvider')
  return ctx
}
