import LegalLayout from '../components/LegalLayout'

const UPDATED = '14 augustus 2026'

const SECTIONS = [
  {
    title: 'Wie wij zijn en wat KasKorsou is',
    blocks: [
      { type: 'p', text: 'KasKorsou (kaskorsou.lazylizardai.com) is een vastgoedzoekmachine voor Curaçao. Het platform wordt geëxploiteerd door Heijvis B.V., handelend onder de naam Lazy Lizard Group, gevestigd op Curaçao. In deze voorwaarden bedoelen we met "wij", "ons" en "KasKorsou" die onderneming, en met "jij" iedereen die de website bezoekt of gebruikt.' },
      { type: 'p', text: 'KasKorsou brengt woningaanbod bij elkaar dat makelaars, projectontwikkelaars en particulieren zelf openbaar op internet publiceren. Wij tonen een samenvatting en verwijzen je door naar de oorspronkelijke aanbieder.' },
      { type: 'note', text: 'KasKorsou is geen makelaar, geen bemiddelaar en geen taxateur. Wij verhuren en verkopen niets, wij zijn geen partij bij welke huur- of koopovereenkomst dan ook, en wij ontvangen geen courtage over transacties die via het platform ontstaan.' },
      { type: 'p', text: 'Door KasKorsou te gebruiken ga je akkoord met deze gebruikersvoorwaarden. Ben je het er niet mee eens, gebruik de website dan niet.' },
    ],
  },
  {
    title: 'Waar de informatie op KasKorsou vandaan komt',
    blocks: [
      { type: 'p', text: 'Vrijwel alle woninggegevens op KasKorsou zijn niet door ons gemaakt. Ze zijn geautomatiseerd verzameld van openbaar toegankelijke bronnen en vervolgens gestructureerd weergegeven. Concreet gaat het om:' },
      { type: 'ul', items: [
        'Openbare websites van makelaarskantoren, projectontwikkelaars en verhuurorganisaties op Curaçao.',
        'Openbare advertenties op sociale media en marktplaatsen, waaronder Facebook Marketplace en openbare Facebook-pagina\'s en -groepen waar woningaanbod wordt aangeboden.',
        'Gegevens die een makelaar of aanbieder ons zelf aanlevert of laat aanpassen.',
      ] },
      { type: 'p', text: 'Wij verzamelen alleen wat op het moment van ophalen openbaar zichtbaar was. Wij omzeilen geen inlogschermen, betaalmuren of technische beveiliging, en wij respecteren de robots.txt van de bronsites. Foto\'s worden niet door ons overgenomen als eigen materiaal: ze worden getoond vanaf de bron of vanaf het platform van de aanbieder, en elke advertentie bevat een link naar het origineel.' },
      { type: 'note', text: 'Het auteursrecht en alle andere rechten op advertentieteksten, foto\'s, plattegronden en video\'s blijven bij de makelaar, fotograaf of aanbieder die ze gemaakt heeft. KasKorsou claimt daar geen enkel recht op.' },
      { type: 'p', text: 'Een uitgebreidere uitleg van deze werkwijze, inclusief hoe vaak we verversen en hoe we omgaan met bezwaren, staat op de pagina "Hoe KasKorsou werkt".' },
    ],
  },
  {
    title: 'Geen garantie op juistheid — controleer altijd bij de bron',
    blocks: [
      { type: 'p', text: 'Wij doen ons best om het aanbod actueel en correct weer te geven, maar wij verifiëren de inhoud niet zelf en kunnen dat ook niet. Prijzen, oppervlaktes, aantallen kamers, ligging, beschikbaarheid en beschrijvingen kunnen verouderd, onvolledig of onjuist zijn. Aanbod kan al verkocht of verhuurd zijn terwijl het bij ons nog zichtbaar is.' },
      { type: 'p', text: 'Sommige informatie op het platform is automatisch samengevat, vertaald of verrijkt door software. Ook daarbij kunnen fouten ontstaan.' },
      { type: 'note', text: 'Alle informatie wordt aangeboden "zoals hij is" (as is). Neem nooit een beslissing over een bezichtiging, bod, huur of aankoop op basis van alleen KasKorsou. Controleer altijd rechtstreeks bij de makelaar of eigenaar.' },
      { type: 'p', text: 'Prijzen staan in XCG (Caribische gulden) of USD, zoals de bron ze toont. Waar wij omrekenen gebruiken wij een vaste koers van 1 USD = 1,79 XCG. Dat is een indicatie, geen wisselkoers waar je rechten aan kunt ontlenen.' },
    ],
  },
  {
    title: 'Wat je wel en niet mag doen op het platform',
    blocks: [
      { type: 'p', text: 'Je mag KasKorsou gratis gebruiken om woningaanbod te zoeken, te bekijken, te bewaren en te delen — voor eigen, niet-commercieel gebruik.' },
      { type: 'h3', text: 'Niet toegestaan' },
      { type: 'ul', items: [
        'Het platform of onderdelen ervan geautomatiseerd en op grote schaal uitlezen, kopiëren of hergebruiken voor een concurrerende of commerciële dienst.',
        'De website overbelasten, verstoren of beveiliging omzeilen.',
        'Contactgegevens van makelaars of aanbieders van het platform halen voor ongevraagde reclame of verkoop.',
        'Onjuiste, misleidende of onrechtmatige informatie bij ons aanleveren.',
        'Zich voordoen als een ander, of een account van iemand anders gebruiken.',
      ] },
      { type: 'p', text: 'Wij mogen de toegang tot het platform beperken of blokkeren als je deze regels overtreedt of als het gebruik de goede werking van de dienst schaadt.' },
    ],
  },
  {
    title: 'Account, favorieten en meldingen',
    blocks: [
      { type: 'p', text: 'Voor het bewaren van woningen kun je een gratis account aanmaken. Je bent zelf verantwoordelijk voor de gegevens die je invult en voor het geheimhouden van je inloggegevens. Meld het ons als je vermoedt dat iemand anders bij je account kan.' },
      { type: 'p', text: 'Je kunt je account op elk moment laten verwijderen. Wat wij met je gegevens doen staat in het privacybeleid.' },
      { type: 'p', text: 'Wij mogen een account weigeren, opschorten of verwijderen bij misbruik, of als een account langere tijd niet gebruikt is.' },
    ],
  },
  {
    title: 'Betaalde diensten voor makelaars',
    blocks: [
      { type: 'p', text: 'Naast het gratis platform bieden wij makelaars betaalde diensten aan, zoals een uitgelichte plaatsing, een eigen profielpagina en 3D-scans of videotours. Prijzen staan op de pagina "Voor makelaars" en zijn in XCG, exclusief omzetbelasting.' },
      { type: 'p', text: 'Voor die betaalde diensten geldt een aparte overeenkomst of offerte. Wijkt die af van deze voorwaarden, dan gaat die overeenkomst voor. Een betaalde plaatsing verandert niets aan de manier waarop wij het overige aanbod tonen, en koopt geen invloed op zoekresultaten die als neutraal worden gepresenteerd.' },
      { type: 'p', text: 'Het feit dat een makelaar niets betaalt, is nooit een reden om zijn aanbod te weren. Het feit dat een makelaar wel betaalt, is nooit een reden om aanbod van anderen te verbergen.' },
    ],
  },
  {
    title: 'Rechten van makelaars, eigenaren en adverteerders',
    blocks: [
      { type: 'p', text: 'Ben je makelaar, ontwikkelaar, verhuurder of particuliere aanbieder en wil je niet dat jouw aanbod op KasKorsou staat? Dat kan. Je hoeft daarvoor geen reden op te geven.' },
      { type: 'ul', items: [
        'Stuur een e-mail naar peter@lazylizardgroup.com met de link naar de advertentie of de naam van je kantoor.',
        'Wij verwijderen de betreffende advertenties binnen vijf werkdagen en zetten je website op onze uitsluitingslijst, zodat er ook geen nieuw aanbod meer wordt opgehaald.',
        'Je kunt ook vragen om alleen een correctie, bijvoorbeeld een verkeerde prijs, een verouderde foto of een verkeerd toegewezen kantoornaam.',
      ] },
      { type: 'note', text: 'Wij verwerken zo\'n verzoek zonder discussie en zonder tegenprestatie. Een verwijderverzoek is geen onderhandeling over een abonnement.' },
    ],
  },
  {
    title: 'Intellectueel eigendom van KasKorsou zelf',
    blocks: [
      { type: 'p', text: 'De naam KasKorsou, het logo, de vormgeving, de software, de kaarten en 3D-weergaves, de zoekfunctionaliteit en de door ons gemaakte teksten zijn eigendom van Heijvis B.V. of van onze licentiegevers. Je mag die niet kopiëren, verveelvoudigen of commercieel hergebruiken zonder schriftelijke toestemming.' },
      { type: 'p', text: 'Materiaal dat je zelf bij ons aanlevert blijft van jou. Door het aan te leveren geef je ons wel het recht om het op het platform en in promotie van het platform te tonen, totdat je het verzoek doet dat te stoppen.' },
    ],
  },
  {
    title: 'Links en diensten van derden',
    blocks: [
      { type: 'p', text: 'KasKorsou bevat links naar websites van makelaars, sociale media en andere partijen, en gebruikt diensten van derden voor onder meer kaarten, video en hosting. Wij hebben geen controle over die websites en diensten en zijn niet verantwoordelijk voor hun inhoud, hun beschikbaarheid of hun omgang met jouw gegevens. Daarvoor gelden hun eigen voorwaarden.' },
    ],
  },
  {
    title: 'Aansprakelijkheid',
    blocks: [
      { type: 'p', text: 'KasKorsou wordt kosteloos en zonder garanties aangeboden. Wij zijn niet aansprakelijk voor schade die ontstaat door het gebruik van het platform of door het vertrouwen op informatie die erop staat. Dat geldt onder meer voor onjuiste of verouderde advertentiegegevens, gemiste kansen, transacties die niet doorgaan, en storingen of onbereikbaarheid van de website.' },
      { type: 'p', text: 'Wij zijn evenmin aansprakelijk voor het handelen van makelaars, verkopers, verhuurders of andere gebruikers met wie je via het platform in contact komt.' },
      { type: 'p', text: 'Voor zover wij toch aansprakelijk zouden zijn, is die aansprakelijkheid beperkt tot directe schade en tot maximaal het bedrag dat je in de zes maanden voorafgaand aan het schadeveroorzakende feit aan ons hebt betaald — voor gratis gebruikers is dat nihil. Aansprakelijkheid voor opzet of bewuste roekeloosheid van onze kant wordt niet uitgesloten.' },
    ],
  },
  {
    title: 'Beschikbaarheid en wijzigingen',
    blocks: [
      { type: 'p', text: 'Wij mogen het platform, de functionaliteit en het aanbod op elk moment aanpassen, tijdelijk stopzetten of beëindigen. Wij streven naar een goede beschikbaarheid maar garanderen geen ononderbroken werking.' },
      { type: 'p', text: 'Deze voorwaarden kunnen wij wijzigen. De actuele versie staat altijd op deze pagina, met de datum van laatste wijziging bovenaan. Blijf je het platform gebruiken na een wijziging, dan geldt de nieuwe versie.' },
    ],
  },
  {
    title: 'Toepasselijk recht en geschillen',
    blocks: [
      { type: 'p', text: 'Op deze voorwaarden en op het gebruik van KasKorsou is het recht van Curaçao van toepassing. Geschillen leggen wij voor aan het Gerecht in eerste aanleg van Curaçao, voor zover de wet niet dwingend een andere rechter aanwijst.' },
      { type: 'p', text: 'Als een bepaling uit deze voorwaarden nietig of onafdwingbaar blijkt, blijven de overige bepalingen gewoon gelden.' },
    ],
  },
  {
    title: 'Contact',
    blocks: [
      { type: 'p', text: 'Heijvis B.V., handelend onder de naam Lazy Lizard Group — Curaçao.' },
      { type: 'p', text: 'E-mail: peter@lazylizardgroup.com' },
      { type: 'p', text: 'Vragen over deze voorwaarden, klachten over een advertentie of een verzoek tot verwijdering kun je naar hetzelfde adres sturen.' },
    ],
  },
]

export default function VoorwaardenPage() {
  return (
    <LegalLayout
      eyebrow="Gebruikersvoorwaarden"
      title="Gebruikersvoorwaarden"
      intro="De spelregels voor het gebruik van KasKorsou: wat wij doen, waar de gegevens vandaan komen, waar je op moet letten en hoe je aanbod laat verwijderen."
      updated={UPDATED}
      sections={SECTIONS}
      metaDescription="De gebruikersvoorwaarden van KasKorsou: wat het platform doet, waar het woningaanbod vandaan komt, aansprakelijkheid en hoe makelaars aanbod laten verwijderen."
      canonical="https://kaskorsou.lazylizardai.com/voorwaarden"
    />
  )
}
