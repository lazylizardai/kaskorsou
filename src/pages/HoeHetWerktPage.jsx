import LegalLayout from '../components/LegalLayout'

const UPDATED = '14 augustus 2026'

const SECTIONS = [
  {
    title: 'Waarom KasKorsou bestaat',
    blocks: [
      { type: 'p', text: 'Wie op Curaçao een huis zoekt, is al snel een middag kwijt. Het aanbod staat verspreid over tientallen makelaarswebsites, een handvol projectsites en de openbare advertenties op sociale media. Elke site heeft zijn eigen zoekfilters, zijn eigen valuta en zijn eigen idee van wat een "wijk" is. Vergelijken is bijna onmogelijk, en het aanbod dat je niet toevallig tegenkomt, bestaat voor jou simpelweg niet.' },
      { type: 'p', text: 'KasKorsou lost dat op door dat verspreide aanbod op één plek te verzamelen, één taal te laten spreken en doorzoekbaar te maken. Je zoekt op prijs, wijk, type en aantal slaapkamers over alle aanbieders heen, en klikt vervolgens door naar de makelaar zelf.' },
      { type: 'note', text: 'Wij zijn een zoekmachine, geen makelaar. Wij verkopen niets, wij verhuren niets en wij rekenen geen courtage. Het contact en de transactie lopen altijd rechtstreeks tussen jou en de aanbieder.' },
    ],
  },
  {
    id: 'bronnen',
    title: 'Waar het aanbod vandaan komt',
    blocks: [
      { type: 'p', text: 'Het aanbod op KasKorsou is niet door ons bedacht of ingetypt. Het wordt geautomatiseerd opgehaald bij bronnen die het zelf openbaar op internet zetten:' },
      { type: 'ul', items: [
        'Ruim veertig makelaarskantoren, projectontwikkelaars en verhuurorganisaties op Curaçao, rechtstreeks van hun eigen website.',
        'Openbare advertenties op sociale media en marktplaatsen — waaronder Facebook Marketplace en openbare Facebook-pagina\'s waar woningen worden aangeboden. Zo komt ook particulier aanbod in beeld dat nergens anders terechtkomt.',
        'Gegevens die makelaars ons zelf aanleveren of via hun profiel laten aanpassen.',
      ] },
      { type: 'p', text: 'Elke nacht draait het verzamelproces opnieuw, zodat prijswijzigingen en nieuw aanbod binnen een dag zichtbaar zijn en verdwenen advertenties uit de zoekresultaten gaan.' },
      { type: 'h3', text: 'Wat wij bewust niet doen' },
      { type: 'ul', items: [
        'Wij halen niets op achter een inlogscherm, betaalmuur of technische beveiliging.',
        'Wij respecteren de robots.txt van elke bronsite. Staat er dat een site niet opgehaald mag worden, dan slaan wij die over — ook als dat ons aanbod kost.',
        'Wij belasten bronsites zo min mogelijk: rustig tempo, één keer per etmaal, geen piekverkeer.',
        'Wij nemen foto\'s niet over als eigen materiaal. Ze worden getoond vanaf de bron, en elke advertentie linkt naar het origineel.',
        'Wij tonen geen contactgegevens van particulieren die die zelf niet in hun advertentie hebben gezet.',
      ] },
    ],
  },
  {
    title: 'Van bron naar zoekresultaat',
    blocks: [
      { type: 'h3', text: 'Stap 1 — Ophalen' },
      { type: 'p', text: 'Per bron draait een eigen script dat de openbaar zichtbare advertentiepagina\'s uitleest: titel, prijs, type, aantal slaapkamers, oppervlakte, ligging en de link naar het origineel.' },
      { type: 'h3', text: 'Stap 2 — Gelijk trekken' },
      { type: 'p', text: 'De ene site schrijft "ANG 450.000", de andere "US$ 250K", de derde zet de prijs in een plaatje. Wij zetten alles om naar een vergelijkbaar formaat, koppelen wijknamen aan elkaar en delen woningen in op type. Waar wij omrekenen tussen USD en XCG gebruiken wij de vaste koers van 1 USD = 1,79 XCG.' },
      { type: 'h3', text: 'Stap 3 — Dubbelingen eruit' },
      { type: 'p', text: 'Eén woning staat vaak bij meerdere kantoren én op Facebook. Wij herkennen die dubbelingen en tonen er één, met de website van de makelaar als voorkeursbron.' },
      { type: 'h3', text: 'Stap 4 — Terug naar de bron' },
      { type: 'p', text: 'Elke advertentie op KasKorsou bevat de naam van de aanbieder en een link naar de originele pagina. Wij houden bezoekers niet vast: het doel is dat je bij de makelaar terechtkomt.' },
      { type: 'note', text: 'Wij verifiëren de inhoud niet. Prijzen, oppervlaktes en beschikbaarheid komen precies zo binnen als de bron ze publiceert, met de fouten die daarin kunnen zitten. Controleer altijd bij de makelaar voordat je een beslissing neemt.' },
    ],
  },
  {
    title: 'Wat dit oplevert voor makelaars',
    blocks: [
      { type: 'p', text: 'Een makelaar hoeft niets te doen om in KasKorsou te staan, en betaalt er niets voor. Het aanbod krijgt extra zichtbaarheid en het verkeer gaat naar de eigen website, niet naar een concurrent.' },
      { type: 'p', text: 'Daarnaast bieden wij betaalde diensten aan: een uitgelichte plaatsing, een eigen profielpagina, 3D-scans en videotours. Dat is een keuze, geen voorwaarde. Wie niets afneemt staat er net zo goed in, en betaalde plaatsingen verdringen het gewone aanbod niet uit de zoekresultaten.' },
    ],
  },
  {
    id: 'pand-verwijderen',
    title: 'Een pand of kantoor laten verwijderen',
    blocks: [
      { type: 'p', text: 'Wil je niet in KasKorsou staan, dan haal je jezelf eruit met één e-mail. Je hoeft geen reden te geven en er volgt geen verkoopgesprek.' },
      { type: 'ul', items: [
        'Mail naar peter@lazylizardgroup.com met de link naar de advertentie, of met de naam en website van je kantoor als het om je hele aanbod gaat.',
        'Wij verwijderen de advertenties binnen vijf werkdagen.',
        'Je website gaat op onze uitsluitingslijst, zodat er ook geen nieuw aanbod meer wordt opgehaald.',
        'Alleen een correctie kan ook: een verkeerde prijs, een verouderde foto of een verkeerd toegewezen kantoornaam.',
      ] },
      { type: 'p', text: 'Hetzelfde geldt voor eigenaren en particuliere aanbieders: staat jouw woning erop en wil je dat niet, dan is één bericht genoeg.' },
    ],
  },
  {
    title: 'Waarom wij hier open over zijn',
    blocks: [
      { type: 'p', text: 'Een platform dat andermans aanbod verzamelt hoort daar helder over te zijn. Daarom staat op elke advertentie wie de aanbieder is, staat er een link naar het origineel, en kan iedereen er met één mail weer uit.' },
      { type: 'p', text: 'Wij verzamelen feitelijke gegevens uit openbare advertenties — prijs, ligging, aantal kamers — en tonen die met bronvermelding. Wij verkopen de verzamelde data niet door, en wij presenteren het aanbod van een ander nooit als het onze.' },
      { type: 'p', text: 'Zie je iets op het platform waarvan je vindt dat het er niet hoort, dan horen wij dat graag. Wij passen het aan.' },
    ],
  },
]

export default function HoeHetWerktPage() {
  return (
    <LegalLayout
      eyebrow="Hoe het werkt"
      title="Hoe KasKorsou werkt"
      intro="Waar het woningaanbod vandaan komt, wat wij er wel en niet mee doen, en hoe je jouw aanbod er met één e-mail weer af haalt."
      updated={UPDATED}
      sections={SECTIONS}
      metaDescription="Hoe KasKorsou werkt: het woningaanbod van Curaçao wordt dagelijks verzameld uit openbare bronnen van makelaars en sociale media, met bronvermelding en een link naar het origineel."
      canonical="https://kaskorsou.lazylizardai.com/hoe-het-werkt"
    />
  )
}
