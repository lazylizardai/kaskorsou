import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CaretRight, ArrowUp } from '@phosphor-icons/react'
import Footer from './Footer'

const TEAL = '#006B7D'
const INK = '#09090B'

/* Lichte surface-ladder (content-zwaar scherm = licht, per ll-surface-system regel 5) */
export const L0 = '#FBFBFC'   // page
export const L1 = '#FFFFFF'   // card
export const L2 = '#F2F2F5'   // inset
export const LINE = 'rgba(0,0,0,0.08)'
export const T1 = '#18181B'   // primary
export const T2 = '#52525B'   // body
export const T3 = '#8A8A94'   // label

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

/**
 * Gedeelde opmaak voor juridische / uitlegpagina's.
 * sections: [{ title, blocks: [{ type: 'p'|'ul'|'note'|'h3', text|items }] }]
 */
export default function LegalLayout({ eyebrow, title, intro, updated, sections, metaDescription, canonical }) {
  const [showTop, setShowTop] = useState(false)

  useEffect(() => {
    document.title = `${title} — KasKorsou`
    const d = document.querySelector('meta[name="description"]')
    if (d && metaDescription) d.setAttribute('content', metaDescription)
    const c = document.querySelector('link[rel="canonical"]')
    if (c && canonical) c.setAttribute('href', canonical)
    const hash = window.location.hash?.slice(1)
    const target = hash && document.getElementById(decodeURIComponent(hash))
    if (target) target.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [title, metaDescription, canonical])

  useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > 700)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div style={{ background: L0, minHeight: '100dvh' }}>
      {/* Vol verzadigde header-band — kleurbudget van het scherm */}
      <header style={{ background: TEAL, paddingTop: 72 }}>
        <div className="max-w-[1100px] mx-auto px-5 lg:px-8 py-12 md:py-16">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase mb-4"
            style={{ letterSpacing: '0.09em', color: 'rgba(255,255,255,0.72)' }}>
            <Link to="/" className="hover:text-white transition-colors">KasKorsou</Link>
            <CaretRight size={10} weight="bold" />
            <span style={{ color: '#FFFFFF' }}>{eyebrow}</span>
          </div>
          <h1 className="font-extrabold text-white"
            style={{
              fontSize: 'clamp(1.5rem, 5.4vw, 3.25rem)', letterSpacing: '-0.04em', lineHeight: 1.06,
              overflowWrap: 'break-word', hyphens: 'auto',
            }}>
            {title}
          </h1>
          {intro && (
            <p className="mt-5 max-w-[62ch]"
              style={{ color: 'rgba(255,255,255,0.88)', fontSize: 17, lineHeight: 1.6 }}>
              {intro}
            </p>
          )}
          {updated && (
            <p className="mt-6 inline-block rounded-full px-3 py-1.5 text-[12px] font-semibold"
              style={{ background: 'rgba(255,255,255,0.16)', color: '#FFFFFF' }}>
              Laatst bijgewerkt: {updated}
            </p>
          )}
        </div>
      </header>

      <div className="max-w-[1100px] mx-auto px-5 lg:px-8 py-10 md:py-14 grid gap-8 lg:gap-12"
        style={{ gridTemplateColumns: 'minmax(0, 1fr)' }}>
        <div className="lg:grid lg:gap-12" style={{ gridTemplateColumns: '220px minmax(0, 1fr)' }}>
          {/* Inhoudsopgave */}
          <nav className="hidden lg:block">
            <div className="sticky top-[92px]">
              <p className="text-[11px] font-semibold uppercase mb-3" style={{ letterSpacing: '0.09em', color: T3 }}>
                Op deze pagina
              </p>
              <ul className="space-y-1.5">
                {sections.map((s, i) => (
                  <li key={s.title}>
                    <a href={`#${s.id || slug(s.title)}`}
                      className="block text-[13px] leading-snug hover:underline transition-colors"
                      style={{ color: T2 }}>
                      <span style={{ color: T3 }}>{i + 1}.</span> {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </nav>

          {/* Inhoud */}
          <main className="min-w-0 space-y-4 md:space-y-5">
            {sections.map((s, i) => (
              <section key={s.title} id={s.id || slug(s.title)}
                style={{ background: L1, border: `1px solid ${LINE}`, borderRadius: 16, scrollMarginTop: 92 }}
                className="p-5 md:p-7">
                <div className="flex items-start gap-3 mb-4">
                  <span className="shrink-0 flex items-center justify-center rounded-lg text-[13px] font-bold tabular-nums"
                    style={{ background: TEAL, color: '#FFFFFF', width: 28, height: 28 }}>
                    {i + 1}
                  </span>
                  <h2 className="font-bold" style={{ color: T1, fontSize: 20, letterSpacing: '-0.02em', lineHeight: 1.25, paddingTop: 2 }}>
                    {s.title}
                  </h2>
                </div>
                <div className="space-y-3.5">
                  {s.blocks.map((b, bi) => {
                    if (b.type === 'h3') return (
                      <h3 key={bi} className="text-[11px] font-semibold uppercase pt-2"
                        style={{ letterSpacing: '0.09em', color: T3 }}>{b.text}</h3>
                    )
                    if (b.type === 'ul') return (
                      <ul key={bi} className="space-y-2">
                        {b.items.map((it, ii) => (
                          <li key={ii} className="flex gap-2.5" style={{ color: T2, fontSize: 15, lineHeight: 1.6 }}>
                            <span aria-hidden className="shrink-0 rounded-full mt-[9px]"
                              style={{ background: TEAL, width: 5, height: 5 }} />
                            <span>{it}</span>
                          </li>
                        ))}
                      </ul>
                    )
                    if (b.type === 'note') return (
                      <div key={bi} className="rounded-r-lg px-4 py-3.5"
                        style={{ background: L2, borderLeft: `3px solid ${TEAL}` }}>
                        <p style={{ color: T1, fontSize: 14.5, lineHeight: 1.6, fontWeight: 500 }}>{b.text}</p>
                      </div>
                    )
                    return <p key={bi} style={{ color: T2, fontSize: 15, lineHeight: 1.68 }}>{b.text}</p>
                  })}
                </div>
              </section>
            ))}

            <div className="rounded-2xl p-5 md:p-7" style={{ background: INK }}>
              <p className="text-[11px] font-semibold uppercase mb-2" style={{ letterSpacing: '0.09em', color: 'rgba(255,255,255,0.5)' }}>
                Vraag of verzoek
              </p>
              <p className="text-white font-bold mb-1" style={{ fontSize: 19, letterSpacing: '-0.02em' }}>
                Iets onduidelijk, of wil je een pand van het platform af?
              </p>
              <p style={{ color: 'rgba(255,255,255,0.72)', fontSize: 15, lineHeight: 1.6 }}>
                Mail naar <a href="mailto:peter@lazylizardgroup.com" className="underline" style={{ color: '#5EEAD4' }}>peter@lazylizardgroup.com</a>.
                Verwijderverzoeken van makelaars en eigenaren voeren we binnen vijf werkdagen door.
              </p>
            </div>
          </main>
        </div>
      </div>

      {showTop && (
        <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          aria-label="Terug naar boven"
          className="fixed bottom-5 right-5 z-40 flex items-center justify-center rounded-full shadow-lg transition-transform hover:scale-105"
          style={{ background: TEAL, color: '#FFFFFF', width: 46, height: 46 }}>
          <ArrowUp size={18} weight="bold" />
        </button>
      )}

      <Footer />
    </div>
  )
}
