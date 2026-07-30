# Dealbot — takenlijst

Bijgewerkt: 30-07-2026

## Fase 1 — de minimale basis (nu)

- [x] Database inrichten in Supabase (gebruikers, zoekvragen, aanbiedingen, logboek)
- [x] Inloggen met e-mailadres + pincode van 4 cijfers; mensen mogen zichzelf aanmelden
- [x] Ophaalscript Albert Heijn — 1024 weekaanbiedingen, 99% met kiloprijs
- [ ] Ophaalscript Jumbo
- [ ] Uitzoeken of Nettorama betrouwbaar uit te lezen is (folder, geen prijzenlijst)
- [x] Automatisch elke ochtend laten draaien via GitHub — 07:00, duurt een halve minuut
- [x] Oude aanbiedingen pas opruimen nadat de nieuwe binnen zijn
- [x] Prijs per kilo/liter berekenen; lukt dat niet, dan onderaan met de melding "kiloprijs onbekend"
- [x] Startpagina: persoonlijke aanbiedingen, gegroepeerd per product, goedkoop naar duur
- [x] Profielpagina: zoekvragen bekijken, toevoegen en verwijderen (merk, variant, vrije tekst)
- [x] Melding als er deze week geen aanbiedingen zijn, met link naar de standaardprijzen-pagina
- [ ] Testknop op de site om het ophalen handmatig te starten (via Supabase, zodat er geen sleutel op de openbare pagina staat) — gaat er na de testfase weer uit

## Fase 2 — later

- [ ] **E-mailbericht sturen zodra er een aanbieding is die bij iemands profiel past.** Let op: hiervoor is een extra gratis maildienst nodig, Supabase mag zelf alleen inlog-mails versturen
- [ ] Bevestigingsmail bij het aanmelden van een nieuw account
- [ ] In het profiel kunnen aanvinken bij welke winkels je daadwerkelijk komt, zodat je geen
      aanbiedingen ziet van een winkel dertig kilometer verderop
- [ ] Meer winkels: Bol, Amazon, Dirk, Plus, Lidl, Aldi, Hoogvliet, Vomar, DekaMarkt, Picnic
- [ ] Zoeken op productgroep, met een achtergrondlijst van producten en EAN-codes
- [ ] De standaardprijzen-pagina bouwen
- [ ] Keuzelijsten in het profielscherm in plaats van vrije tekst
- [ ] Geschikt maken voor een mobiele app

## Nog uit te zoeken

- [ ] Nettorama: alleen digitale folder beschikbaar? Zo ja, hoe betrouwbaar is dat uit te lezen?
- [ ] Verschillen de aanbiedingen per filiaal in de regio Utrecht / Noord-Holland?
