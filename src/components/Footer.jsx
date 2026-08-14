import { Link } from 'react-router-dom'
import { Globe, Cube, MagnifyingGlass, Heart, ArrowUpRight } from '@phosphor-icons/react'

const TEAL = '#006B7D'
const INK = '#09090B'

const COLS = [
  {
    label: 'Zoeken',
    links: [
      { to: '/search', text: 'Alle woningen', icon: MagnifyingGlass },
      { to: '/kaart', text: 'Kaart', icon: Globe },
      { to: '/favorites', text: 'Bewaard', icon: Heart },
    ],
  },
  {
    label: 'Makelaars',
    links: [
      { to: '/makelaars', text: 'Voor makelaars', icon: Cube },
      { to: '/hoe-het-werkt#pand-verwijderen', text: 'Pand laten verwijderen' },
      { to: '/hoe-het-werkt#bronnen', text: 'Waar onze data vandaan komt' },
    ],
  },
  {
    label: 'Juridisch',
    links: [
      { to: '/hoe-het-werkt', text: 'Hoe KasKorsou werkt' },
      { to: '/voorwaarden', text: 'Gebruikersvoorwaarden' },
      { to: '/privacy', text: 'Privacy & cookies' },
    ],
  },
]

export default function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer style={{ background: INK }} className="mt-16">
      <div className="max-w-[1400px] mx-auto px-5 lg:px-8 py-12 md:py-16">
        <div className="grid gap-10 md:gap-8" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          {/* Featured merk-blok (span 2 op breed) — geen 4 identieke kolommen */}
          <div style={{ gridColumn: 'span 1' }} className="md:col-span-2 max-w-[46ch]">
            <div className="flex items-center gap-2.5 mb-4">
              <img src="/kaskorsou-icon.svg" alt="" width={32} height={32} className="w-8 h-8" />
              <span className="text-lg font-bold tracking-tight" style={{ letterSpacing: '-0.02em' }}>
                <span style={{ color: '#FFFFFF' }}>Kas</span><span style={{ color: '#5EEAD4' }}>Kòrsou</span>
              </span>
            </div>
            <p style={{ color: 'rgba(255,255,255,0.66)', fontSize: 15, lineHeight: 1.65 }}>
              Al het woningaanbod van Curaçao op één plek. Wij verzamelen wat makelaars en particulieren
              zelf openbaar online zetten, en sturen je door naar de bron. Wij zijn geen makelaar en
              bemiddelen niet.
            </p>
            <Link to="/hoe-het-werkt"
              className="inline-flex items-center gap-1.5 mt-5 px-4 py-2.5 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90"
              style={{ background: TEAL, color: '#FFFFFF' }}>
              Hoe het werkt <ArrowUpRight size={14} weight="bold" />
            </Link>
          </div>

          {COLS.map((col) => (
            <div key={col.label}>
              <p className="text-[11px] font-semibold uppercase mb-4"
                style={{ letterSpacing: '0.09em', color: 'rgba(255,255,255,0.42)' }}>
                {col.label}
              </p>
              <ul className="space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.text}>
                    <Link to={l.to}
                      className="inline-flex items-center gap-2 text-sm transition-colors hover:text-white"
                      style={{ color: 'rgba(255,255,255,0.72)' }}>
                      {l.icon && <l.icon size={14} style={{ color: '#5EEAD4' }} />}
                      {l.text}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-6 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
          style={{ borderTop: '1px solid rgba(255,255,255,0.10)' }}>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            © {year} KasKorsou — een platform van Heijvis B.V. (Lazy Lizard Group), Curaçao.
          </p>
          <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
            <a href="mailto:peter@lazylizardgroup.com" className="hover:text-white transition-colors">peter@lazylizardgroup.com</a>
          </p>
        </div>
      </div>
    </footer>
  )
}
