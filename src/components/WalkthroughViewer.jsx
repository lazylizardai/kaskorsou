import { useEffect, useRef, useState, useCallback } from 'react'
import { HandGrabbing, SpeakerSimpleHigh, SpeakerSimpleSlash } from '@phosphor-icons/react'
import { buildVideoStreamUrl } from '../lib/video'
import { walkthroughChapters, walkthroughMusicUrl } from '../lib/walkthrough'

const CORAL = '#E8672A'

// Bezichtiging: de bezoeker sleept zelf door het huis. De video wordt nooit
// afgespeeld — we zetten currentTime rechtstreeks, met een lerp zodat het
// niet schokt. Daarom staat er ook geen geluid op de video: bij scrubben
// speelt audio sowieso niet. Muziek loopt los mee, zodat een makelaar later
// van deuntje kan wisselen zonder dat de video opnieuw gerenderd hoeft.
export default function WalkthroughViewer({ listing }) {
  const chapters = walkthroughChapters(listing)
  const musicUrl = walkthroughMusicUrl(listing)

  const wrapRef = useRef(null)
  const videoRef = useRef(null)
  const musicRef = useRef(null)
  const target = useRef(0)
  const current = useRef(0)
  const raf = useRef(null)
  const dragging = useRef(false)
  const lastX = useRef(0)

  const [idx, setIdx] = useState(0)
  const [touched, setTouched] = useState(false)
  const [sound, setSound] = useState(false)
  const [ready, setReady] = useState(false)

  const tick = useCallback(() => {
    const v = videoRef.current
    current.current += (target.current - current.current) * 0.18
    if (v) {
      const d = v.duration && isFinite(v.duration) ? v.duration : 0
      if (d && v.readyState >= 1) {
        const t = current.current * (d - 0.05)
        if (Math.abs(v.currentTime - t) > 0.016) {
          try { v.currentTime = t } catch { /* seek nog niet mogelijk */ }
        }
      }
    }
    const p = current.current
    let i = 0
    for (let j = chapters.length - 1; j >= 0; j--) {
      if (p >= chapters[j].t) { i = j; break }
    }
    setIdx(prev => (prev === i ? prev : i))
    if (Math.abs(target.current - current.current) > 0.0004) {
      raf.current = requestAnimationFrame(tick)
    } else {
      raf.current = null
    }
  }, [chapters])

  const seekTo = useCallback((p, immediate) => {
    target.current = Math.min(1, Math.max(0, p))
    if (immediate) current.current = target.current
    if (!touched) setTouched(true)
    if (!raf.current) raf.current = requestAnimationFrame(tick)
  }, [tick, touched])

  // Pas laden als de speler in beeld komt — scheelt mobiele data.
  useEffect(() => {
    const el = wrapRef.current
    const v = videoRef.current
    if (!el || !v) return
    if (!('IntersectionObserver' in window)) { v.preload = 'auto'; v.load(); return }
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) { v.preload = 'auto'; v.load(); io.disconnect() }
      })
    }, { rootMargin: '300px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current) }, [])

  const onPointerDown = e => {
    dragging.current = true
    lastX.current = e.clientX
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = e => {
    if (!dragging.current) return
    const w = wrapRef.current?.clientWidth || 1
    const dx = e.clientX - lastX.current
    lastX.current = e.clientX
    seekTo(target.current + dx / (w * 1.6))
  }
  const stop = () => { dragging.current = false }

  const toggleSound = () => {
    const m = musicRef.current
    if (!m) return
    if (m.paused) { m.volume = 0.45; m.play().then(() => setSound(true)).catch(() => {}) }
    else { m.pause(); setSound(false) }
  }

  const ch = chapters[idx] || chapters[0]

  return (
    <div>
      <div
        ref={wrapRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={stop}
        onPointerCancel={stop}
        onWheel={e => { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) { seekTo(target.current + e.deltaX / 2200) } }}
        style={{
          position: 'relative', borderRadius: 16, overflow: 'hidden',
          // Verticale video: de doos krijgt dezelfde 9:16-verhouding, zodat er
          // geen zwarte balken naast staan. Op desktop begrenzen we de breedte,
          // anders wordt hij absurd hoog.
          aspectRatio: '9 / 16', width: '100%', maxWidth: 420, margin: '0 auto',
          boxShadow: `0 0 0 1.5px ${CORAL}, 0 12px 36px rgba(232,103,42,0.20)`,
          background: '#000', cursor: dragging.current ? 'grabbing' : 'grab',
          touchAction: 'pan-y', userSelect: 'none',
        }}
      >
        <video
          ref={videoRef}
          key={listing.walkthrough_url}
          src={buildVideoStreamUrl(listing.walkthrough_url)}
          muted
          playsInline
          preload="none"
          poster={listing.images?.[0]}
          disablePictureInPicture
          onLoadedMetadata={() => { setReady(true); seekTo(0, true) }}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', pointerEvents: 'none' }}
        />

        {/* leesbaarheid van het label boven een licht beeld */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          background: 'linear-gradient(180deg, rgba(0,0,0,0.38) 0%, rgba(0,0,0,0) 16%, rgba(0,0,0,0) 52%, rgba(0,0,0,0.84) 100%)',
        }} />

        <div style={{
          position: 'absolute', top: 12, left: 12, pointerEvents: 'none',
          background: 'rgba(9,9,11,0.7)', backdropFilter: 'blur(8px)',
          border: `1px solid ${CORAL}`, color: 'white', padding: '5px 10px',
          borderRadius: 8, fontSize: 11, fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <HandGrabbing size={11} weight="fill" style={{ color: CORAL }} />
          Bezichtiging
        </div>

        {musicUrl && (
          <button
            onClick={toggleSound}
            aria-label={sound ? 'Muziek uit' : 'Muziek aan'}
            style={{
              position: 'absolute', top: 12, right: 12,
              background: sound ? CORAL : 'rgba(9,9,11,0.7)', backdropFilter: 'blur(8px)',
              border: `1px solid ${sound ? CORAL : 'rgba(255,255,255,0.18)'}`,
              color: 'white', padding: '7px 9px', borderRadius: 8,
              display: 'flex', alignItems: 'center', cursor: 'pointer',
            }}>
            {sound ? <SpeakerSimpleHigh size={14} weight="fill" /> : <SpeakerSimpleSlash size={14} weight="fill" />}
          </button>
        )}

        <div style={{ position: 'absolute', left: 14, right: 14, top: 46, height: 3, background: 'rgba(255,255,255,0.2)', borderRadius: 99, overflow: 'hidden', pointerEvents: 'none' }}>
          <div style={{ height: '100%', width: `${current.current * 100}%`, background: CORAL, transition: 'width 0.12s linear' }} />
        </div>

        <div style={{ position: 'absolute', left: 18, right: 18, bottom: 16, pointerEvents: 'none' }}>
          <div style={{ color: 'white', fontSize: 26, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1, textShadow: '0 2px 20px rgba(0,0,0,0.7)' }}>
            {ch?.name}
          </div>
          {ch?.sub && (
            <div style={{ color: '#E4E4E7', fontSize: 12.5, fontWeight: 500, marginTop: 6, textShadow: '0 1px 12px rgba(0,0,0,0.85)' }}>
              {ch.sub}
            </div>
          )}
        </div>

        {!touched && ready && (
          <div style={{
            position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)',
            background: 'rgba(9,9,11,0.62)', backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.16)', borderRadius: 999,
            padding: '11px 20px', color: 'white', fontSize: 12.5, fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase', pointerEvents: 'none',
          }}>
            ← sleep om te lopen →
          </div>
        )}
      </div>

      {chapters.length > 1 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 12, justifyContent: 'center' }}>
          {chapters.map((c, i) => (
            <button
              key={c.name + i}
              onClick={() => seekTo(c.t + 0.025)}
              style={{
                padding: '7px 13px', borderRadius: 999, fontSize: 12.5, fontWeight: 600,
                background: i === idx ? CORAL : '#F4F4F5',
                color: i === idx ? 'white' : '#52525B',
                border: '1px solid ' + (i === idx ? CORAL : '#E4E4E7'),
                cursor: 'pointer', transition: 'background-color 0.15s, color 0.15s',
              }}>
              {c.name}
            </button>
          ))}
        </div>
      )}

      {musicUrl && <audio ref={musicRef} loop preload="none" src={musicUrl} />}
    </div>
  )
}
