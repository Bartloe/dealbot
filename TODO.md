# Dealbot — takenlijst

Bijgewerkt: 31-07-2026

## Fase 1 — de minimale basis (nu)

- [x] Database inrichten in Supabase (gebruikers, zoekvragen, aanbiedingen, logboek)
- [x] Inloggen met e-mailadres + pincode van 4 cijfers; mensen mogen zichzelf aanmelden
- [x] Ophaalscript Albert Heijn — 1024 weekaanbiedingen, 99% met kiloprijs
- [x] Ophaalscript Jumbo — 1242 aanbiedingen, 99,7% met kiloprijs
- [x] Derde keten: Dirk van den Broek — 417 aanbiedingen, 94% met kiloprijs.
      Vomar viel af: die publiceert zijn aanbiedingen alleen als digitale folder
- [ ] Zoekvelden herindelen: Merk, Productgroep (keuzelijst) en Vrije tekst als drie
      onafhankelijke ingangen. Alle drie de ketens leveren de productgroep mee; die
      staat nu in het veld "variant". Nu aan de beurt
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
- [ ] Meer winkels: DekaMarkt (werkt precies als Dirk, dus weinig werk), Bol, Amazon,
      Picnic. Plus, Coop, Hoogvliet en Lidl blokkeren automatisch ophalen
- [ ] Vomar gebruiken voor de standaardprijzen-pagina: hun productlijst geeft het hele
      assortiment met normale prijs, merk, inhoud én streepjescode (EAN)
- [ ] Productgroepen van de verschillende ketens aan elkaar knopen (elke keten hanteert
      een eigen indeling), eventueel met een achtergrondlijst van producten en EAN-codes
- [ ] De standaardprijzen-pagina bouwen
- [ ] Keuzelijsten in het profielscherm in plaats van vrije tekst
- [ ] Geschikt maken voor een mobiele app

## Nog uit te zoeken

- [ ] Nettorama: alleen digitale folder beschikbaar? Zo ja, hoe betrouwbaar is dat uit te lezen?
      (Bij Vomar bleek zo'n folder níet betrouwbaar uit te lezen — dat is een voorproefje)
- [ ] Verschillen de aanbiedingen per filiaal in de regio Utrecht / Noord-Holland?
