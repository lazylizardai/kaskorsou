import LegalLayout from '../components/LegalLayout'

const UPDATED = '14 augustus 2026'

const SECTIONS = [
  {
    title: 'Wie verwerkt jouw gegevens',
    blocks: [
      { type: 'p', text: 'KasKorsou is een platform van Heijvis B.V., handelend onder de naam Lazy Lizard Group, gevestigd op Curaçao. Wij zijn verantwoordelijk voor de verwerking van persoonsgegevens via deze website.' },
      { type: 'p', text: 'Wij houden ons aan de Landsverordening bescherming persoonsgegevens van Curaçao. Voor bezoekers uit de Europese Unie hanteren wij daarnaast de uitgangspunten van de AVG (GDPR).' },
      { type: 'p', text: 'Vragen over privacy? Mail naar peter@lazylizardgroup.com.' },
    ],
  },
  {
    title: 'Welke gegevens wij van jou verwerken',
    blocks: [
      { type: 'h3', text: 'Als je alleen rondkijkt' },
      { type: 'ul', items: [
        'Technische gegevens die elke website ontvangt: IP-adres, browsertype, apparaat, taal en de pagina\'s die je bekijkt. Die worden verwerkt door onze hostingpartij om de site te leveren en te beveiligen.',
        'Lokale opslag in je browser voor instellingen zoals je valutakeuze en je zoekfilters. Die gegevens blijven op jouw apparaat.',
      ] },
      { type: 'h3', text: 'Als je een account aanmaakt' },
      { type: 'ul', items: [
        'Je e-mailadres en wachtwoord (versleuteld opgeslagen, wij kunnen het niet inzien).',
        'Je naam en, als je die invult, je telefoonnummer.',
        'De woningen die je bewaart als favoriet.',
      ] },
      { type: 'h3', text: 'Als je ons mailt' },
      { type: 'ul', items: [
        'Je e-mailadres en de inhoud van je bericht, zolang dat nodig is om je vraag af te handelen.',
      ] },
      { type: 'note', text: 'Wij verkopen je gegevens niet, verhuren ze niet en gebruiken ze niet voor advertentieprofielen bij derden.' },
    ],
  },
  {
    title: 'Waarom wij die gegevens gebruiken',
    blocks: [
      { type: 'ul', items: [
        'Om het platform te laten werken: zoeken, tonen, filteren en het bewaren van favorieten.',
        'Om je account aan te maken en je te kunnen laten inloggen.',
        'Om misbruik, spam en overbelasting van de website tegen te gaan.',
        'Om te begrijpen welke onderdelen van het platform gebruikt worden, op geaggregeerd niveau.',
        'Om te voldoen aan wettelijke verplichtingen.',
      ] },
      { type: 'p', text: 'De grondslag is per geval: uitvoering van de overeenkomst (je account), ons gerechtvaardigd belang (werking en beveiliging van het platform), of jouw toestemming (bijvoorbeeld als je ons vraagt contact op te nemen).' },
    ],
  },
  {
    title: 'Gegevens van makelaars en aanbieders',
    blocks: [
      { type: 'p', text: 'Op KasKorsou staat ook informatie die betrekking kan hebben op personen die niet zelf op onze site zijn geweest: de naam van een makelaarskantoor, soms de naam van een contactpersoon, een telefoonnummer of e-mailadres, en het adres of de wijk van een aangeboden woning.' },
      { type: 'p', text: 'Die gegevens komen uit openbare advertenties die de aanbieder zelf heeft gepubliceerd, met het doel gevonden te worden door kopers en huurders. Wij verwerken ze uitsluitend om dat aanbod vindbaar te maken en om door te verwijzen naar de aanbieder.' },
      { type: 'ul', items: [
        'Wij verzamelen geen gegevens achter een inlog, betaalmuur of beveiliging.',
        'Wij tonen geen contactgegevens van particulieren die daar niet zelf voor gekozen hebben in hun advertentie.',
        'Wij gebruiken deze gegevens niet voor ongevraagde reclame aan derden.',
      ] },
      { type: 'note', text: 'Sta je erin en wil je eruit? Mail peter@lazylizardgroup.com met de link of je kantoornaam. Wij verwijderen de gegevens binnen vijf werkdagen en zorgen dat ze niet opnieuw worden opgehaald. Je hoeft geen reden te geven.' },
    ],
  },
  {
    title: 'Cookies en vergelijkbare technieken',
    blocks: [
      { type: 'p', text: 'KasKorsou gebruikt geen advertentiecookies en geen trackers van sociale netwerken of advertentienetwerken. Er is dus ook geen cookiebanner die je moet wegklikken.' },
      { type: 'h3', text: 'Wat wij wel gebruiken' },
      { type: 'ul', items: [
        'Functionele opslag in je browser om je ingelogd te houden en je voorkeuren te onthouden. Zonder die opslag werkt inloggen niet.',
        'Beveiligings- en verkeersgegevens van onze hostingpartij, om aanvallen en misbruik te blokkeren.',
      ] },
      { type: 'p', text: 'Onderdelen van derden die je pagina laden — zoals kaartmateriaal, video en foto\'s die rechtstreeks van de website van de makelaar komen — kunnen jouw IP-adres ontvangen. Daarop hebben wij geen invloed; daarvoor gelden de privacyverklaringen van die partijen.' },
    ],
  },
  {
    title: 'Met wie wij gegevens delen',
    blocks: [
      { type: 'p', text: 'Wij delen gegevens alleen met partijen die nodig zijn om het platform te laten draaien, en alleen voor dat doel:' },
      { type: 'ul', items: [
        'Onze database- en inlogdienst, waarin accounts en favorieten worden opgeslagen.',
        'Onze hosting- en beveiligingspartij, die de website uitlevert.',
        'Kaart- en videodiensten die op de website worden getoond.',
      ] },
      { type: 'p', text: 'Deze partijen staan buiten Curaçao, onder meer in de Verenigde Staten en de Europese Unie. Wij kiezen leveranciers die een passend beveiligingsniveau hanteren. Verder verstrekken wij gegevens alleen als de wet ons daartoe verplicht.' },
    ],
  },
  {
    title: 'Hoe lang wij gegevens bewaren',
    blocks: [
      { type: 'ul', items: [
        'Accountgegevens: zolang je account bestaat. Verwijder je je account, dan verwijderen wij ze binnen 30 dagen.',
        'Favorieten: zolang je account bestaat.',
        'E-mailcorrespondentie: maximaal twee jaar na het laatste contact.',
        'Technische logbestanden: maximaal twaalf maanden.',
      ] },
      { type: 'p', text: 'Advertentiegegevens van aanbieders bewaren wij zolang het aanbod actief is. Verdwijnt een advertentie bij de bron, dan wordt hij bij ons op inactief gezet en na verloop van tijd opgeruimd.' },
    ],
  },
  {
    title: 'Jouw rechten',
    blocks: [
      { type: 'p', text: 'Je hebt het recht om te weten welke gegevens wij van je hebben, en om ze te laten corrigeren of verwijderen. Ook kun je bezwaar maken tegen de verwerking en om een kopie van je gegevens vragen.' },
      { type: 'p', text: 'Stuur je verzoek naar peter@lazylizardgroup.com. Wij reageren binnen vier weken. Om te voorkomen dat wij gegevens aan de verkeerde persoon geven, kunnen wij vragen om extra bevestiging van je identiteit.' },
      { type: 'p', text: 'Ben je het niet eens met hoe wij met je gegevens omgaan, dan kun je een klacht indienen bij het College bescherming persoonsgegevens van Curaçao. Wij horen het uiteraard liever eerst zelf, zodat wij het kunnen oplossen.' },
    ],
  },
  {
    title: 'Beveiliging',
    blocks: [
      { type: 'p', text: 'De website draait volledig over een beveiligde verbinding. Wachtwoorden worden versleuteld opgeslagen en zijn voor ons niet leesbaar. De toegang tot de database is beperkt tot wat de website nodig heeft.' },
      { type: 'p', text: 'Absolute veiligheid bestaat niet. Merk je iets wat niet klopt of vind je een kwetsbaarheid, meld het dan bij peter@lazylizardgroup.com — wij pakken dat serieus op en stellen een melding op prijs.' },
    ],
  },
  {
    title: 'Kinderen',
    blocks: [
      { type: 'p', text: 'KasKorsou is niet gericht op kinderen onder de 16 jaar. Wij verzamelen niet bewust gegevens van kinderen. Denk je dat dat toch gebeurd is, laat het ons weten, dan verwijderen wij ze.' },
    ],
  },
  {
    title: 'Wijzigingen in dit privacybeleid',
    blocks: [
      { type: 'p', text: 'Verandert het platform, dan kan dit beleid meeveranderen. De actuele versie staat altijd op deze pagina met de datum van laatste wijziging bovenaan. Bij ingrijpende wijzigingen melden wij dat duidelijk op de website.' },
    ],
  },
]

export default function PrivacyPage() {
  return (
    <LegalLayout
      eyebrow="Privacy & cookies"
      title="Privacy & cookies"
      intro="Welke gegevens KasKorsou verwerkt, waarom, hoe lang wij ze bewaren en wat jouw rechten zijn. In gewone taal, zonder cookiemuur."
      updated={UPDATED}
      sections={SECTIONS}
      metaDescription="Privacybeleid van KasKorsou: welke gegevens wij verwerken, waarom, met wie wij delen, hoe lang wij bewaren en hoe je je gegevens laat verwijderen."
      canonical="https://kaskorsou.lazylizardai.com/privacy"
    />
  )
}
