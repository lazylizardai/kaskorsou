import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MagnifyingGlass, House, ArrowRight } from '@phosphor-icons/react'
import Footer from '../components/Footer'

const TEAL = '#006B7D'
const INK = '#09090B'

export default function NotFoundPage() {
  useEffect(() => { document.title = 'Pagina niet gevonden — KasKorsou' }, [])

  return (
    <div style={{ background: '#FBFBFC', minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
      <div className="flex-1 flex items-center">
        <div className="max-w-[720px] mx-auto px-5 lg:px-8 py-24 md:py-32 w-full" style={{ paddingTop: 128 }}>
          <p className="text-[11px] font-semibold uppercase mb-3" style={{ letterSpacing: '0.09em', color: '#8A8A94' }}>
            Foutcode 404
          </p>
          <h1 className="font-extrabold" style={{ color: INK, fontSize: 'clamp(2rem, 7vw, 3rem)', letterSpacing: '-0.04em', lineHeight: 1.05 }}>
            Deze pagina bestaat niet
          </h1>
          <p className="mt-4 max-w-[52ch]" style={{ color: '#52525B', fontSize: 16.5, lineHeight: 1.65 }}>
            Misschien is de woning inmiddels verkocht of verhuurd en van het platform gehaald, of klopt
            er iets niet aan de link. Zoek gerust verder — het aanbod wordt elke nacht ververst.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/search"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-semibold transition-opacity hover:opacity-90"
              style={{ background: TEAL, color: '#FFFFFF' }}>
              <MagnifyingGlass size={16} weight="bold" /> Zoek een woning
            </Link>
            <Link to="/"
              className="inline-flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-semibold transition-colors bg-white hover:bg-zinc-50"
              style={{ color: INK, border: '1px solid rgba(0,0,0,0.10)' }}>
              <House size={16} weight="fill" style={{ color: TEAL }} /> Naar de homepage
            </Link>
          </div>
          <Link to="/hoe-het-werkt"
            className="inline-flex items-center gap-1.5 mt-8 text-sm font-medium hover:underline"
            style={{ color: TEAL }}>
            Hoe KasKorsou werkt <ArrowRight size={13} weight="bold" />
          </Link>
        </div>
      </div>
      <Footer />
    </div>
  )
}
