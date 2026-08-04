# Wijzigingen — Dealbot

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
