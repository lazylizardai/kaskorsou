// KasKorsou — valuta-utils
//
// Curaçao heeft een vaste koppeling: 1 USD = 1,79 XCG. ANG (Nederlandse
// Antilliaanse gulden) is in 2026 vervangen door XCG (Caribische gulden) —
// zelfde waarde, alleen de naam veranderde. Overal waar de data nog
// currency 'ANG' heeft (oudere scrape-rijen) tonen we dus gewoon XCG.
//
// Listings staan in hun eigen, native valuta (wat de makelaar/scraper zelf
// gebruikte — XCG of USD), we rekenen NIET om voor weergave. Voor filteren
// en sorteren rekenen we wel alles om naar één canonieke eenheid (USD) zodat
// een XCG-huis correct meetelt in een USD-bereik en vice versa.

export const USD_TO_XCG = 1.79

function isUsd(currency) {
  return currency === 'USD' || currency === '$'
}

// Rekent een prijs om naar USD-equivalent, voor filteren/sorteren.
export function toUSD(price, currency) {
  if (price == null || Number.isNaN(Number(price))) return null
  const n = Number(price)
  return isUsd(currency) ? n : n / USD_TO_XCG
}

// Rekent een prijs om naar XCG-equivalent (voor de valuta-switch in de filter).
export function toXCG(price, currency) {
  if (price == null || Number.isNaN(Number(price))) return null
  const n = Number(price)
  return isUsd(currency) ? n * USD_TO_XCG : n
}

const nf = new Intl.NumberFormat('nl-NL')

// Toont een prijs in de eigen valuta van de listing — nooit omgerekend, en
// altijd het volledige bedrag (190.000 / 1.200.000), nooit afgekort tot
// "1.2M" — Peter wil de exacte bedragen kunnen lezen.
export function formatPrice(price, currency, listingType) {
  const usd = isUsd(currency)
  if (price == null || Number.isNaN(Number(price))) {
    return listingType ? (usd ? '$ –' : '– XCG') : 'Prijs op aanvraag'
  }
  const n = Math.round(Number(price))
  const amount = nf.format(n)
  const base = usd ? `$ ${amount}` : `${amount} XCG`
  return listingType === 'rent' ? `${base}/mnd` : base
}

// Compacte notatie voor sliders/badges: "150k", "1.2M" (zonder symbool).
export function formatCompact(price) {
  if (price == null || Number.isNaN(Number(price))) return '–'
  const n = Number(price)
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  return `${(n / 1000).toFixed(0)}k`
}
