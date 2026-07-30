# Wijzigingen — Dealbot

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
