import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Camera, CaretDown, ChartLineUp, Check, Crown, Cube,
  Eye, House, ShootingStar, Sparkle, X,
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'

const TEAL = '#006B7D'
const CORAL = '#E8672A'
const SAND = '#F5F0E8'
const INK = '#09090B'
const DARK = '#0B1120'
const GOLD = '#D4A24C'

const slideUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] },
})

const TIERS = [
  {
    id: 'single',
    name: 'Single Scan',
    icon: Camera,
    price: 'XCG 999',
    suffix: 'eenmalig',
    blurb: 'Eén woning. Eén scan. Eén jaar hosting inclusief.',
    features: [
      '1 fotorealistische 3D-tour',
      'Premium positie op KasKorsou (12 maanden)',
      '"3D Tour" badge op kaart, lijst en card',
      'Embed-link voor je eigen website',
      'Gouden pin op kaart — clustert niet weg',
    ],
    cta: 'Bestel single scan',
    badge: null,
    color: TEAL,
  },
  {
    id: 'pro',
    name: 'Makelaar Pro',
    icon: ChartLineUp,
    price: 'XCG 1.999',
    suffix: 'per maand',
    blurb: 'Voor kantoren met 5+ listings die structureel willen opvallen.',
    features: [
      '5 scans per maand inclusief',
      'AI auto-tagging (kamers, features, m²)',
      'Dashboard met views/leads per listing',
      'Eigen branded viewer-pagina',
      'Voorrang op planning + 24u oplevering',
      'Maandrapport: zoveel kopers bekeken jouw listings',
    ],
    cta: 'Word Makelaar Pro',
    badge: 'MEEST GEKOZEN',
    color: GOLD,
  },
  {
    id: 'diy',
    name: 'Airbnb DIY',
    icon: House,
    price: 'XCG 299',
    suffix: 'per scan',
    blurb: 'Voor hosts: jij filmt zelf, wij processen + hosten.',
    features: [
      'Capture-template + 1-op-1 begeleiding (15 min call)',
      'Wij verwerken jouw video tot 3D-tour',
      '6 maanden hosting',
      'Embed-link voor Airbnb / Booking.com',
      'Optie: upgrade naar pro-scan voor XCG 599',
    ],
    cta: 'Start DIY scan',
    badge: null,
    color: CORAL,
  },
  {
    id: 'resort',
    name: 'Resort Retainer',
    icon: Crown,
    price: 'Vanaf XCG 4.999',
    suffix: 'per maand',
    blurb: 'Maandelijkse scan tijdens nieuwbouw — voor investor decks en pre-sales.',
    features: [
      'Maandelijkse update-scan tot oplevering',
      'Pre-sales tour-pagina voor je investeerders',
      'Tijdlijn-viewer (zie de bouw vorderen per maand)',
      'White-label viewer in jouw branding',
      'Persoonlijke account-manager',
    ],
    cta: 'Plan kennismaking',
    badge: 'B2B',
    color: '#7C3AED',
  },
]

const STEPS = [
  {
    n: '01',
    icon: Camera,
    title: 'Wij scannen jouw woning',
    desc: '15–60 min on-site met telefoon. Geen verbouwing nodig, geen speciale apparatuur. We werken met natuurlijk daglicht en jouw bestaande styling.',
  },
  {
    n: '02',
    icon: Cube,
    title: 'Binnen 48u online',
    desc: 'Cloud-processing maakt een fotorealistische 3D-tour van jouw woning. Werkt direct in de browser — geen app, geen VR-bril.',
  },
  {
    n: '03',
    icon: ShootingStar,
    title: 'Premium-positie op KasKorsou',
    desc: 'Jouw listing krijgt een gouden pin op de kaart, een "3D Tour" badge, en staat bovenaan in alle zoekresultaten. Kopers filteren steeds vaker op alleen 3D-tours.',
  },
]

const FAQS = [
  {
    q: 'Hoe lang duurt een scan?',
    a: 'Een gemiddelde woning duurt 30–60 min on-site. We plannen één moment met je in en de scan staat binnen 48 uur live op KasKorsou. Resorts in bouwfase doen we per scan-bezoek 60–90 min.',
  },
  {
    q: 'Wat als ik mijn listing wil veranderen?',
    a: 'Bij Single Scan en Pro krijg je één gratis re-shoot per jaar als de woning ingrijpend verandert (renovatie, nieuwe meubels). Daarbuiten 50% korting op een aanvullende scan.',
  },
  {
    q: 'Kan ik de 3D-tour ook op mijn eigen site gebruiken?',
    a: 'Ja. Je krijgt een embed-link die je in je eigen makelaarssite, Funda Caribbean, Facebook Marketplace post of LinkedIn kunt zetten. Werkt overal waar iframe wordt ondersteund.',
  },
  {
    q: 'Wat gebeurt er als ik stop met betalen voor Makelaar Pro?',
    a: 'Bestaande scans blijven zichtbaar zonder premium-positie. Geen gouden pin, geen voorrang in zoekresultaten, maar de tour blijft beschikbaar voor 12 maanden vanaf upload-datum.',
  },
  {
    q: 'Werkt het ook voor verhuur (rent)?',
    a: 'Absoluut. Met name Airbnb-hosts en boutique hotels zien direct conversie-impact: bezoekers die de 3D-tour bekeken boeken vaker en stellen minder vragen vooraf. Single Scan-tier werkt voor zowel koop als huur.',
  },
  {
    q: 'Kan ik dit zelf?',
    a: 'Ja, met onze DIY-tier voor XCG 299 begeleiden we je om zelf te filmen. Maar voor de meeste makelaars is service-tier lonender — onze kwaliteit ligt structureel hoger, en de tijd die jij niet kwijt bent aan capture/processing besteedt aan klanten zelf.',
  },
]

const PROBLEMS = [
  'Kopers vragen 5+ verschillende makelaars om bezichtigingen — jij bent één van velen',
  'Foto-galerijen tonen niet hoe ruimtes echt aanvoelen',
  'Video-tours zijn lineair en eenrichtingsverkeer — geen interactie',
  'Internationale kopers (NL, US) willen niet vliegen voor een eerste indruk',
  'De wapenwedloop met content op Instagram en Facebook stopt nooit',
]

const SOLUTIONS = [
  'Kopers lopen virtueel door de woning vanuit de browser — kiezen vooraf welke 2-3 ze fysiek bezoeken',
  'Internationale klanten beslissen vanuit NL/US zonder eerst te vliegen',
  'Premium positie op KasKorsou: gouden pin, badge, bovenaan zoekresultaten',
  'Embed-link voor je eigen socials, makelaarssite en WhatsApp business',
  'Kopers stellen minder voorvragen — alleen serieuze leads bellen',
]

const DEMO_LISTING = '/listing/eee32cd1-bfa9-4801-93de-14f8c2b35790'

function FaqItem({ q, a, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ borderBottom: '1px solid #E4E4E7' }}>
      <button onClick={() => setOpen(!open)}
        style={{
          width: '100%', padding: '20px 0', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', color: INK, fontWeight: 600, fontSize: 16, textAlign: 'left',
        }}>
        {q}
        <CaretDown size={16} weight="bold"
          style={{ color: '#A1A1AA', transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s', flexShrink: 0 }} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: 'hidden' }}>
            <p style={{ color: '#52525B', fontSize: 15, lineHeight: 1.55, paddingBottom: 20, maxWidth: 720 }}>{a}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function TierCard({ tier, idx }) {
  const Icon = tier.icon
  const isPro = tier.id === 'pro'
  return (
    <motion.div {...slideUp(idx * 0.05)}
      style={{
        position: 'relative',
        background: isPro ? DARK : 'white',
        color: isPro ? 'white' : INK,
        border: isPro ? `1.5px solid ${GOLD}` : '1px solid #E4E4E7',
        borderRadius: 18,
        padding: 28,
        boxShadow: isPro
          ? `0 0 0 1px ${GOLD}33, 0 18px 40px -12px rgba(212,162,76,0.35)`
          : '0 1px 3px rgba(0,0,0,0.04)',
        display: 'flex',
        flexDirection: 'column',
      }}>
      {tier.badge && (
        <span style={{
          position: 'absolute', top: -10, left: 24,
          background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
          color: '#1F1407', padding: '4px 10px', borderRadius: 6,
          fontSize: 10, fontWeight: 800, letterSpacing: '0.08em',
          boxShadow: '0 2px 6px rgba(212,162,76,0.45)',
        }}>{tier.badge}</span>
      )}
      <div style={{
        width: 40, height: 40, borderRadius: 10,
        background: isPro ? `${tier.color}22` : `${tier.color}14`,
        color: tier.color,
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16,
      }}>
        <Icon size={20} weight="duotone" />
      </div>
      <h3 style={{ fontWeight: 700, fontSize: 19, letterSpacing: '-0.02em', marginBottom: 4 }}>{tier.name}</h3>
      <p style={{ fontSize: 13, color: isPro ? 'rgba(255,255,255,0.6)' : '#71717A', marginBottom: 18, lineHeight: 1.4 }}>
        {tier.blurb}
      </p>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 22 }}>
        <span style={{ fontWeight: 800, fontSize: 28, letterSpacing: '-0.03em' }}>{tier.price}</span>
        <span style={{ fontSize: 13, color: isPro ? 'rgba(255,255,255,0.55)' : '#71717A' }}>{tier.suffix}</span>
      </div>
      <ul style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 22, flex: 1 }}>
        {tier.features.map(f => (
          <li key={f} style={{ display: 'flex', gap: 9, fontSize: 14, lineHeight: 1.45 }}>
            <Check size={15} weight="bold" style={{ color: tier.color, flexShrink: 0, marginTop: 3 }} />
            <span style={{ color: isPro ? 'rgba(255,255,255,0.85)' : '#3F3F46' }}>{f}</span>
          </li>
        ))}
      </ul>
      <button
        onClick={() => document.getElementById('intake-form')?.scrollIntoView({ behavior: 'smooth' })}
        style={{
          width: '100%', padding: '11px 16px', borderRadius: 10, fontSize: 14, fontWeight: 600,
          background: isPro
            ? 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)'
            : tier.color,
          color: isPro ? '#1F1407' : 'white',
          border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          transition: 'transform 0.15s',
        }}
        onMouseOver={e => (e.currentTarget.style.transform = 'translateY(-1px)')}
        onMouseOut={e => (e.currentTarget.style.transform = 'translateY(0)')}>
        {tier.cta} <ArrowRight size={13} weight="bold" />
      </button>
    </motion.div>
  )
}

function Field({ label, type = 'text', value, onChange, required }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: INK, marginBottom: 6 }}>{label}</label>
      <input type={type} required={required} value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', padding: '10px 12px', border: '1px solid #E4E4E7',
          borderRadius: 8, fontSize: 14, color: INK, outline: 'none', fontFamily: 'inherit',
        }} />
    </div>
  )
}

export default function MakelaarsPage() {
  const [form, setForm] = useState({ name: '', email: '', phone: '', company: '', tier: 'pro', message: '' })
  const [sent, setSent] = useState(false)
  const [sending, setSending] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setSending(true)
    await new Promise(r => setTimeout(r, 800))
    setSent(true)
    setSending(false)
  }

  return (
    <div style={{ background: 'white', fontFamily: 'Geist, system-ui, sans-serif' }} className="min-h-[100dvh]">

      {/* ─────────── HERO ─────────── */}
      <section style={{ background: DARK, paddingTop: 120, paddingBottom: 80, position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: '-20%', right: '-10%', width: '60%', height: '120%',
          background: 'radial-gradient(ellipse at center, rgba(212,162,76,0.18) 0%, transparent 60%)',
          pointerEvents: 'none',
        }} />
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8" style={{ position: 'relative' }}>
          <motion.div {...slideUp(0)} className="flex items-center gap-2 mb-6">
            <span style={{ background: 'rgba(212,162,76,0.12)', border: '1px solid rgba(212,162,76,0.35)', color: GOLD }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold backdrop-blur-sm">
              <Cube size={11} weight="fill" />
              Voor makelaars op Curaçao
            </span>
          </motion.div>

          <motion.h1 {...slideUp(0.05)}
            style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.05 }}
            className="text-4xl md:text-6xl lg:text-7xl max-w-[800px] mb-6">
            Verkoop sneller.<br />
            <span style={{ color: GOLD }}>Met fotorealistische 3D-tours.</span>
          </motion.h1>

          <motion.p {...slideUp(0.10)}
            style={{ color: 'rgba(255,255,255,0.72)', maxWidth: 620 }}
            className="text-base md:text-xl leading-relaxed mb-10">
            Kopers willen vandaag huizen vooraf bekijken — zonder afspraak. Geef ze een fotorealistische 3D-tour en zie het verschil: meer leads, meer kwalitatieve bezichtigingen, snellere verkoop.
          </motion.p>

          <motion.div {...slideUp(0.15)} className="flex flex-wrap gap-3">
            <button
              onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })}
              style={{
                background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
                color: '#1F1407', fontWeight: 700, boxShadow: '0 6px 20px rgba(212,162,76,0.4)',
              }}
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl text-sm hover:opacity-95 transition-opacity">
              Bekijk pakketten <ArrowRight size={14} weight="bold" />
            </button>
            <Link to={DEMO_LISTING}
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)', color: 'white', fontWeight: 600 }}
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl text-sm hover:bg-white/15 transition-colors backdrop-blur-sm">
              <Eye size={14} weight="bold" /> Bekijk voorbeeld-tour
            </Link>
          </motion.div>

          <motion.div {...slideUp(0.2)} style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
            className="grid grid-cols-2 md:grid-cols-3 gap-6 mt-12 pt-10 max-w-[700px]">
            {[
              { v: '687', l: 'actieve listings op KasKorsou' },
              { v: '<48u', l: 'van scan tot live op platform' },
              { v: '0%', l: 'lokale concurrentie (Matterport ontbreekt)' },
            ].map(s => (
              <div key={s.l}>
                <p style={{ color: GOLD, fontWeight: 800, letterSpacing: '-0.03em' }} className="text-2xl md:text-3xl">{s.v}</p>
                <p style={{ color: 'rgba(255,255,255,0.5)' }} className="text-xs md:text-sm mt-1">{s.l}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ─────────── PROBLEEM / OPLOSSING ─────────── */}
      <section style={{ padding: '80px 0', background: SAND }}>
        <div className="max-w-[1100px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="text-center mb-14">
            <p style={{ color: CORAL, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-3">De realiteit op Curaçao</p>
            <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-5xl">
              Waarom video's niet meer<br />genoeg zijn
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6">
            <motion.div {...slideUp(0.05)}
              style={{ background: 'white', border: '1px solid #E4E4E7', borderRadius: 18, padding: 32 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FEE2E2', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>
                <X size={18} weight="bold" style={{ color: '#DC2626' }} />
              </div>
              <h3 style={{ color: INK, fontWeight: 700, fontSize: 20, marginBottom: 14 }}>Wat nu gebeurt</h3>
              <ul style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {PROBLEMS.map(p => (
                  <li key={p} style={{ display: 'flex', gap: 10, color: '#52525B', fontSize: 14, lineHeight: 1.5 }}>
                    <span style={{ color: '#DC2626', fontWeight: 700, flexShrink: 0 }}>—</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </motion.div>

            <motion.div {...slideUp(0.1)}
              style={{
                background: DARK, color: 'white', borderRadius: 18, padding: 32,
                border: `1.5px solid ${GOLD}`, boxShadow: '0 12px 36px -12px rgba(212,162,76,0.35)',
              }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14,
              }}>
                <Cube size={18} weight="fill" style={{ color: '#1F1407' }} />
              </div>
              <h3 style={{ color: 'white', fontWeight: 700, fontSize: 20, marginBottom: 14 }}>Met een 3D-tour op KasKorsou</h3>
              <ul style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {SOLUTIONS.map(s => (
                  <li key={s} style={{ display: 'flex', gap: 10, color: 'rgba(255,255,255,0.85)', fontSize: 14, lineHeight: 1.5 }}>
                    <Check size={15} weight="bold" style={{ color: GOLD, flexShrink: 0, marginTop: 3 }} />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ─────────── HOE HET WERKT ─────────── */}
      <section style={{ padding: '80px 0', background: 'white' }}>
        <div className="max-w-[1100px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="text-center mb-14">
            <p style={{ color: TEAL, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-3">Hoe het werkt</p>
            <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-5xl">
              Van afspraak tot live op platform.<br />Binnen 48 uur.
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-5">
            {STEPS.map((step, i) => {
              const Icon = step.icon
              return (
                <motion.div key={step.n} {...slideUp(i * 0.07)}
                  style={{ background: SAND, borderRadius: 18, padding: 28, position: 'relative', overflow: 'hidden' }}>
                  <span style={{
                    position: 'absolute', top: 14, right: 18, fontSize: 64, fontWeight: 900,
                    color: 'rgba(0,107,125,0.08)', letterSpacing: '-0.05em', lineHeight: 1,
                  }}>{step.n}</span>
                  <div style={{
                    width: 44, height: 44, borderRadius: 12, background: 'white', color: TEAL,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 18,
                    position: 'relative', boxShadow: '0 2px 6px rgba(0,107,125,0.12)',
                  }}>
                    <Icon size={22} weight="duotone" />
                  </div>
                  <h3 style={{ color: INK, fontWeight: 700, fontSize: 19, letterSpacing: '-0.01em', marginBottom: 10, position: 'relative' }}>
                    {step.title}
                  </h3>
                  <p style={{ color: '#52525B', fontSize: 14, lineHeight: 1.55, position: 'relative' }}>{step.desc}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ─────────── PRICING ─────────── */}
      <section id="pricing" style={{ padding: '80px 0', background: SAND }}>
        <div className="max-w-[1300px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="text-center mb-14">
            <p style={{ color: GOLD, fontWeight: 600, letterSpacing: '0.1em' }}
              className="text-xs uppercase mb-3 flex items-center justify-center gap-1.5">
              <Sparkle size={11} weight="fill" />Pakketten
            </p>
            <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-5xl">
              Kies wat past bij jouw schaal
            </h2>
            <p style={{ color: '#52525B', maxWidth: 580, margin: '14px auto 0' }} className="text-base md:text-lg">
              Single scan voor één listing, abonnement voor kantoren met volume, of een retainer voor resort-ontwikkelaars in bouwfase.
            </p>
          </motion.div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
            {TIERS.map((tier, i) => <TierCard key={tier.id} tier={tier} idx={i} />)}
          </div>

          <motion.p {...slideUp(0.2)} style={{ color: '#71717A', textAlign: 'center', marginTop: 32, fontSize: 13 }}>
            Alle prijzen in XCG (Caribbean Guilder) excl. OB. Geen setupkosten, maandelijks opzegbaar.
          </motion.p>
        </div>
      </section>

      {/* ─────────── DEMO ─────────── */}
      <section style={{ padding: '80px 0', background: DARK }}>
        <div className="max-w-[1100px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="text-center mb-12">
            <p style={{ color: GOLD, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-3">Bekijk het verschil</p>
            <h2 style={{ color: 'white', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-5xl">
              Zo ziet een Premium listing eruit
            </h2>
            <p style={{ color: 'rgba(255,255,255,0.6)', maxWidth: 560, margin: '14px auto 0' }} className="text-base">
              Bekijk live op KasKorsou een voorbeeld-listing met 3D-tour. Loop door de woning, zoom in, draai rond — alles vanuit je browser.
            </p>
          </motion.div>
          <motion.div {...slideUp(0.05)} className="flex flex-wrap justify-center gap-3">
            <Link to={DEMO_LISTING}
              style={{
                background: 'linear-gradient(135deg, #E8B547 0%, #D4A24C 50%, #B5862E 100%)',
                color: '#1F1407', fontWeight: 700,
              }}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm hover:opacity-95 transition-opacity">
              <Eye size={14} weight="bold" /> Open voorbeeld in nieuwe tab
            </Link>
            <Link to="/search?scan=1"
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', fontWeight: 600 }}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm hover:bg-white/15 transition-colors">
              Zie alle 3D-tours <ArrowRight size={13} weight="bold" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ─────────── FAQ ─────────── */}
      <section style={{ padding: '80px 0', background: 'white' }}>
        <div className="max-w-[820px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="mb-10">
            <p style={{ color: TEAL, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-3">Veelgestelde vragen</p>
            <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-4xl">
              Eerst even wat checken?
            </h2>
          </motion.div>
          <motion.div {...slideUp(0.05)}>
            {FAQS.map((faq, i) => (
              <FaqItem key={faq.q} q={faq.q} a={faq.a} defaultOpen={i === 0} />
            ))}
          </motion.div>
        </div>
      </section>

      {/* ─────────── INTAKE FORM ─────────── */}
      <section id="intake-form" style={{ padding: '80px 0', background: SAND }}>
        <div className="max-w-[640px] mx-auto px-5 lg:px-8">
          <motion.div {...slideUp(0)} className="text-center mb-10">
            <p style={{ color: CORAL, fontWeight: 600, letterSpacing: '0.1em' }} className="text-xs uppercase mb-3">Begin vandaag</p>
            <h2 style={{ color: INK, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1 }} className="text-3xl md:text-4xl">
              Plan een kennismaking
            </h2>
            <p style={{ color: '#52525B', marginTop: 12 }} className="text-base">
              Vul het formulier in en we nemen binnen 24 uur contact op. Geen verplichtingen.
            </p>
          </motion.div>

          {sent ? (
            <motion.div {...slideUp(0)}
              style={{ background: 'white', border: `1.5px solid ${TEAL}`, borderRadius: 18, padding: 40, textAlign: 'center' }}>
              <div style={{
                width: 56, height: 56, borderRadius: '50%', background: '#E6F2F4', color: TEAL,
                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
              }}>
                <Check size={26} weight="bold" />
              </div>
              <h3 style={{ color: INK, fontWeight: 800, fontSize: 22, marginBottom: 8 }}>
                Bedankt — we nemen binnen 24u contact op
              </h3>
              <p style={{ color: '#52525B', fontSize: 14 }}>
                Je hoort binnenkort van ons via {form.email || 'e-mail'}.
              </p>
            </motion.div>
          ) : (
            <motion.form {...slideUp(0.05)} onSubmit={handleSubmit}
              style={{ background: 'white', borderRadius: 18, padding: 32, border: '1px solid #E4E4E7' }}>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <Field label="Naam *" required value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} />
                <Field label="Bedrijf / kantoor" value={form.company} onChange={v => setForm(f => ({ ...f, company: v }))} />
                <Field label="E-mail *" type="email" required value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} />
                <Field label="Telefoon" type="tel" value={form.phone} onChange={v => setForm(f => ({ ...f, phone: v }))} />
              </div>
              <div className="mb-4">
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: INK, marginBottom: 6 }}>
                  Welk pakket interesseert je?
                </label>
                <div className="flex flex-wrap gap-2">
                  {TIERS.map(tier => (
                    <button key={tier.id} type="button"
                      onClick={() => setForm(f => ({ ...f, tier: tier.id }))}
                      style={{
                        padding: '8px 14px', borderRadius: 999, fontSize: 13, fontWeight: 500,
                        border: form.tier === tier.id ? `1.5px solid ${TEAL}` : '1px solid #E4E4E7',
                        background: form.tier === tier.id ? '#E6F2F4' : 'white',
                        color: form.tier === tier.id ? TEAL : '#52525B',
                        transition: 'all 0.15s',
                      }}>
                      {tier.name}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mb-5">
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: INK, marginBottom: 6 }}>
                  Bericht (optioneel)
                </label>
                <textarea value={form.message}
                  onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                  rows={3}
                  placeholder="Hoeveel listings? Welke buurten? Specifieke vragen?"
                  style={{
                    width: '100%', padding: '10px 12px', border: '1px solid #E4E4E7',
                    borderRadius: 8, fontSize: 14, color: INK, fontFamily: 'inherit',
                    outline: 'none', resize: 'vertical',
                  }} />
              </div>
              <button type="submit" disabled={sending}
                style={{
                  width: '100%', padding: '13px 16px', borderRadius: 11,
                  background: sending ? '#A1A1AA' : INK, color: 'white',
                  fontWeight: 600, fontSize: 14, border: 'none',
                  cursor: sending ? 'wait' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'background 0.15s',
                }}>
                {sending ? 'Versturen...' : <>Verstuur aanvraag <ArrowRight size={14} weight="bold" /></>}
              </button>
              <p style={{ color: '#A1A1AA', fontSize: 11, textAlign: 'center', marginTop: 12 }}>
                We bewaren je gegevens nooit langer dan nodig en delen ze niet met derden.
              </p>
            </motion.form>
          )}
        </div>
      </section>

      {/* ─────────── FOOTER ─────────── */}
      <section style={{ padding: '40px 0', background: DARK, color: 'white' }}>
        <div className="max-w-[1200px] mx-auto px-5 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p style={{ color: 'rgba(255,255,255,0.55)' }} className="text-xs">
            KasKorsou — Vastgoedplatform Curaçao · Built by Lazy Lizard AI
          </p>
          <div className="flex items-center gap-4 text-xs">
            <Link to="/" style={{ color: 'rgba(255,255,255,0.8)' }}>Naar KasKorsou</Link>
            <a href="mailto:peter@lazylizardgroup.com" style={{ color: GOLD }}>peter@lazylizardgroup.com</a>
          </div>
        </div>
      </section>
    </div>
  )
}
