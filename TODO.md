# Dealbot — takenlijst

Bijgewerkt: 01-08-2026 22:05

## Fase 1 — de minimale basis (nu)

- [x] Database inrichten in Supabase (gebruikers, zoekvragen, aanbiedingen, logboek)
- [x] Inloggen met e-mailadres + pincode van 4 cijfers; mensen mogen zichzelf aanmelden
- [x] Ophaalscript Albert Heijn — 1024 weekaanbiedingen, 99% met kiloprijs
- [x] Ophaalscript Jumbo — 1242 aanbiedingen, 99,7% met kiloprijs
- [x] Derde keten: Dirk van den Broek — 417 aanbiedingen, 94% met kiloprijs.
      Vomar viel af: die publiceert zijn aanbiedingen alleen als digitale folder
- [x] Zoekvelden herindeeld: Merk, Productgroep (keuzelijst per winkel) en Vrije tekst
      zoeken elk in hun eigen deel van de aanbieding. Vrije tekst kijkt niet meer in de
      productgroep, waardoor "koffie" geen krat bier meer oplevert
- [x] Keuzelijst dekt het hele assortiment: per winkel wordt de volledige
      productgroep-indeling opgehaald, niet alleen wat er in de bonus lag.
      3962 groepen in plaats van 511; Jumbo deelt nu net zo fijn in als Albert Heijn
- [x] Meerpakken van Albert Heijn erbij: die staan niet in de bonusfolder maar wel
      in het assortiment. Een meerpak telt mee als het losse product zelf in de
      bonus is, en krijgt de kiloprijs van het losse pak maal het aantal
- [x] Zoeken op koffiebonen zonder merk: bij Albert Heijn zat het merk in de
      groepsnaam ("Lavazza koffiebonen", 1791 groepen). De groep is nu de lade uit
      de winkelindeling ("Koffiebonen", 313 laden); het merk heeft zijn eigen veld
- [ ] Uitzoeken of Nettorama betrouwbaar uit te lezen is (folder, geen prijzenlijst)
- [x] Automatisch elke ochtend laten draaien via GitHub — 07:00, duurt een halve minuut
- [x] Oude aanbiedingen pas opruimen nadat de nieuwe binnen zijn
- [x] Prijs per kilo/liter berekenen; lukt dat niet, dan onderaan met de melding "kiloprijs onbekend"
- [x] Startpagina: persoonlijke aanbiedingen, gegroepeerd per product, goedkoop naar duur
- [x] Profielpagina: zoekvragen bekijken, toevoegen en verwijderen
      (merk, productgroep, vrije tekst)
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
- [ ] Productgroepen van de verschillende ketens aan elkaar knopen. Voor Albert Heijn
      (313 laden) en Jumbo (2153) lost het zichzelf grotendeels op: de namen lijken
      sterk op elkaar en een zoekvraag bewaart alleen de naam, dus "Koffiebonen" pakt
      allebei. Wat overblijft zijn namen die net anders geschreven zijn, en vooral
      **Dirk met zijn 17 grove afdelingen** — daar is geen fijnere indeling te halen,
      dus die vraagt iets eigens (bijvoorbeeld op woorden in de productnaam).
      Eventueel met een achtergrondlijst van producten en EAN-codes
- [ ] De standaardprijzen-pagina bouwen
- [ ] Ook merk als keuzelijst in het profielscherm (de productgroep is er al één)
- [ ] Geschikt maken voor een mobiele app

## Als optie openhouden

- [ ] **Blijvende volumekortingen op meerpakken tóch aanbieden?** Albert Heijn
      geeft op veel meerpakken het hele jaar door 2 tot 10% korting ("10% volume
      voordeel"). Die weren we nu, want het zijn geen weekaanbiedingen: ze zouden
      elke week in de lijst staan en de echte koopjes verdringen. Bij Albert
      Heijn gaat het om ruim 2300 stuks. Denkbaar als aparte keuze in het
      profiel ("laat ook doorlopende meerpakkortingen zien"), of alleen tonen
      wanneer de kiloprijs onder de gewone bonusprijs duikt.

## Nog uit te zoeken

- [ ] Nettorama: alleen digitale folder beschikbaar? Zo ja, hoe betrouwbaar is dat uit te lezen?
      (Bij Vomar bleek zo'n folder níet betrouwbaar uit te lezen — dat is een voorproefje)
- [ ] Verschillen de aanbiedingen per filiaal in de regio Utrecht / Noord-Holland?
