# Dealbot — takenlijst

Bijgewerkt: 03-08-2026 11:00

## Fase 1 — de minimale basis (nu)

- [x] Database inrichten in Supabase (gebruikers, zoekvragen, aanbiedingen, logboek)
- [x] Inloggen met e-mailadres + pincode van 4 cijfers; mensen mogen zichzelf aanmelden
- [x] Ophaalscript Albert Heijn — 1024 weekaanbiedingen, 99% met kiloprijs
- [x] Ophaalscript Jumbo — 1242 aanbiedingen, 99,7% met kiloprijs
- [x] Derde keten: Dirk van den Broek — 417 aanbiedingen, 94% met kiloprijs
- [x] Vierde keten: Vomar — zijn aanbiedingen staan alleen in de digitale folder,
      en die wordt sinds 03-08-2026 door een AI voorgelezen. 219 aanbiedingen uit
      37 pagina's, 79% met kiloprijs. Wordt één keer per week gelezen: alleen als
      er een nieuwe uitgave hangt
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
- [x] Dirk fijner ingedeeld: 146 groepen ("Koffie & cacao") in plaats van 17 grove
      afdelingen. Fijner publiceert Dirk niet; voor "koffiebonen" is vrije tekst
      daar de route
- [ ] **De folder van vólgende week aanbieden.** Vomar heeft daar een eigen vaste
      ingang voor ("folder volgende week"), en de folderlezer kan hem al aan —
      alleen is er nog geen plek waar je hem ziet. Uit te zoeken: op zondag 2
      augustus stond die ingang leeg, dus we weten nog niet op welke dag Vomar de
      folder van de week erna klaarzet. Dat bepaalt of het een aparte pagina moet
      worden ("aanbiedingen volgende week") of een schakelaar op de startpagina
- [ ] Uitzoeken of Nettorama betrouwbaar uit te lezen is — nu wél kansrijk: een
      folder is geen belemmering meer, mits hij als PDF te downloaden is
- [x] Automatisch elke ochtend laten draaien via GitHub — 07:00, duurt een halve minuut
- [x] Oude aanbiedingen pas opruimen nadat de nieuwe binnen zijn
- [x] Prijs per kilo/liter berekenen; lukt dat niet, dan onderaan met de melding "kiloprijs onbekend"
- [x] Startpagina: persoonlijke aanbiedingen, gegroepeerd per product, goedkoop naar duur
- [x] Profielpagina: zoekvragen bekijken, toevoegen en verwijderen
      (merk, productgroep, vrije tekst)
- [x] Melding als er deze week geen aanbiedingen zijn, met link naar de standaardprijzen-pagina
- [ ] **De Gemini-sleutels op GitHub zetten**, anders wordt de folder alleen op de
      laptop gelezen en niet in de ochtendrun. Eén instelling volstaat:
      `GEMINI_API_KEYS` met alle sleutels achter elkaar, gescheiden door komma's
      (Settings → Secrets and variables → Actions). Let op: het zijn dezelfde tien
      sleutels als in project subs, en elke sleutel heeft ongeveer twintig vragen
      per dag. Eén folder kost er zo'n veertig, dus de folderlezer eet twee
      sleutels op van wat subs die dag nog kan vertalen
- [ ] Testknop op de site om het ophalen handmatig te starten (via Supabase, zodat er geen sleutel op de openbare pagina staat) — gaat er na de testfase weer uit

## Fase 2 — later

- [ ] **E-mailbericht sturen zodra er een aanbieding is die bij iemands profiel past.** Let op: hiervoor is een extra gratis maildienst nodig, Supabase mag zelf alleen inlog-mails versturen
- [ ] Bevestigingsmail bij het aanmelden van een nieuw account
- [ ] In het profiel kunnen aanvinken bij welke winkels je daadwerkelijk komt, zodat je geen
      aanbiedingen ziet van een winkel dertig kilometer verderop
- [ ] **Vijfde keten: Lidl.** Uitgezocht op 03-08-2026 en kansrijk: één verzoek naar
      `www.lidl.nl/c/aanbiedingen/a10008785` levert 108 aanbiedingen met prijs,
      van-prijs, productgroep en looptijd. Let op: maar ongeveer de helft noemt de
      inhoud, dus de rest krijgt "kiloprijs onbekend". Een merkveld is er niet
- [ ] Meer winkels: DekaMarkt (werkt precies als Dirk, dus weinig werk), Bol, Amazon,
      Picnic. Plus, Coop en Hoogvliet blokkeren automatisch ophalen
- [x] Vomar gebruiken voor de standaardprijzen-pagina: hun productlijst geeft het hele
      assortiment met normale prijs, merk, inhoud én streepjescode (EAN). Gedaan op
      02-08-2026: 6174 producten, allemaal met kiloprijs en EAN, in twee verzoeken.
      Vomar levert sinds 03-08-2026 allebei: schapprijzen uit de webshop-ingang én
      aanbiedingen uit de voorgelezen folder
- [ ] Productgroepen van de verschillende ketens aan elkaar knopen. Voor Albert Heijn
      (313 laden) en Jumbo (2153) lost het zichzelf grotendeels op: de namen lijken
      sterk op elkaar en een zoekvraag bewaart alleen de naam, dus "Koffiebonen" pakt
      allebei. Wat overblijft zijn namen die net anders geschreven zijn, en
      **Dirk met zijn 146 groepen** — die zijn een slag grover ("Koffie & cacao"),
      dus daar blijft vrije tekst op de productnaam de route.
      De achtergrondlijst met EAN-codes is er inmiddels: 6174 Vomar-producten,
      allemaal mét streepjescode, in de tabel `standaardprijzen`
- [ ] **Voorvoegsel "lokaal" bij Jumbo-groepen opschonen.** Een deel van Jumbo's
      groepsnamen begint met "lokaal" ("lokaal Koffiebonen"), waardoor dezelfde
      groep twee keer in de keuzelijst staat en niet meer op één naam matcht met
      Albert Heijn. Uitzoeken of het voorvoegsel altijd weg mag, of dat het iets
      betekent (streekproducten) dat we willen bewaren
- [x] De standaardprijzen-pagina bouwen — gedaan op 02-08-2026, gevuld met Vomar.
      Zoeken op merk of productnaam, of een productgroep kiezen; resultaten van
      goedkoop naar duur per kilo
- [ ] **Dirk (en Lidl) erbij als tweede winkel op de standaardprijzen-pagina, zodat
      er echt te vergelijken valt.** Met één winkel erin staat er alleen een prijs;
      pas met een tweede wordt de pagina nuttig.
      - **Dirk** is de makkelijke: het hele assortiment is op te halen met
        `listWebGroupProducts(webGroupId)` per groep, gevolgd door
        `products(productIds, storeId)` in blokken. Let op: van de 1123 artikelen
        in "Koffie & cacao" levert maar een zesde een prijs in winkel 66.
      - **Lidl valt hier af, maar is wél bruikbaar voor aanbiedingen.** Uitgezocht
        op 03-08-2026: Lidl blokkeert niet — zijn aanbiedingenpagina bevat de
        prijzen gewoon zelf, 108 stuks in één verzoek. Maar schapprijzen bestaan
        bij Lidl niet online: alleen wat in de bonus ligt heeft een bedrag.
        Voor deze pagina is Dirk dus de tweede winkel.
      - Koppelen tussen winkels gaat het beste op streepjescode. Vomar levert die
        bij 100% van zijn producten; van Dirk is dat nog onbekend, Lidl geeft er
        geen (alleen eigen artikelnummers, dus koppelen op naam)
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
