# Wijzigingen — Dealbot

## 31-07-2026 (ochtend) — knop om de 07.00-run met de hand te starten

- Op de startpagina staat tijdelijk een blokje **07.00-run**. Daarmee is de
  dagelijkse ophaalronde meteen te starten, zodat een testresultaat niet tot de
  volgende ochtend hoeft te wachten.
- De knop opent GitHub, waar de run met één klik begint. Dat is met opzet zo:
  de sleutel die zo'n run mag starten hoort niet in een openbare website. Ernaast
  staat een knop om de pagina te verversen zodra de run klaar is.
- Bedoeld om er weer uit te halen: de sectie in `index.html`, `assets/handrun.js`
  en het blokje `.handrun` in `assets/stijl.css`.

## 31-07-2026 (nacht) — drie zoekvelden die elk hun eigen ding doen

- **Het krat Amstel bij "koffie" is weg.** Vrije tekst zocht ook in de
  productgroep van de winkel, en bij Dirk heet die groep "Dranken, sap, koffie
  & thee". Daardoor kwam er bier, thee en frisdrank mee. Vrije tekst kijkt nu
  alleen nog naar het merk en de productnaam. Gemeten in de lijst van deze week:
  "koffie" gaf 136 treffers, waarvan 100 vals; er blijven er 36 over.
- **"Variant" heet voortaan "Productgroep".** In dat veld stond altijd al de
  indeling van de winkel zelf, niet een variant als "espresso". De naam wekte
  de verkeerde verwachting: wie "merk Lavazza + variant oro" invulde, kreeg
  niets.
- **De productgroep is een keuzelijst geworden**, gevuld met de groepen die deze
  week écht in de aanbiedingen zitten, met het aantal erbij. Je kunt dus geen
  groep meer kiezen die niets oplevert.
- Die lijst staat per winkel gegroepeerd, omdat elke keten anders indeelt:
  Albert Heijn tot op "Toiletpapier - vochtig", Jumbo en Dirk niet verder dan
  "Koffie en thee". Kies je een groep, dan zoek je dus binnen één winkel. Het
  aan elkaar knopen van die indelingen blijft werk voor fase 2.
- Het profielscherm zegt nu onder elk veld waar dat veld op zoekt, en zet "én"
  tussen de delen van een zoekvraag: binnen één zoekvraag moeten ze allemaal
  kloppen.
- Bestaande zoekvragen zijn meeverhuisd: stond er bij "variant" een woord dat
  geen echte productgroep is, dan is het naar vrije tekst gegaan in plaats van
  te verdwijnen.

## 31-07-2026 — van één naar drie winkels

- **Jumbo erbij**: 1242 weekaanbiedingen, waarvan 99,7% met een kilo- of
  literprijs. Zit een product in meer dan één actie, dan blijft de goedkoopste
  staan.
- **Dirk van den Broek erbij**: 417 aanbiedingen, 94% met een kilo- of
  literprijs.
- Vomar valt af als bron van aanbiedingen. Hun productlijst is prima, maar de
  aanbiedingen staan alleen in een digitale folder: plaatjes met losse
  tekstflarden. Daar is geen betrouwbare koppeling product–prijs–inhoud uit te
  halen. Vomar blijft wél interessant voor de standaardprijzen-pagina later.
- Nieuwe aanbiedingsvorm herkend: een bedrag korting in euro's ("1,00 korting").
  Die werd eerst niet omgerekend, waardoor zo'n aanbieding de normale prijs hield.
- Producten met een onmogelijke prijs (een paar cent voor een kilo kaas) blijven
  buiten de lijst; dat is een fout bij de winkel en zou de lijst aanvoeren.
- Samen staan er nu ruim 2600 aanbiedingen klaar, opgehaald in een halve minuut.

## 30-07-2026 (avond) — de website staat

- Inloggen werkt met e-mailadres en een pincode van vier cijfers. Wie nog geen
  account heeft, kan zich op hetzelfde scherm aanmelden.
- Startpagina toont de aanbiedingen die bij je eigen zoekvragen passen,
  per product bij elkaar en van goedkoop naar duur.
- Staat er bij een product een los pak naast een voordeelpak, dan wijst de
  pagina géén "beste prijs" aan: die prijzen zijn niet eerlijk te vergelijken.
- Zijn er geen aanbiedingen, dan legt de pagina uit waarom: nog geen zoekvragen
  ingevuld, of deze week even niets, met een link naar de standaardprijzen.
- Profielpagina om zoekvragen te bekijken, toe te voegen en te verwijderen.
- De pagina met standaardprijzen bestaat alvast als lege pagina, zodat de
  verwijzing vanaf de startpagina niet doodloopt.

## 30-07-2026

- Database ingericht in Supabase, inclusief de regel dat niemand bij de
  zoekvragen van een ander kan.
- Ophalen van de weekaanbiedingen van Albert Heijn werkt: 1024 aanbiedingen,
  waarvan 99% met een berekende kilo- of literprijs.
- Permanente staffelkortingen op multipacks worden overgeslagen; dat zijn geen
  weekaanbiedingen.
- Het ophalen draait nu elke ochtend om 07:00 vanzelf op GitHub en is met de
  hand te starten. Eerste automatische ronde geslaagd in 32 seconden.
- Logboek toegevoegd: per ophaalronde staat vast of het gelukt is en hoeveel
  aanbiedingen er binnenkwamen.

## 27-07-2026

- Projectmap gekoppeld aan de GitHub-repo `Bartloe/dealbot`.
- Functioneel ontwerp (v2.5) toegevoegd aan het project.
- Takenlijst aangemaakt, verdeeld over fase 1, fase 2 en uit te zoeken punten.
- Basiskeuzes vastgelegd: Supabase als database, inloggen met e-mail + pincode,
  dagelijks automatisch ophalen via GitHub.
