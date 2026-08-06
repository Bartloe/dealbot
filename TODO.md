# Dealbot — takenlijst

Bijgewerkt: 06-08-2026 15:16

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
- [x] Automatisch elke ochtend laten draaien via GitHub — 07:00, duurt tien minuten
      sinds Picnic meedoet
- [x] **De ochtendronde deelt zelf in** (06-08-2026): het indelen hangt achter het
      ophalen aan, zonder ooit een AI-vraag te stellen — alleen het bestaande
      vertaalboekje wordt toegepast. Vertalen blijft handwerk, want één nieuwe keten
      zou de ronde tientallen vragen laten doen en die heeft de folderlezer nodig.
      Onbekende groepsnamen worden geteld en staan per winkel op de beheerpagina;
      dát is het sein om `python scripts/indeel.py` te draaien
      - **Nog te doen:** `database/19_ochtendronde_indelen.sql` in Supabase draaien
        voor die kolom. Tot dan blijft de kolom weg van de beheerpagina
- [x] Oude aanbiedingen pas opruimen nadat de nieuwe binnen zijn
- [x] Prijs per kilo/liter berekenen; lukt dat niet, dan onderaan met de melding "kiloprijs onbekend"
- [x] Startpagina: persoonlijke aanbiedingen, gegroepeerd per product, goedkoop naar duur
- [x] Winkelpagina: alle aanbiedingen van één winkel in de lopende week, per productgroep.
      Winkel kiezen op logo; gedaan op 03-08-2026
- [ ] **De folderlezer ook een productgroep laten meegeven.** Voor het profielscherm
      is dit opgelost door onze eigen indeling: Vomar komt zonder winkelgroep binnen,
      maar 124 van zijn 169 aanbiedingen krijgen alsnog een plek via de productnaam.
      De overige 45 (27%) blijven in de restbak, en op de winkelpagina staat álles
      van Vomar nog onder één kopje "Overig" — die pagina bundelt namelijk op de
      groepsnaam van de winkel zelf, en die is er bij een folder niet
- [x] Profielpagina: zoekvragen bekijken, toevoegen en verwijderen
      (afdeling/groep uit onze eigen indeling, merk, vrije tekst)
- [x] Melding als er deze week geen aanbiedingen zijn, met link naar de standaardprijzen-pagina
- [x] **De Gemini-sleutels op GitHub gezet** — nagelopen op 06-08-2026: de ronde van
      07:36 las zelf de folder van 3 t/m 9 augustus (122 aanbiedingen). De folder
      wordt dus niet meer alleen op de laptop gelezen. Let op: elke sleutel heeft
      ongeveer twintig vragen per dag en één folder kost er zo'n veertig, dus de
      folderlezer eet twee sleutels op van wat project subs die dag nog kan vertalen
- [x] **Testknop op de site om het ophalen handmatig te starten** (05-08-2026): twee
      knoppen op de beheerpagina — *Nu ophalen* en *Folder opnieuw lezen*. De database
      geeft het startsein door aan GitHub met een sleutel uit zijn eigen kluis, dus er
      staat geen sleutel op de openbare pagina. Hooguit eens per vijf minuten, en de
      pagina laat zien of het sein is aangenomen. Gaat er na de testfase weer uit

## Beheerpagina

- [x] **Beheerpagina, alleen voor het beheerdersaccount** (04-08-2026): hoe de laatste
      ronde per winkel is gegaan (met storingsmelding) en hoe compleet de oogst is —
      aantallen zonder kiloprijs en zonder plek in onze eigen indeling
- [x] **Gebruikersoverzicht** (05-08-2026): naam, e-mail, aangemaakt op, laatst ingelogd,
      aantal zoekvragen. Per gebruiker: op slot zetten, weer openen en verwijderen. Plus
      de lijst geweerde e-mailadressen, zodat opnieuw aanmelden met hetzelfde adres niet
      lukt. Aanmelden blijft verder vrij. De knop "herstelmail sturen" hoort bij de klus
      hieronder — zonder pagina om een nieuwe pincode te kiezen leidt die mail nergens heen
- [x] **Automatisch uitloggen na 8 uur zonder activiteit** (05-08-2026): de klok loopt in
      de browser en wordt door elke klik of toetsaanslag teruggezet
- [x] **Pincode vergeten** (05-08-2026): de gebruiker vraagt zelf een herstelmail aan en
      stelt via de link een nieuwe pincode in. Twee kanttekeningen: de nieuwe pincode moet
      verschillen van de huidige (Supabase weigert dezelfde), en de ingebouwde mailer
      stuurt maar een handvol berichten per uur — voor 25 gebruikers genoeg, maar niet om
      mee te testen
- [x] **In Supabase de Site URL goedgezet** (05-08-2026): `https://bartloe.github.io/dealbot/`
      als Site URL, met `https://bartloe.github.io/dealbot/**` bij Redirect URLs. De hele
      weg van vergeten pincode naar nieuwe pincode is daarna van begin tot eind nagelopen
      met `python scripts/tests/test_pincode.py` — 13 controles, allemaal goed: de link
      komt op onze eigen pagina uit, geeft tijdelijke toegang, de nieuwe pincode werkt en
      de oude niet meer, en een kapotte link geeft een nette melding

## Fase 2 — later

- [ ] **E-mailbericht sturen zodra er een aanbieding is die bij iemands profiel past.** Let op: hiervoor is een extra gratis maildienst nodig, Supabase mag zelf alleen inlog-mails versturen
- [ ] Bevestigingsmail bij het aanmelden van een nieuw account
- [ ] In het profiel kunnen aanvinken bij welke winkels je daadwerkelijk komt, zodat je geen
      aanbiedingen ziet van een winkel dertig kilometer verderop
- [x] **Vijfde keten: Lidl.** Gedaan op 03-08-2026: één verzoek naar
      `www.lidl.nl/aanbiedingen` levert 108 aanbiedingen met prijs, van-prijs,
      productgroep en looptijd; 89 daarvan met kiloprijs. Veertig aanbiedingen
      zijn Lidl Plus-kaartprijzen en staan in een eigen veld — die tellen mee,
      met "met Lidl Plus" in de actietekst. Een merkveld is er niet
- [x] **Zesde keten: Picnic.** Gedaan op 05-08-2026: 1836 aanbiedingen (91% met
      kiloprijs) en 12.754 schapprijzen uit één rondgang door 265 laden, in vijf
      minuten. Picnic heeft geen webwinkel en geen folder — alles zit in zijn app —
      dus Dealbot logt in met een eigen Picnic-account. Elke verse inlog vraagt om
      een code per sms of e-mail, dus er is één keer met de hand ingelogd; die
      sleutel geldt tot 01-02-2027. Een aanbieding is te herkennen aan het gele
      vlaggetje op de producttegel, níet aan de rode prijs — dat label
      ("Prijskampioen") is een blijvend lage prijs
- [x] **De sleutel van Picnic als instelling op GitHub gezet** — nagelopen op
      06-08-2026: de ronde van 07:36 liep zelf langs 284 laden van Picnic en zette
      1818 aanbiedingen en 12.781 schapprijzen klaar
- [ ] **Op tijd waarschuwen dat de Picnic-sleutel verloopt** (01-02-2027). Nu merk
      je het pas als de ronde stukloopt; de beheerpagina zou het van tevoren
      kunnen melden
- [ ] Meer winkels: DekaMarkt (werkt precies als Dirk, dus weinig werk), Bol, Amazon.
      Plus, Coop en Hoogvliet blokkeren automatisch ophalen
- [x] Vomar gebruiken voor de standaardprijzen-pagina: hun productlijst geeft het hele
      assortiment met normale prijs, merk, inhoud én streepjescode (EAN). Gedaan op
      02-08-2026: 6174 producten, allemaal met kiloprijs en EAN, in twee verzoeken.
      Vomar levert sinds 03-08-2026 allebei: schapprijzen uit de webshop-ingang én
      aanbiedingen uit de voorgelezen folder
- [x] **Eigen productindeling van twee lagen, los van de winkels.** In plaats van de
      indelingen van vijf ketens aan elkaar te lijmen staat er nu één eigen indeling
      boven, en hangt elk product daaronder. Proefstuk Koffie & thee gedaan op
      03-08-2026: 340 aanbiedingen over alle vijf de winkels, steekproef van vijftig
      vijftig keer goed, 2% viel buiten de indeling. Zie CHANGELOG voor hoe het werkt
- [x] **De overige 28 takken van de indeling erbij** — klaar op 06-08-2026. Onze
      indeling telt 28 afdelingen met 252 laden, en het vertaalboekje is compleet:
      alle 3183 winkelgroepen staan erin (3076 onder onze indeling, 62
      eigenschapgroepen, 45 bewust afgevallen)
- [x] **Het profielscherm op de eigen indeling gezet** (04-08-2026): 28 afdelingen om
      open te klappen met hun groepen, in plaats van 3962 groepsnamen per winkel. Eén
      keer "Koffiebonen" aanvinken dekt alle winkels. De winkelpagina houdt de indeling
      van de winkel zelf — daar blader je door één folder
- [x] **Kenmerken: de derde laag onder de lade** (05-08-2026). Onze lade
      Toiletpapier bevat het droge en het vochtige door elkaar; het kenmerk
      "vochtig" maakt dat onderscheid alsnog, in onze eigen woorden en bij alle
      winkels tegelijk. Afgeleid uit de groepsnamen van de winkels zelf, dus er
      wordt nergens een lijstje met de hand bijgehouden
- [x] **De kenmerken opgehaald bij de winkelgroepen die er al stonden** — klaar op
      06-08-2026: 283 kenmerken verdeeld over 121 laden. Ze staan als knopjes onder
      de lade op het profielscherm en als verfijning op de standaardprijzen-pagina
- [x] **De startpagina de eigen indeling laten gebruiken** — gedaan op 04-08-2026:
      de gevonden aanbiedingen staan gebundeld onder hun afdeling en lade. Tot en met
      zes afdelingen staat alles meteen open; daarboven zijn de blokken dicht
- [x] **De eigen indeling is op de hele website de zoekingang** — nagelopen op
      06-08-2026, nu het vertaalboekje compleet is. Alle 28 afdelingen hebben inhoud
      en 196 van de 252 laden liggen deze week ook echt in de bonus. Van de 8479
      aanbiedingen valt 1,7% in de restbak en staat 13,5% alleen op zijn afdeling —
      daarom staat "Alles uit …" bovenaan elke afdeling: wie alleen laden aanvinkt,
      mist die. De restbak is wél te kiezen op de standaardprijzen-pagina en
      bewust niet op het profielscherm: een zoekvraag op "nog niet ingedeeld" zou
      elke week iets anders opleveren
- [ ] **Voorvoegsel "lokaal" bij Jumbo-groepen opschonen.** Minder dringend dan het
      was: sinds onze eigen indeling de zoekingang is, komen "Koffiebonen" en
      "lokaal Koffiebonen" allebei onder dezelfde lade uit. Wat overblijft is dat
      het twee regels in het vertaalboekje kost in plaats van één, en dat de
      winkelpagina ze als twee kopjes naast elkaar toont. Uitzoeken of het
      voorvoegsel altijd weg mag, of dat het iets betekent (streekproducten)
- [x] De standaardprijzen-pagina bouwen — gedaan op 02-08-2026, gevuld met Vomar.
      Zoeken op merk of productnaam, of een productgroep kiezen; resultaten van
      goedkoop naar duur per kilo
- [x] **Een tweede winkel op de standaardprijzen-pagina** — opgelost op 05-08-2026
      door Picnic, die 12.754 schapprijzen meelevert uit dezelfde rondgang als zijn
      aanbiedingen. Naast Vomar staat er nu dus echt iets te vergelijken. Let op:
      Picnic geeft geen streepjescode, dus koppelen aan Vomar kan alleen op naam
- [ ] **Albert Heijn erbij op de standaardprijzen-pagina — de prijzen komen al
      binnen.** Gemeten op 06-08-2026. De ochtendronde loopt bij Albert Heijn al
      de hele winkelindeling af (29 afdelingen met hun laden), om te weten in
      welke lade een product ligt en om meerpakken te vinden. Elk product dat
      daarbij binnenkomt draagt zijn gewone winkelprijs mee; alles wat niet in de
      bonus is wordt nu weggegooid. Er is dus geen enkel extra verzoek nodig —
      alleen wegschrijven.
      - **Omvang: 43.178 producten.** Meer dan het dubbele van Vomar (6174) en
        Picnic (12.754) samen. Dat is 216 schrijfblokken tegen 64 voor Picnic, dus
        de ochtendronde wordt langer aan de databasekant. Eerst meten hoeveel.
      - De gewone prijs staat er óók bij als een product deze week in de bonus
        ligt. Precies wat nodig is om te zien of een aanbieding echt korting is.
      - De grens van 3000 per tak speelt geen rol: maar drie afdelingen zitten
        erboven (Drogisterij 3641, Soepen en sauzen 3436, Bier en wijn 3163) en de
        bron zakt daar al automatisch af naar de laden eronder.
      - Geen streepjescode, dus koppelen aan Vomar kan alleen op naam — net als
        bij Picnic.
      - **Actueel houden kost niets:** meeliften met de ochtendronde. Het
        wegschrijven zelf is al gebouwd (bijwerken per 200, daarna opruimen wat
        niet terugkwam), dus dagelijks verversen is eenvoudiger dan een eigen
        schema verzinnen.
- [ ] **Jumbo erbij op de standaardprijzen-pagina — eerst uitzoeken.** Jumbo geeft
      de gewone prijs gewoon prijs, met inhoud en indeling erbij; dat is op
      06-08-2026 nagegaan. Maar anders dan bij Albert Heijn halen we zijn
      assortiment nu niet op, en zijn zoekingang wil een zoekterm in plaats van een
      productgroep — per afdeling aflopen lukte niet.
      - Uit te zoeken: is er een ingang per productgroep? Zo niet, dan is de omweg
        om de 2480 groepsnamen die we al van Jumbo hebben als zoekterm te
        gebruiken. Dat levert overlap en gaten op, en het zijn 2480 verzoeken.
      - Een dieptegrens is er niet: een resultatenlijst is tot de laatste door te
        bladeren.
      - **Actueel houden kost hier wél verzoeken.** Schapprijzen veranderen zelden,
        dus één keer per week is genoeg — als aparte ronde, niet aangehangen aan
        het dagelijkse ophalen.
- [ ] **Dirk erbij op de standaardprijzen-pagina.** Nu minder
      dringend dan het was, maar hoe meer winkels hoe beter te vergelijken.
      - **Dirk** is de makkelijke: het hele assortiment is op te halen met
        `listWebGroupProducts(webGroupId)` per groep, gevolgd door
        `products(productIds, storeId)` in blokken. Let op: van de 1123 artikelen
        in "Koffie & cacao" levert maar een zesde een prijs in winkel 66.
      - **Lidl valt hier af, maar is wél bruikbaar voor aanbiedingen.** Uitgezocht
        op 03-08-2026: Lidl blokkeert niet — zijn aanbiedingenpagina bevat de
        prijzen gewoon zelf, 108 stuks in één verzoek. Maar schapprijzen bestaan
        bij Lidl niet online: alleen wat in de bonus ligt heeft een bedrag.
      - Koppelen tussen winkels gaat het beste op streepjescode. Vomar levert die
        bij 100% van zijn producten; van Dirk is dat nog onbekend, Lidl en Picnic
        geven er geen (alleen eigen artikelnummers, dus koppelen op naam)
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
