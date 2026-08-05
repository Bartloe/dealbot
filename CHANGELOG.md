# Wijzigingen — Dealbot

## 06-08-2026 — Een afgebroken vertaalronde hervatten

De ronde die alle 2606 winkelgroepen langs de AI stuurt om er de kenmerken uit
te halen, kost ongeveer 45 vragen. Loopt de dagvoorraad leeg, dan valt hij stil —
en dan was er geen goede manier om de volgende ochtend verder te gaan:

- **opnieuw beginnen** met `--opnieuw` stelde alle vragen van gisteravond nog
  eens, en juist die vragen zijn schaars: ze komen uit dezelfde voorraad als het
  voorlezen van de Vomar-folder;
- **gewoon doorstarten** zonder die instelling deed helemaal niets, want élke
  groep staat al in het vertaalboekje. Hij zag dus alles als "al gedaan".

Wat al vertaald was ging overigens nooit verloren: elk blok van zestig
groepsnamen gaat meteen naar de database zodra het antwoord binnen is.

Vanaf nu is er `python scripts/indeel.py --verder`. Die slaat over wat er in deze
ronde al is bijgewerkt en vraagt de rest. Vóór er ook maar één AI-vraag uitgaat,
meldt hij hoeveel groepen hij overslaat en hoeveel er nog aan de beurt komen —
klopt dat niet met wat je verwacht, dan kun je hem stoppen.

Waar de ronde begon wordt afgeleid uit het moment waarop de regels in het boekje
zijn bijgewerkt: een etmaal terug vanaf de laatste. Dat is bewust géén kalenderdag.
Een ronde die om kwart voor twaalf 's avonds begint en na middernacht doorloopt,
is één ronde en geen twee — op een kalenderdag afgaan zou het werk van vóór
twaalven alsnog overdoen. Duurde het langer dan een etmaal, dan geef je de
begindatum zelf mee: `--verder 05-08-2026`.

`scripts/tests/test_hervatten.py` legt dat vast, met de randen: het geval rond
middernacht, een regel uit een oudere ronde die wél opnieuw moet, een tijdstip
zonder tijdzone (dat is altijd UTC — anders schuift alles twee uur op en valt de
grens midden in de ronde) en een datum die niet te lezen is.

## 05-08-2026 — Kenmerken: alleen het vochtige toiletpapier volgen

Onze indeling heeft één lade *Huishouden › Toiletpapier*, met het droge en het
vochtige door elkaar. Wie alleen het vochtige wilde volgen, kon dat nergens
kiezen. Datzelfde speelt bij koffie (bonen, pads, capsules), bij melk (vol,
halfvol, lactosevrij) en bij tientallen andere laden.

De laden fijner maken lost dat niet op: dan groeit de indeling eindeloos en moet
iemand hem met de hand blijven bijhouden. **Maar de winkels hebben die fijne
indeling allang gemaakt.** Vomar zegt "Toiletpapier Vochtig", Albert Heijn
"Toiletpapier - vochtig". Wij gooiden dat detail weg zodra de winkelgroep onder
onze lade werd gehangen.

Vanaf nu wordt het bewaard als **kenmerk**: één woord in onze eigen taal, dat bij
elke winkel hetzelfde is. Een derde, optionele laag dus — afdeling › lade ›
kenmerk.

### Wat je ervan merkt

- **In je profiel** staan onder een lade knopjes met de kenmerken die erin
  voorkomen: *vochtig* onder Toiletpapier, *pads* en *capsules* onder de koffie.
  Klik je er een aan, dan volg je alleen dat — bij alle winkels tegelijk. Vink je
  de lade zelf aan, dan krijg je gewoon alles wat erin ligt, precies zoals
  voorheen. Bestaande zoekvragen veranderen dus niet.
- **Zoeken op "vochtig"** in het profielscherm vindt nu de lade Toiletpapier, met
  het knopje er al onder. Je hoeft dus niet te weten in welke lade iets ligt.
- **Op de standaardprijzen-pagina** staan de verfijningsknopjes voortaan op het
  kenmerk in plaats van op de groepsnaam van de winkel. Waar eerst drie knopjes
  stonden voor hetzelfde vochtige toiletpapier — elk met alleen de producten van
  één keten — staat er nu één. Wat geen kenmerk heeft, komt onder *overig* te
  staan en verdwijnt dus niet.
- **De knopjes op beide pagina's zijn dezelfde.** Wat je bij het vergelijken van
  prijzen ziet, kun je in je profiel gaan volgen.

### Waarom dit zichzelf onderhoudt

Er staat nergens een lijstje met kenmerken dat iemand moet bijhouden. Het rolt
uit het vertaalwerk dat we voor alle 2606 winkelgroepen toch al doen: de AI die
"Toiletpapier Vochtig" onder onze lade hangt, houdt daarbij het woord *vochtig*
over. Komt er een winkel of een productsoort bij, dan groeien de kenmerken
vanzelf mee.

Twee dingen houden dat bij elkaar:

- **Eén woord per ding.** De vertaler krijgt de kenmerken die de lade al kent mee
  in zijn opdracht, met de instructie er één te hergebruiken als het over
  hetzelfde gaat. Vragen is geen garantie, dus daarna wordt het nog afgedwongen:
  "vochtige" valt terug op "vochtig" en "halfvolle" op "halfvol". Een ladenaam
  die per ongeluk in het kenmerk terechtkomt gaat eraf — bij "Toiletpapier
  Vochtig" blijft alleen "vochtig" over.
- **Alleen kenmerken die iets splitsen.** Een kenmerk dat maar bij één product
  voorkomt is ruis en blijft van het scherm weg.

Voor winkels die het onderscheid niet in hun groepsnaam maken — bij Dirk heet
alles gewoon "Toiletpapier" — wordt het kenmerk uit de productnaam gevist, met
de woorden die de lade van de ándere winkels heeft geleerd. Dat gebeurt op hele
woorden: "vol" slaat niet aan op "volkoren", en "halfvolle melk" landt bij
*halfvol* en niet bij *vol*.

Eerlijk over de zwakke plek: benoemt een winkel het vochtige nergens — niet in de
groep, niet op het pak — dan blijft het daar onvindbaar. Dat is geen fout maar
het eerlijke antwoord; die informatie bestaat daar simpelweg niet.

### Onder de motorkap

- `database/16_kenmerken.sql` — kenmerk erbij op het vertaalboekje, op de
  aanbiedingen, op de standaardprijzen en op de zoekvragen. Plus de functie
  `kenmerken()`, die per lade teruggeeft wat erin zit. Een kenmerk zonder lade
  kan niet: "vochtig" bestaat bij het toiletpapier én bij de doekjes.
- `scripts/dealbot/kenmerken.py` — nieuw. Het opschonen, het samenvallen van
  schrijfwijzen en het vissen uit de productnaam.
- `scripts/tests/test_kenmerken.py` — nieuw, 48 controles en allemaal goed. Met
  nadruk op de randen: leeg antwoord, ladenaam herhaald, woord middenin een
  ander woord, twee schrijfwijzen van hetzelfde.

## 05-08-2026 — Verwijderen en weren in één handeling

Een account verwijderen en het e-mailadres weren zijn twee dingen die je bijna
altijd achter elkaar doet — en juist die volgorde werkte ongelukkig: zodra het
account weg was, stond het adres nergens meer op het scherm en moest je het uit
je hoofd overtikken in het blok eronder.

- **Bij het verwijderen staat nu een vinkje**: "dit e-mailadres ook weren, zodat
  er geen nieuw account mee aangemaakt kan worden". Eén handeling dus.
- **Het adres gaat eerst op de lijst, het account pas daarna weg.** Gaat er bij
  het weren iets mis, dan staat het account er nog gewoon en kun je het opnieuw
  proberen. Andersom zou het adres onvindbaar zijn geworden.
- **Annuleren is de standaardkeuze.** Wie het venster wegklikt of op Enter drukt,
  verwijdert niets.

Twee kleinigheden meegenomen in hetzelfde overzicht:

- **Knoppen blijven niet meer grijs.** Wie het verwijderen afbrak, keek daarna
  tegen een knop aan die niets meer deed. De knop *Herstelmail* meldt nu kort
  "Verstuurd" en is na een halve minuut weer te gebruiken — lang genoeg om een
  tweede mail door dubbelklikken te voorkomen, kort genoeg om het opnieuw te
  kunnen proberen als de eerste niet aankwam.
- **Te zien welk account de beheerder is.** Dat vlaggetje is alleen in de
  database te zetten, maar het hoort wel zichtbaar te zijn: anders is aan niets
  af te lezen welk account overal bij kan.

De proef op het gebruikersbeheer (`scripts/tests/test_beheer.py`) is uitgebreid
met deze handeling: 28 controles, allemaal goed. Het adres blijft daarna ook
echt dicht — aanmelden met datzelfde adres lukt niet meer.

## 05-08-2026 — Picnic erbij als zesde winkel

Picnic doet mee, en hij is meteen de op één na grootste bron: **1836
aanbiedingen en 12.754 schapprijzen**, verdeeld over 265 productgroepen. Van die
aanbiedingen heeft 91% een kiloprijs.

### Waarom dit anders ging dan bij de andere ketens

Picnic heeft geen winkel om binnen te lopen en geen folder om te lezen. Hij
heeft ook geen webwinkel: zijn hele assortiment zit uitsluitend in zijn app.
Hun eigen site zegt het zo — *"Nee, een papieren folder hebben we niet. Maar
eigenlijk kun je onze app zien als een folder."* Die app-ingang laat alleen
ingelogde klanten toe, en een omweg via een vergelijkingssite bestaat niet:
supermarktscanner.nl heeft Picnic helemaal niet in huis.

Dealbot logt daarom in met een eigen Picnic-account. Dat kan niet elke ochtend
opnieuw: **Picnic vraagt bij elke verse inlog om een code per sms of e-mail**, en
die kan een ochtendronde niet beantwoorden. Er is dus één keer met de hand
ingelogd; de sleutel die daaruit komt is bewaard en geldt **tot 1 februari
2027**. Loopt hij af, dan meldt de beheerpagina dat met zoveel woorden — en dan
is er opnieuw één code nodig.

### Wat er binnenkomt

- **De hele winkel wordt afgelopen**, net als bij Albert Heijn: 26 afdelingen met
  daaronder 265 laden als *Koffiebonen*, *Yoghurt & skyr* en *Verse vis*. Dat is
  dezelfde fijne indeling waar Albert Heijn zijn laden voor heeft, en dus veel
  bruikbaarder dan de grove afdelingen van Dirk.
- **Eén rondgang levert allebei**: de aanbiedingen én de gewone schapprijzen. Bij
  Picnic zit dat op dezelfde producttegel, dus de winkel wordt maar één keer
  afgelopen. Het kost ongeveer vijf minuten.
- **Picnic is daarmee de tweede winkel op de standaardprijzen-pagina.** Tot nu
  toe stond daar alleen Vomar, en met één winkel valt er niets te vergelijken.
- **Ligt een product deze week in de actie, dan staat op de
  standaardprijzen-pagina zijn gewóne prijs** — daar hoort te staan wat iets
  kost als er even geen aanbieding is.

### Twee valkuilen die we eruit hebben gehaald

- **Een rode prijs betekent niet "aanbieding".** Picnic zet het label
  *Prijskampioen* — een blijvend lage prijs — in exact dezelfde rode kleur als
  een actieprijs. Alleen het gele vlaggetje op de tegel telt; daar staat de
  actietekst ook in.
- **"1+1 gratis" en "2e = 40% korting" staan bij Picnic naast de gewóne prijs.**
  Wie die klakkeloos overneemt, zet zo'n aanbieding twee keer zo duur in de lijst
  als hij is. Dealbot rekent nu zelf uit wat je per stuk betaalt. De vorm
  "2e = 40% korting" was nieuw en werd eerst gelezen als korting op élk
  exemplaar — dat scheelde een kwart in de prijs.

### Onderweg verbeterd voor álle winkels

- **Koffie en thee krijgen eindelijk een prijs per kopje.** Dealbot rekende in
  grammen en liters en kende "36 pads", "20 koppen" of "10 cups" niet, waardoor
  die producten zonder kiloprijs onderaan bleven hangen. Nu tellen ze mee.
  Bewust níet meegeteld: "3-4 porties" en "6-8 punten" — dat zegt iets over
  hoeveel mensen ervan eten, niet over wat er in de verpakking zit. Een
  bereidingstijd ("30 min") wordt ook niet voor inhoud aangezien.
- **Herkomst is geen merk.** Bij onverpakte groente en fruit zet Picnic "Uit
  Nederland" in het merkveld. Dat blijft er nu uit: anders vindt dezelfde aardbei
  bij Albert Heijn zijn tegenhanger niet meer, want winkels worden op merk plus
  productnaam aan elkaar geknoopt.

### Onder onze eigen indeling

**257 van de 258 Picnic-groepen** hebben een plek gekregen in onze eigen
indeling, en daarmee hangt **91% van zijn aanbiedingen** eronder. Eén keer
*Koffiebonen* aanvinken geeft nu 40 aanbiedingen bij zes winkels; *Yoghurt &
skyr* er 39, waarvan 23 van Picnic.

### Wat er nog moet gebeuren

- **De sleutel als instelling op GitHub zetten**: `PICNIC_TOKEN` onder Settings →
  Secrets and variables → Actions. Zonder die instelling draait de ochtendronde
  gewoon door, maar blijft Picnic buiten de lijst.
- `database/13_picnic.sql` staat klaar. De winkel is al aangemaakt, dus dit
  script uitvoeren verandert niets meer — het is de vastlegging.

## 05-08-2026 — Eén hapering gooide een hele winkel om

Vanochtend om 07:35 viel Albert Heijn uit de ronde met de melding "wegschrijven
mislukt". De vier andere winkels liepen op datzelfde moment gewoon door, dus de
database was niet plat: de verbinding haperde een paar tellen, precies toen het
eerste pakketje aanbiedingen de deur uit ging. Daar was geen weg omheen — lukte
het versturen niet in één keer, dan stopte het daar. Bij bijna vijfduizend
aanbiedingen in vierentwintig pakketjes is dat vragen om ongelukken, en het is
geen toeval dat het juist de grootste winkel trof.

- **Elke vraag aan de database krijgt nu drie herkansingen**, met een oplopende
  pauze ertussen: een halve seconde, twee, en vijf. Een hapering duurt zelden
  langer, en langer wachten houdt de ochtendronde onnodig op.
- **Alleen bij een hapering of een tijdelijke storing.** Is het een echte fout in
  wat wij versturen, dan stopt het meteen — zo'n fout hoort zichtbaar te worden
  en niet vier keer zinloos herhaald.
- **Opnieuw sturen kan geen kwaad**: wegschrijven gebeurt als "bijwerken op
  sleutel", dus hetzelfde pakketje twee keer versturen levert exact hetzelfde
  resultaat en geen dubbele regels.
- **Blijft het stuk, dan zegt de melding dat ook** ("ook na 4 pogingen"), zodat
  op de beheerpagina te zien is dat het niet aan één toevallige tel lag.

Er is niets verloren gegaan. Omdat het wegschrijven mislukte, is het opruimen
overgeslagen en bleef de lijst van gisteren staan — die aanbiedingen liepen nog
tot en met 9 augustus, dus de site heeft de hele ochtend kloppende prijzen laten
zien. De ronde is intussen opnieuw gedraaid: Albert Heijn staat weer op 4787
aanbiedingen.

Een nieuw proefstuk (`scripts/tests/test_herkansing.py`) bewijst het gedrag met
een nagebootste database, want dit is bij uitstek iets wat je pas mist op de
zeldzame ochtend dat het misgaat.

## 05-08-2026 — Vochtig toiletpapier ligt nu gewoon bij het toiletpapier

Op de standaardprijzen-pagina stond "Toiletpapier Vochtig" als losse groep náást
"Toiletpapier". Wie op toiletpapier zocht, kreeg dus niet alles te zien wat er in
dat schap ligt. Daar zat een groter gat achter.

- **Vomar hing helemaal buiten onze indeling.** Alle andere winkels waren vertaald
  naar onze eigen afdelingen en laden, Vomar als enige niet: zijn ruim zesduizend
  producten hadden geen afdeling en geen lade. De oorzaak was een afspraak die
  ooit klopte — de indeling van een winkel die alleen zijn schap publiceert ging
  expres niet naar de groepenlijst, want een zoekvraag daarop zou nooit een
  aanbieding opleveren. Sinds diezelfde lijst het vertaalboekje voedt, betekende
  die afspraak dat Vomar nooit vertaald werd. Dat is rechtgezet; zijn 320
  groepsnamen zijn nu vertaald.
- **De standaardprijzen worden voortaan ook ingedeeld**, niet alleen de
  aanbiedingen. Dat gebeurt in dezelfde ronde en met hetzelfde vertaalboekje.
- **De keuzelijst op de standaardprijzen-pagina toont onze eigen indeling**:
  dezelfde afdelingen en laden als op de rest van de site, met per lade het aantal
  producten erin. Lege laden blijven weg — op deze pagina valt niets te wachten op
  een aanbieding. Onderaan staat "Nog niet ingedeeld" voor wat nergens onder valt,
  zodat er niets stilletjes uit beeld verdwijnt.
- **Knopjes om binnen een lade te verfijnen.** In de lade Toiletpapier staat nu
  `alles`, `Toiletpapier` en `Toiletpapier Vochtig`; klikken filtert de lijst.
  Die knopjes zijn de groepsnamen van de winkel zelf, dus ze lezen zoals de winkel
  het opschrijft. Filteren gebeurt in het scherm, zonder nieuwe vraag aan de
  database.

Bewuste keuze: de indeling krijgt **geen derde laag**. Elke keten noemt hetzelfde
anders — "Toiletpapier - vochtig", "Vochtig toiletpapier", "Toiletpapier Vochtig"
— dus zo'n laag zou opnieuw vertaald moeten worden, met duizenden namen in plaats
van 28 afdelingen. "Vochtig" is een eigenschap van toiletpapier, geen eigen plek
in de winkel; net zoals glutenvrij brood gewoon brood is.

Uit te voeren in Supabase: `database/15_standaardprijzen_indeling.sql`.

## 05-08-2026 — De groepenlijst in het profiel doet het weer

Wie in zijn profiel een zoekvraag wilde toevoegen, kreeg bij het eerste zoekveld
"De productgroepen konden niet worden opgehaald" en zag geen enkele afdeling
staan. Typen hielp niet: er viel niets te doorzoeken.

- **Oorzaak**: bij het gebruikersbeheer van gisteren is de groepenlijst achter de
  blokkadecontrole gezet. In die striktere vorm ging het optellen van een hele
  afdeling mis — de database rekende het totaal uit als kommagetal terwijl er een
  heel getal beloofd was, en weigerde daarop het hele antwoord.
- **Opgelost** in `database/14_groepenlijst_hersteld.sql`. De afdelingen, laden
  en aantallen zijn ongewijzigd; alleen het totaal komt er weer goed uit.

Alleen de database; aan de website verandert niets.

## 05-08-2026 — Pincode vergeten? Zelf een nieuwe kiezen

Wie zijn pincode kwijt was, kon nergens heen: de beheerder kent hem ook niet en
kan hem niet opzoeken. Dat is nu opgelost zonder dat iemand anders de pincode
onder ogen krijgt.

- **"Pincode vergeten?" op het inlogscherm** stuurt een mail met een link. Via die
  link kies je op een eigen pagina een nieuwe pincode, twee keer in te tikken
  tegen typefouten.
- **De site verraadt niet wie er een account heeft.** Of het adres bekend is of
  niet, het antwoord is hetzelfde: "is dit adres bij ons bekend, dan staat er een
  mail voor je klaar".
- **De beheerder kan zo'n mail ook namens iemand versturen** met de knop
  *Herstelmail* in het gebruikersoverzicht. Hij stelt de pincode dus niet zelf in
  en krijgt hem ook niet te zien.
- Een verlopen of al gebruikte link levert een begrijpelijke melding op in plaats
  van een leeg scherm.

Twee dingen om te weten: **de nieuwe pincode moet verschillen van de huidige** —
Supabase weigert dezelfde opnieuw. En de ingebouwde mailer van Supabase stuurt
maar een handvol berichten per uur; voor deze kring van gebruikers ruim genoeg,
maar niet om mee te stoeien.

Instelling in Supabase: onder Authentication → URL Configuration moet de Site URL
`https://bartloe.github.io/dealbot/` zijn, met `https://bartloe.github.io/dealbot/**`
bij de Redirect URLs. Zonder dat komt de link uit de mail bij localhost terecht.

## 05-08-2026 — Na acht uur stilte gaat de sessie eruit

Wie inlogde bleef ingelogd tot hij op Uitloggen klikte. Op een gedeelde of
vergeten laptop stond Dealbot daarmee voor iedereen open.

- **Acht uur zonder enige handeling beëindigt de sessie.** Bij terugkomst staat
  het inlogscherm klaar met de reden erbij.
- **Wie bezig is, merkt er niets van.** Elke klik, toetsaanslag of scrollbeweging
  zet de klok terug op nul; niemand wordt midden in het kijken uitgegooid.
- Staat de pagina uren onaangeroerd open, dan valt hij vanzelf terug op het
  inlogscherm — er hoeft niet eerst iets geklikt te worden.
- Uitloggen wist het moment, zodat de volgende gebruiker met een schone lei begint.

Alleen de website; aan de database verandert niets.

## 05-08-2026 — Gebruikersbeheer: wie er is, en wie er niet meer in mag

De beheerpagina heeft er twee blokken bij gekregen. Aanmelden blijft vrij, maar
er is nu wel te zien wie dat gedaan heeft en er is een manier om in te grijpen.

- **Het overzicht van accounts**: naam, e-mailadres, wanneer het account is
  aangemaakt, wanneer er voor het laatst is ingelogd en hoeveel zoekvragen
  eronder hangen.
- **Op slot zetten** is terug te draaien. Die gebruiker kan nog wel inloggen,
  maar krijgt niets meer te zien: het inlogscherm zegt hem dat zijn account
  geblokkeerd is en de sessie stopt meteen. Ook als hij de website omzeilt komt
  hij niet verder — alle leesrechten in de database lopen sinds deze wijziging
  langs dezelfde controle.
- **Verwijderen** is dat niet: het inlogaccount, het profiel en alle zoekvragen
  gaan weg. Het scherm vraagt eerst om een bevestiging.
- **De beheerder kan zichzelf niet buitensluiten.** Met één beheerder zou er dan
  niemand meer binnenkomen om het terug te draaien; de database weigert het.
- **Een lijst geweerde e-mailadressen.** Blokkeren houdt een bestaand account
  tegen; deze lijst voorkomt dat er met hetzelfde adres een nieuw account bij
  komt. Bewust op adres en niet op IP-nummer: thuisaansluitingen wisselen van
  nummer en op mobiel internet delen duizenden mensen er één, dus daarmee raak je
  vooral de verkeerde.

Database: `database/12_gebruikersbeheer.sql` moet één keer worden uitgevoerd.
Tot dat moment werkt de beheerpagina niet — ook de knop in de balk blijft weg.

## 04-08-2026 — Een beheerpagina: hoe ging het ophalen, en wat kwam eruit

Er was tot nu toe geen plek waar te zien is of het ophalen van vanochtend gelukt
is. Ging een keten stuk, dan zag de site er gewoon uit — alleen met de prijzen
van gisteren. Daar is een beheerpagina voor gekomen, alleen zichtbaar en
bruikbaar voor het beheerdersaccount.

- **Beheerder is een eigenschap van het account, niet van de pagina.** Eén account
  heeft het vlaggetje; alleen dat account krijgt antwoord van de database. Voor
  alle anderen staat de knop niet in de balk, en wie het adres tóch intikt krijgt
  te horen dat de pagina niet voor hem is. Een gebruiker kan zichzelf geen
  beheerder maken: van zijn eigen profiel mag hij vanaf de website alleen nog de
  weergavenaam wijzigen.
- **De laatste ronde per winkel**: wanneer, gelukt of mislukt, hoeveel er binnenkwam
  en bij een storing de melding uit het logboek. Een winkel die nog nooit heeft
  gedraaid blijft in de lijst staan — dat je van Nettorama niets ziet, is zelf ook
  een bericht.
- **Het logboek vermeldt voortaan het soort ronde.** Vomar levert onder één
  winkelnummer twee dingen: zijn schapprijzen en zijn voorgelezen folder. Die waren
  niet uit elkaar te houden, waardoor een geslaagde prijzenronde een mislukte folder
  kon verbergen. Nu staan ze apart in het overzicht.
- **De kwaliteit van de gegevens**: per winkel hoeveel aanbiedingen en schapprijzen
  er staan, en hoeveel daarvan geen kiloprijs of geen plek in onze eigen indeling
  hebben — met het percentage erbij.
- **De knop om de run met de hand te starten is verhuisd** van de aanbiedingen-pagina
  naar beheer. Op de aanbiedingen-pagina blijft alleen de regel staan wanneer er
  voor het laatst is opgehaald.

Database: `database/11_beheer.sql` moet één keer worden uitgevoerd. Dat moet
gebeuren vóór de eerstvolgende ochtendrun, want het ophaalscript schrijft het
soort ronde vanaf nu mee in het logboek.

## 04-08-2026 — De startpagina ordent per afdeling en groep

Nu een zoekvraag over een hele afdeling kan gaan, kwamen er op de startpagina zo
veel producten onder elkaar te staan dat je erin verdwaalde. De gevonden
producten staan daarom voortaan in blokken per afdeling, met de groep als
tussenkopje erbinnen.

- **Elke afdeling is een blok dat je open- en dichtklapt**, met het aantal
  producten erachter. Tot en met zes afdelingen staat alles meteen open; heb je er
  meer, dan zijn de blokken dicht en zie je eerst waar iets ligt.
- **De groep staat als tussenkopje boven zijn producten**, zodat binnen een grote
  afdeling nog steeds te zien is wat waar hoort.
- **Producten waarvan de plek niet bekend is, komen onder "Overig"** — helemaal
  onderaan, maar ze verdwijnen niet uit beeld.
- **Hetzelfde product bij twee winkels blijft één kaart.** Deelt de ene winkel het
  fijner in dan de andere, dan telt de indeling die het vaakst voorkomt; kent maar
  één winkel de groep, dan wint die — een bekende groep zegt meer dan een lege.
- De samenvatting bovenaan noemt er de afdelingen bij: "12 producten met een
  aanbieding voor jou, in 3 afdelingen."

Alleen de website; aan de database verandert niets.

## 04-08-2026 — Eén keer aanvinken, alle winkels tegelijk

Het profielscherm zoekt niet meer in de groepsnamen van de winkels, maar in onze
eigen indeling. Je vinkt **Koffiebonen** aan en ziet daarmee de koffiebonen van
alle winkels tegelijk — 32 aanbiedingen bij vijf ketens deze week. Voorheen moest
je dat bij elke keten apart doen, in de woorden van die keten ("Koffiebonen" bij
Albert Heijn, "lokaal Koffiebonen" bij Jumbo, "Koffie & cacao" bij Dirk), en bij
Vomar kon het helemaal niet omdat de folder geen groep meelevert.

### Hoe het scherm er nu uitziet

- **Kiezen gaat door 28 afdelingen die je openklapt**, met daaronder de groepen
  om aan te vinken. Zoeken kan ook: typ "koffie" en alleen wat past blijft staan,
  opengeklapt.
- **Bovenaan elke afdeling staat "Alles uit …"**. Dat is meer dan een gemak: van
  de ingedeelde aanbiedingen kwam 12% niet verder dan de afdeling (de winkelgroep
  was te grof). Wie alleen groepen aanvinkt, mist die; wie de afdeling aanvinkt,
  krijgt ze erbij. Het aantal achter de afdeling telt ze mee.
- **Achter elke regel staat wat erin zit** ("nu 32 aanbiedingen"), en een groep
  die nu leeg is blijft gewoon te kiezen: de zoekvraag staat klaar tot er iets van
  in de bonus komt.
- **Wat je al volgt, is niet nog eens aan te vinken** — dat zou dezelfde zoekvraag
  dubbel opslaan.
- Zoeken op merk of op een woord in de productnaam blijft gewoon bestaan, voor
  wat niet in een groep te vangen is.

### In de database

`database/10_indeling_in_profiel.sql` moet één keer gedraaid worden. De zoekvraag
krijgt daarin een afdeling en een groep in plaats van een winkelgroepsnaam, en het
matchen gaat over onze eigen indeling. **De bestaande zoekvragen worden gewist**:
ze wijzen naar een zoekingang die verdwijnt, en dit is nog de testfase. De
groepsnaam van de winkel zelf blijft ongemoeid op de aanbieding staan — die is de
bron van de vertaling en op de winkelpagina, waar je door één folder bladert,
juist de logische indeling.

## 04-08-2026 — De hele winkel onder onze eigen indeling

Het proefstuk met alleen Koffie & thee werkte, dus nu staat het complete
assortiment in de indeling: **28 hoofdgroepen met 252 subgroepen**. Het skelet
komt opnieuw van de winkelindeling van Albert Heijn (29 afdelingen, 313 laden),
vers opgehaald en niet uit het hoofd nagemaakt.

### Vier keuzes die van Albert Heijn afwijken

- **"Glutenvrij" is bij ons geen afdeling.** Glutenvrij is een eigenschap van een
  product, geen plek in de winkel: glutenvrij brood is brood. Als aparte afdeling
  zou het brood op twee plekken staan en vond je met "Brood" niet alles.
- **De twee AH-eigen shops zijn vervangen** door "Huis, tuin & vrije tijd" en
  "Bloemen & planten" — precies de schappen waarin Lidl zijn wekelijkse non-food
  kwijt kan.
- **"Koken, tafelen, vrije tijd" is gesplitst**, anders lagen pannen, kaarsen,
  kleding en tijdschriften in één bak.
- **Elke subgroepnaam komt maar één keer voor.** De naam is de sleutel waarmee de
  afdeling wordt opgezocht; hing "Verspakketten" onder twee afdelingen, dan was
  niet meer te zeggen welke bedoeld werd.

### Twee regels die door alle takken heen lopen

- **De diepvries wint.** Vissticks zijn vis, maar wie ze zoekt loopt naar de
  vriezer — en zo staat het ook in elke winkel. Een rol diepvrieszakken trapt
  daar niet in: die blijft huishoudartikel.
- **De productnaam mag alleen aanvullen binnen de afdeling die de winkel al
  noemde.** Zegt de winkel "Kaas", dan blijft het bij de kaas staan, hoe hard het
  woord koffiebonen in de productnaam ook roept.

### Wat het oplevert

**5984 van de 7159 aanbiedingen** hangen nu onder onze indeling (84%). Per
winkel: Albert Heijn 4610, Jumbo 1192, Vomar 124, Dirk 57, Lidl 1. Van het
vertaalboekje staan 2018 winkelgroepen vertaald, waarvan 1982 een plek kregen.

Van de ingedeelde aanbiedingen kwam 12% niet verder dan de afdeling: de
winkelgroep was te grof en de productnaam gaf niets prijs. Die staan zichtbaar in
de lijst, zodat er bijgestuurd kan worden in plaats van dat ze stilletjes
verdwijnen.

### Nog te doen

588 groepsnamen wachten nog (Jumbo 405, Dirk 140, Lidl 43): de dagvoorraad
AI-vragen was op. Eén keer `python scripts/indeel.py` draaien maakt het af; wat
al vertaald is wordt overgeslagen. Vooral Dirk en Lidl hebben er baat bij — die
staan nu nog vrijwel helemaal in de restbak.

Daarna kan de website de nieuwe indeling gaan gebruiken.

### Twee reparaties onderweg

- **Een vertaalronde raakt zijn werk niet meer kwijt.** De eerste grote ronde
  vertaalde 2490 groepsnamen en verloor er bij het opslaan ruim duizend van:
  alles ging pas aan het eind naar de database, en één dubbele groepsnaam in een
  blok laat de database het héle blok weigeren. Nu gaat elk vertaald blok er
  meteen in, en een groepsnaam die twee keer in een antwoord staat levert nog
  maar één regel op.
- **Het indelen is honderd keer sneller.** De trefwoorden werden bij élk product
  opnieuw opgeschoond. Met ruim 1300 trefwoorden en duizenden aanbiedingen liep
  dat vast; nu gebeurt het één keer bij het opstarten en gaan 20.000 producten er
  in iets meer dan een seconde doorheen.

## 03-08-2026 — Een eigen productindeling: proefstuk Koffie & thee

Elke winkel deelt zijn assortiment anders in. Albert Heijn zegt "Koffiebonen",
Jumbo zegt "lokaal Koffiebonen", Dirk gooit alles op één hoop ("Koffie & cacao")
en de voorgelezen Vomar-folder levert helemaal geen groep. Samen 2606 losse
groepsnamen, en met één zoekvraag vond je nooit alle winkels.

Daar staat nu één eigen indeling boven: **hoofdgroep en subgroep, in onze eigen
woorden**. Elk product hangt daaronder, ongeacht wat de winkel er zelf van vindt.
Als proefstuk is één tak gebouwd — Koffie & thee — over alle vijf de winkels.

### Hoe het werkt

- **Het skelet komt van Albert Heijn.** Zijn winkelindeling (29 afdelingen met
  313 laden) is al twee lagen diep, staat in gewoon Nederlands en dekt het hele
  assortiment. Eén keer overgenomen, daarna van ons: hij verandert niet mee als
  Albert Heijn morgen iets hernoemt.
- **Vertaald wordt er per groep, niet per product.** Er zijn 2606 winkelgroepen
  tegenover tienduizenden producten, dus één groep vertalen dekt er duizenden in
  één klap — en volgende week gelden dezelfde groepen nog gewoon.
- **Het vertalen doet de AI die er al zat** (dezelfde die de folder voorleest),
  en het antwoord wordt bewaard. Een gewone ophaalronde 's ochtends kost daardoor
  geen enkele AI-vraag.
- **De productnaam is het vangnet** voor Dirk (te grof) en de Vomar-folder (geen
  groep). Zo komen Dirks koffiebonen alsnog onder "Koffiebonen" terecht.
- **De groep van de winkel zelf blijft gewoon staan.** Op de winkelpagina — waar
  je door één folder bladert — is die juist de logische.

### Drie soorten winkelgroep, en waarom dat nodig was

Bij de eerste proef belandde "Nivea Men **Espresso** deodorant" bij de koffie, en
"AH Brownie espresso" ook. Dat werd rechtgezet door onderscheid te maken:

1. **De groep valt onder onze indeling** → die is leidend.
2. **De groep valt er zeker niet onder** (deodorant, chocoladerepen) → het product
   telt niet mee. De winkel heeft al gezegd wat het is.
3. **De groep is gemengd** ("IJskoffie en milkshakes") → het product telt pas mee
   als zijn eigen naam laat zien dat het erbij hoort. Zonder deze derde soort moet
   je kiezen tussen milkshakes bij de koffie, of de ijskoffie kwijtraken.

### Wat het proefstuk opleverde

340 koffie- en thee-aanbiedingen, over alle vijf de winkels:

| Subgroep | AH | Jumbo | Dirk | Vomar | Lidl |
| --- | --- | --- | --- | --- | --- |
| Thee | 87 | – | 35 | 1 | – |
| IJsthee | 40 | 23 | – | – | – |
| Koffiecups | 3 | 33 | 21 | 2 | – |
| Koffiebonen | 9 | 21 | – | 1 | 1 |
| Filterkoffie | 23 | – | 1 | 1 | – |
| Cacao & chocolademelk | 12 | 8 | – | – | – |
| IJskoffie | – | 15 | – | – | – |
| Oploskoffie, Koffiemelk | 1 | 1 | – | – | – |

Gecontroleerd: een steekproef van vijftig stond **vijftig keer op de goede plek**.
Van alles wat naar koffie of thee ruikt bleef 2% buiten de indeling — vrijwel
allemaal terecht (deodorant, brownie, limonadesiroop). Dat Dirk geen koffiebonen
heeft klopt: hij heeft er deze week simpelweg geen in de bonus, alleen Hak-bonen.

De AI hield zelf de valstrikken tegen: "Theeworst" is worst, "Wasmiddel capsules"
zijn geen koffiecups, en chocoladerepen horen niet bij de cacao.

### Nog te doen

De website gebruikt de nieuwe indeling nog niet — eerst moeten de overige 28
takken erbij (groente, zuivel, vlees, enzovoort). Dat is herhaalwerk: takken in
`indeling.py` zetten en `indeel.py` draaien.

## 03-08-2026 — Nieuwe pagina: aanbiedingen per winkel

Naast je eigen zoekvragen kun je nu ook gewoon door een winkel bladeren. Bovenaan
de pagina staan de logo's van de winkels; klik er één aan en je ziet alles wat
daar deze week in de aanbieding is, geordend per productgroep.

- **Kiezen doe je op het logo.** Onder elk logo staat hoeveel er deze week ligt,
  zodat je meteen ziet waar iets te halen valt. De gekozen winkel blijft achter
  het adres staan (`winkel.html#jumbo`): verversen houdt je bij dezelfde winkel.
- **Alles van de lopende week.** Aanbiedingen met een periode moeten vandaag
  geldig zijn; zo verdwijnt een weekendactie vanzelf zodra het weekend voorbij is.
- **Per productgroep, goedkoopste bovenaan.** Elke groep is een blokje dat je
  open- en dichtklapt. Bij winkels met veel groepen staat alles dichtgeklapt: je
  ziet dan eerst de indeling en klapt open wat je interesseert.

### Wat er per winkel te zien is

| Winkel | Aanbiedingen | Productgroepen |
| --- | --- | --- |
| Albert Heijn | 4624 | 140 |
| Jumbo | 1227 | 248 |
| Dirk | 405 | 55 |
| Vomar | 153 | geen indeling |
| Lidl | 82 | 38 |

### Twee dingen om te weten

- **Vomar komt zonder productgroep binnen.** Zijn aanbiedingen worden uit de
  folder voorgelezen, en daar wordt nu geen groep bij vastgelegd. Alle 153 staan
  daarom onder één kopje "Overig". Dat is te verhelpen door de folderlezer ook om
  een productgroep te vragen; staat op de takenlijst.
- **Albert Heijn is fors gegroeid.** Er staan 4624 aanbiedingen, veel meer dan de
  1024 uit de bonusfolder: de meerpakken tellen mee. De pagina bouwt een groep
  daarom pas op als je hem openklapt, anders wordt hij traag.

## 03-08-2026 — Lidl erbij als vijfde winkel

Lidl doet mee. Zijn aanbiedingenpagina draagt de prijzen zelf bij zich, dus er
is geen folder, geen AI en geen inloggen nodig: één verzoek per ochtend levert
de hele week.

- **108 aanbiedingen, 89 daarvan met een kiloprijs (82%).** Ze staan in de
  database en zijn op de website te zoeken.
- **De hele week in één keer.** De acties die op maandag beginnen staan er, maar
  ook die van woensdag en vrijdag. Elke aanbieding houdt zijn eigen begindatum,
  zodat te zien is vanaf wanneer je hem kunt halen.
- **46 productgroepen** ("Yoghurt", "Bier & Cider") zijn aan te vinken op het
  profielscherm.

### Twee dingen om te weten

- **Veertig aanbiedingen gelden alleen met de Lidl Plus-kaart.** Dat is bij Lidl
  geen uitzondering maar een derde van de folder, vooral groente, fruit en vlees.
  Ze tellen mee — het zijn echte aanbiedingen — maar er staat "met Lidl Plus"
  bij, zodat je niet voor een verrassing bij de kassa staat.
- **Lidl deelt zijn eigen producten weleens raar in.** "Bruine bollen" staat bij
  hem onder "Chocoladeproducten". Dat nemen we over zoals hij het aanlevert; het
  komt alleen voor bij de groep, niet bij de prijs.

### Wat Lidl niet geeft

Schapprijzen en streepjescodes. Alleen wat in de aanbieding ligt heeft een prijs,
dus Lidl komt niet op de standaardprijzen-pagina en is niet op streepjescode aan
Vomar te koppelen.

## 03-08-2026 — de folder van Vomar wordt voorgelezen

Gisteren stond hier nog dat de aanbiedingen van Vomar onbereikbaar zijn. Dat is
niet meer zo. Ze staan nog steeds alleen in de folder, maar die folder wordt nu
**voorgelezen door een AI die naar de pagina's kijkt** — precies zoals jij dat
zelf zou doen.

- **219 aanbiedingen uit de folder van week 32**, 172 daarvan met een kiloprijs
  (79%). Alle 37 pagina's zijn gelezen.
- **De folder komt vanzelf binnen.** Vomar heeft een vaste ingang "folder deze
  week" die altijd naar de nieuwste uitgave wijst. Daar hangt de folder als PDF
  aan; die halen we op en maken er plaatjes van.
- **De acties gelden niet allemaal even lang.** Een deel van de pagina's is een
  weekendactie ("donderdag 6 t/m zaterdag 8 augustus"), de rest loopt de hele
  week. Elke pagina houdt nu zijn eigen periode aan, afgelezen van de pagina zelf.
- **De folder wordt maar één keer per week gelezen.** Elke ochtend wordt gekeken
  welke uitgave er hangt; staat die er al in, dan gebeurt er niets. Dat scheelt
  ruim dertig AI-vragen per dag.

### Twee dingen die je zo over het hoofd ziet

- **"1+1 gratis" is een valstrik.** Op de omslag stond ijs met 7,58 doorgestreept
  en 3,79 groot in beeld — maar één pak kost gewoon 3,79. Dat grote bedrag geldt
  voor twéé pakken, dus je betaalt 1,90 per pak. Wie dat niet doorheeft, zet de
  aanbieding twee keer zo duur in de lijst. De AI geeft daarom door voor hoeveel
  stuks een bedrag geldt; het rekenwerk doen we zelf.
- **Het paginanummer in de folder klopt niet met het blad in het bestand.** Blad 1
  van de PDF droeg nummer 32. Wij tellen daarom zelf.

### Als Google het even te druk heeft

Bij het eerste proefdraaien kwam de melding "This model is currently experiencing
high demand" langs (foutcode 503). Dat is opgelost zoals in het project subs:

- Bij drukte wordt er **gewacht** (4, 8, 16 en dan 32 seconden) en het bij
  dezelfde sleutel opnieuw geprobeerd. Vraagt Google zelf om een bepaalde
  wachttijd, dan houden we die aan.
- Is een sleutel **echt op voor vandaag**, dán pas gaat de volgende sleutel aan
  de beurt. Er staan er nu tien klaar, elk met een eigen dagvoorraad.
- Dat verschil is het hele punt: Google gebruikt voor "je gaat te snel" en "je
  bent door je dagvoorraad heen" dezelfde foutcode. Bij twijfel wachten we, want
  wachten kost niets en een goede sleutel afschrijven wel.

Tijdens het lezen van deze folder gebeurde precies dat: na achttien pagina's was
de eerste sleutel op, en zonder haperen ging het verder op de tweede. Op de
laatste pagina viel de verbinding weg; ook dat werd op de volgende sleutel
gewoon afgemaakt.

## 02-08-2026 — de standaardprijzen-pagina werkt, met dank aan Vomar

- **De pagina "Standaardprijzen" is niet langer een belofte.** Je kunt er nu
  opzoeken wat iets gewoon kost als er even geen aanbieding is: zoek op een merk
  of productnaam, of kies een productgroep. De treffers staan van goedkoop naar
  duur per kilo, met een link naar de winkel.
- **Vomar staat weer aan — maar alleen voor prijzen, niet voor aanbiedingen.**
  Hij levert **6.174 producten**, allemaal met een kiloprijs én allemaal met een
  streepjescode. Dat laatste heeft geen enkele andere keten. Het ophalen kost
  twee verzoeken en duurt een halve seconde.
- **Vomar deelt dieper in dan Dirk.** Drie lagen: 10 afdelingen, 85 hoofdgroepen
  en **339 groepen** als *Koffiebonen*, *Koffiecups* en *Oploskoffie*. Dat is
  hetzelfde niveau als de laden van Albert Heijn.
- Die groepen komen bewust **niet** in de keuzelijst van je profiel. Vomar levert
  geen aanbiedingen, dus een zoekvraag op zo'n groep zou nooit een treffer geven.
  Ze staan alleen op de standaardprijzen-pagina zelf.

### Waar supermarktscanner.nl zijn Vomar-prijzen vandaan haalt

Op hun koffiebonen-pagina stonden veertien Vomar-producten, terwijl wij
dachten dat er bij Vomar niets te halen viel. Uitgezocht:

- Ze gebruiken **de webshop-ingang van Vomar zelf**. De prijzen kloppen tot op de
  cent. Wij halen daar nu hetzelfde vandaan — en completer: Vomar voert 21
  soorten koffiebonen, supermarktscanner toont er 14.
- Het zijn **gewone winkelprijzen, geen aanbiedingen**. Van hun veertien
  Vomar-kaarten had er geen enkele een "t/m zondag"-datum; bij Albert Heijn zeven
  van de vierentwintig.
- **De aanbiedingen van Vomar blijven onbereikbaar,** en dat is nu uitgezocht in
  plaats van vermoed. De ingang kent geen actieprijs en geen einddatum. Er zit
  een aanzet in hun website (een pagina "Discount Deals" en een kortingsvlaggetje),
  maar die staat uit. De folder bevat alleen drukwerk waarin de productnamen op
  één hoop staan en de bedragen op een andere — met prijzen als "99 3." voor
  € 3,99. Zetten ze hun Discount Deals ooit aan, dan is dat het moment om terug
  te komen.

## 02-08-2026 — Dirk is acht keer zo fijn ingedeeld

- **Dirk bleek méér te publiceren dan zijn 17 grove afdelingen.** Onder
  "Dranken, sap, koffie & thee" zit een tweede laag met onder meer *Koffie &
  cacao*, *Thee*, *Bier* en *Vruchtensappen*. In totaal **146 groepen** in plaats
  van 17. Dat gegeven kwam al met elke aanbieding mee — het werd alleen gebruikt
  om de link naar dirk.nl mee te bouwen, niet om op te zoeken.
- **In de keuzelijst staan nu die 146 groepen.** Wie op koffie zoekt krijgt bij
  Dirk niet langer het hele drankenschap mee, inclusief bier en thee. Op dit
  moment liggen er 22 dingen uit *Koffie & cacao* in de aanbieding.
- Vreemde afdelingen als "DekaGebak" en "Non food inout" zijn uit de lijst
  verdwenen; die hoorden bij de oude grove indeling.
- **Dieper gaat het bij Dirk niet.** Een groep *Koffiebonen* bestaat daar niet:
  het veld voor een derde laag zit wel in hun systeem, maar komt leeg terug en
  staat niet op de producten. Wil je bij Dirk echt alleen bonen, gebruik dan
  **Vrije tekst** — Dirk zet het woord "Koffiebonen" gewoon in de productnaam
  (34 producten in het schap). Dat is precies wat vergelijkingssites als
  supermarktscanner.nl doen: die gebruiken helemaal geen productgroepen.
- Levert Dirk een keer geen groep mee, dan valt Dealbot terug op de afdeling;
  gaat het ophalen van de hele lijst mis, dan blijven de 17 afdelingen staan.
  Beide terugvallen zijn afgedekt met een controle (`scripts/tests/test_dirk.py`).

## 01-08-2026 — zoeken op koffiebonen kan nu ook bij Albert Heijn

- **Bij Albert Heijn zat het merk in de groepsnaam.** De groepen heetten
  "Lavazza koffiebonen", "Perla koffiebonen", "Douwe Egberts koffiebonen" — 1791
  stuks, allemaal merk plus product door elkaar. Wie alle koffiebonen wilde zien
  moest er veertien apart aanvinken, en een nieuw merk miste hij alsnog.
- Albert Heijn heeft die algemene indeling wél: **29 afdelingen met daaronder
  313 laden**, waaronder gewoon *Koffiebonen*. Die naam stond alleen niet op de
  producten zelf. Dealbot loopt de winkelindeling nu lade voor lade af en
  onthoudt bij elk product waar het lag.
- **Eén keuze "Koffiebonen" pakt nu alle merken**, ook merken die er volgend jaar
  bij komen. Op dit moment zijn dat 22 weekaanbiedingen bij Albert Heijn — de
  goedkoopste is Douwe Egberts Aroma rood voordeelpak voor € 14,24 per kilo.
- Alleen op een merk zoeken kan nog steeds: kies de groep *Koffiebonen* en vul
  daarbij het veld **Merk** in. Dat veld stond er al.
- **Bijvangst: Jumbo noemt zijn laden bijna net zo.** Een zoekvraag bewaart alleen
  de naam van de groep, dus "Koffiebonen" zoekt vanaf nu bij Albert Heijn én
  Jumbo tegelijk.
- Van de 34.706 producten bij Albert Heijn liggen er **7 in geen enkele lade**;
  die houden hun oude schaplabel. Dirk blijft achter met zijn 17 grove
  afdelingen — daar is bij die winkel niets fijners te halen.
- De keuzelijst wordt voortaan **opgeschoond** in plaats van alleen aangevuld:
  groepsnamen die een winkel niet meer gebruikt, verdwijnen. Komt er uit een
  ronde een verdacht korte lijst, dan wordt er niets weggegooid.
- De ochtendronde bij Albert Heijn duurt hierdoor ongeveer **vier minuten** in
  plaats van anderhalve.

## 01-08-2026 — de keuzelijst dekt nu de hele winkel

- **Je kon alleen kiezen uit groepen die ooit in de bonus hadden gelegen.** Dat
  is precies verkeerd om: een zoekvraag is er juist om te wáchten tot iets in de
  aanbieding komt. Stond een groep nog nooit in de folder, dan was hij niet aan
  te vinken en werd hij volgende week dus gemist.
- Dealbot haalt nu **per winkel de volledige indeling van het hele assortiment**
  op. De keuzelijst groeide van 511 naar **3962 productgroepen**: Albert Heijn
  1791, Jumbo 2153 en Dirk 17.
- **Jumbo deelt voortaan net zo fijn in als Albert Heijn.** We bewaarden de hele
  afdeling ("Koffie en thee", 18 stuks) — te grof om iets aan te hebben. Elk
  product noemt zijn hele indelingspad, dus nemen we de onderste laag:
  *Koffiebonen*, *Zwarte thee*, *Verzorgende shampoo*. Zoeken op "koffiebonen"
  vindt nu bij twee winkels iets in plaats van bij één.
- Bij Dirk komen alle **17 afdelingen** in de lijst in plaats van de 11 waar
  deze week toevallig iets van in de folder stond.
- Aanvinken kan ongeacht of er nu iets in ligt; achter elke groep blijft staan
  *nu 10 aanbiedingen* of *nu niets in de bonus*.
- De database gaf hooguit duizend regels per keer terug. Met bijna vierduizend
  groepen viel driekwart stil weg, dus de website haalt de lijst nu in blokken
  op.

## 01-08-2026 — de meerpakken zijn boven water

- **De folder blijkt tóch niet alles te noemen.** De koffiebonen 3-packs van
  Douwe Egberts en L'OR liggen deze week in de bonus, maar de bonusfolder noemt
  alleen de losse pakken. Meerpakken staan bij Albert Heijn alleen in het
  assortiment, niet in de folder.
- We hebben eerst geteld hoe groot het gat was: van de **6538 aanbiedingen die
  deze week bij Albert Heijn lopen, stonden er 4487 niet in de folder** — 4263
  meerpakken en 224 gewone schapaanbiedingen (snoepgroente, aardbeien, mango).
- Naast de folder loopt Dealbot nu **het hele assortiment langs op bonuslabel**
  en vult aan wat de folder mist. Dat kost ongeveer een halve minuut extra.
- **Meerpakken tellen alleen mee als het losse product zelf in de bonus is.**
  Dan is het meerpak dezelfde weekaanbieding in een grotere verpakking: een
  2-pack voor de halve prijs hoort bij "1 + 1 gratis" op het losse pak. Ligt het
  losse product niet in de bonus, dan is het een staffelkorting die het hele
  jaar geldt ("10% volume voordeel") — die blijft eruit. Zo vielen 2356
  blijvende volumekortingen af.
- **Een meerpak krijgt een echte kiloprijs.** Albert Heijn noemt een 3-pack
  koffiebonen "3 stuks", en daar valt niets uit te rekenen. Dealbot kijkt naar
  het losse pak (500 g) en maakt er 1500 g van. De 3-pack Excellent gold komt zo
  op € 19,98 per kilo — duurder dan het losse pak met 2e halve prijs (€ 17,99),
  en dat zie je nu in één oogopslag.
- Blijvende webshopkortingen van de AH Voordeelshop (parfumsets die tot 31
  december in de bonus staan) blijven eruit: die horen niet in een weeklijst.
- Resultaat: **4202 aanbiedingen in plaats van 2089.** Mislukt het langslopen
  van het assortiment, dan gaat de ronde gewoon door met de folder alleen.

## 01-08-2026 — productgroepen zoeken in plaats van scrollen

- **De keuzelijst is een zoekveld geworden.** Met 479 groepen bij Albert Heijn
  alleen al was scrollen geen doen, en zoeken op "koffie" leverde niets op: die
  groepen heten *Douwe Egberts koffiebonen* en staan dus onder de D. Nu typ je
  een woord en vind je alles waar dat woord ín zit, waar het ook staat.
- **Je zoekt dwars door alle winkels heen.** Achter elke treffer staat bij welke
  winkel hij hoort. "koffie" geeft nu 11 treffers verdeeld over Albert Heijn,
  Jumbo en Dirk.
- **Meerdere tegelijk aanvinken kan.** Elke aangevinkte groep wordt een eigen
  zoekvraag; met één klik zet je er dus drie klaar bij drie winkels. Je keuzes
  blijven boven het zoekveld staan terwijl je verder zoekt.
- Achter elke treffer staat wat erin zit: *nu 10 aanbiedingen* of *nu niets in
  de bonus*. Groepen die met je zoekwoord beginnen staan bovenaan, daarna wat er
  nu daadwerkelijk in de bonus ligt.
- Merk en vrije tekst blijven een apart formulier, want die twee typ je zelf.

## 01-08-2026 — Albert Heijn: we zagen maar een deel van de bonus

- **De koffiebonen zijn boven water.** Dealbot haalde de aanbiedingen van Albert
  Heijn op via hun zoekingang, en die laat niet verder kijken dan 3000
  producten. Alles daarna viel buiten beeld — en koffiebonen stonden nu eenmaal
  verderop in de rij. Dat was geen instelling die te hoog stond: het is een
  harde grens van Albert Heijn zelf.
- Voortaan lopen we **de bonusfolder van de week** af, hoofdstuk voor hoofdstuk
  en aanbieding voor aanbieding. Die folder ís de bonus, dus daar kan per
  definitie niets buiten vallen.
- Resultaat: **2089 aanbiedingen in plaats van 1598**, met 15 soorten
  koffiebonen erbij en twee nieuwe productgroepen (*Douwe Egberts koffiebonen*
  en *L'OR koffiebonen*). Het aantal groepen groeide van 283 naar 479.
- Acties van Gall & Gall en Etos staan in dezelfde folder maar blijven eruit —
  die koop je niet in de supermarkt.
- Weigert Albert Heijn tussendoor even (dat gebeurde gisterochtend), dan wacht
  Dealbot nu en probeert het opnieuw. Mislukt meer dan een vijfde van de folder,
  dan schrijft hij bewust níets weg: dan blijft de volledige lijst van gisteren
  staan in plaats van dat er een halve lijst voor in de plaats komt.

## 01-08-2026 — te zien wanneer er voor het laatst is opgehaald

- Onder de kop van de startpagina staat nu **"Laatste run gedraaid op: 01-08
  12:23"**. Zo is in één oogopslag te zien of de lijst van vanochtend is of van
  eergisteren.
- Is er ná die ronde nog een poging mislukt, dan staat dat er in het rood bij.
  De lijst is dan ouder dan je op grond van de klok zou denken, en dat hoor je
  te weten vóór je naar de winkel gaat.
- De regel verschijnt in Nederlandse tijd, ook als je in het buitenland kijkt.
  Lukt het opzoeken niet, dan blijft de regel gewoon weg — de aanbiedingen zelf
  gaan voor.

## 31-07-2026 (middag) — kiezen uit alle groepen, niet alleen die van deze week

- **De keuzelijst bij Productgroep bevat voortaan alles wat Dealbot ooit is
  tegengekomen.** Hij werd gevuld met alleen de groepen die op dat moment in de
  bonus lagen, en dat is precies verkeerd om: een zoekvraag zet je juist om te
  wachten tot iets in de aanbieding komt. "Koffiebonen" was daardoor niet te
  kiezen.
- Achter elke groep staat nu wat erin zit: *"Koffiebonen — nu niets in de
  bonus"* of *"Perla filterkoffie — nu 7 aanbiedingen"*. Groepen met
  aanbiedingen staan bovenaan bij hun winkel, lege groepen eronder.
- Dealbot houdt die lijst zelf bij: elke ochtendrun voegt toe wat hij tegenkomt.
  De lijst raakt dus nooit iets kwijt, ook niet als een winkel een groep een
  week overslaat.
- Mislukt het bijhouden, dan gaat de ophaalronde gewoon door — de aanbiedingen
  zelf staan dan al veilig in de database.

## 31-07-2026 (ochtend) — ochtendrun mislukte, hersteld

- De ronde van vanochtend schreef niets weg: de database herkende het
  hernoemde veld `productgroep` nog niet, omdat zijn interne overzicht van de
  tabellen na de naamswijziging van vannacht nog niet was ververst. Alle drie de
  winkels liepen erop stuk.
- De lijst van gisteren bleef gewoon staan — het opruimen gebeurt pas nadat het
  wegschrijven gelukt is, dus de website is geen moment leeg geweest.
- Handmatig opnieuw gedraaid: 3257 aanbiedingen binnen (Albert Heijn 1595,
  Jumbo 1242, Dirk 420). Er is dus niets blijvend mis; het was eenmalig.
- De hulpstukken van de ochtendrun (`checkout` en `setup-python`) zijn
  bijgewerkt naar versie 7. GitHub waarschuwde dat de oude motor eronder
  verdwijnt.

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
