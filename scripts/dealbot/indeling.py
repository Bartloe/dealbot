"""
===============================================================================
 Dealbot — onze eigen productindeling van twee lagen

 Versie      : 2.0
 Reden       : Het proefstuk met alleen "Koffie & thee" is geslaagd: 340
               aanbiedingen van vijf winkels hangen onder één indeling. Daarmee
               is bewezen dat de aanpak werkt en gaat nu het hele assortiment
               erin — 28 hoofdgroepen met samen ruim 280 subgroepen.

               Twee dingen zijn onderweg veranderd. Ten eerste worden de
               trefwoorden nu één keer bij het opstarten opgeschoond in plaats
               van bij elk product opnieuw; met dit aantal woorden zou dat laatste
               het indelen van tienduizenden aanbiedingen onwerkbaar traag maken.
               Ten tweede is de lijst uitzonderingen bijna leeg: woorden als
               "theeworst" en "hagelslag" hoeven niet meer geblokkeerd te worden,
               want die hebben nu gewoon hun eigen plek in de indeling.
 Datum       : 03-08-2026 23:10

 Onderdelen:
   INDELING             - de eigen indeling: hoofdgroepen met hun subgroepen
   TOELICHTING          - uitleg bij de subgroepen waar verwarring dreigt
   TREFWOORDEN          - woorden in een productnaam die een subgroep verraden
   HOOFD_TREFWOORDEN    - woorden die alleen de afdeling aanwijzen
   UITZONDERINGEN       - folderregels die helemaal geen product zijn
   Plek                 - waar een product hoort: hoofdgroep + eventuele subgroep
   schoon()             - naam opschonen om te kunnen vergelijken
   subgroepen()         - de subgroepen van één hoofdgroep
   hoofdgroep_van()     - bij welke hoofdgroep hoort deze subgroep
   bestaat()            - is dit een bestaande combinatie?
   uit_naam()           - lees de plek af uit de productnaam (het vangnet)
   plaats()             - de eindregel: winkelgroep eerst, productnaam als vangnet
===============================================================================
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# -----------------------------------------------------------------------------
# De eigen indeling.
#
# Het skelet komt van de winkelindeling van Albert Heijn (29 afdelingen met 313
# laden): die is al twee lagen diep, staat in gewoon Nederlands en dekt het hele
# supermarktassortiment. Hij is één keer overgenomen en daarna van ons — hij
# verandert dus niet mee als Albert Heijn morgen iets hernoemt.
#
# Vier keuzes die van Albert Heijn afwijken, met de reden erbij:
#
#   - "Glutenvrij" is bij ons geen afdeling. Glutenvrij is een eigenschap van een
#     product, geen plek in de winkel: glutenvrij brood is brood. Zou het een
#     eigen hoofdgroep zijn, dan stond het brood op twee plekken en vond je met
#     "Brood" niet alles. Hetzelfde geldt voor lactosevrij en halal — behalve waar
#     het werkelijk een apart schap is (halal vlees, lactosevrije kaas).
#   - "AH Voordeelshop" en "AH Bloemenshop" zijn winkels van Albert Heijn zelf,
#     geen boodschappenafdelingen. Wat er functioneel in ligt komt terug als
#     "Huis, tuin & vrije tijd" en "Bloemen & planten" — dat zijn ook precies de
#     schappen waarin Lidl zijn wekelijkse non-food kwijt kan.
#   - "Koken, tafelen, vrije tijd" is bij ons gesplitst in "Koken & tafelen" en
#     "Huis, tuin & vrije tijd". Anders was het één bak met pannen, kaarsen,
#     kleding, gereedschap en tijdschriften door elkaar.
#   - "Koffiecups" en "Koffiepods" zijn samengevoegd. Voor wie boodschappen doet
#     is dat hetzelfde ding; Senseo-pads zijn wél echt iets anders en blijven los.
#     En "Cacao & chocolademelk" hangt onder Koffie & thee, waar Dirk en Lidl het
#     ook zetten: wie warme dranken zoekt kijkt zo op één plek.
#
# Twee regels die bij elke tak gelden:
#
#   - Diepvries wint. Een diepvriespizza hoort bij Diepvries, niet bij de verse
#     pizza's. Zo staat het in elke winkel en zo zoekt een mens ook.
#   - Elke subgroepnaam komt in de héle indeling maar één keer voor. De naam is
#     namelijk de sleutel waarmee de bijbehorende hoofdgroep wordt opgezocht; zou
#     "Verspakketten" onder twee afdelingen hangen, dan was niet meer te zeggen
#     welke van de twee bedoeld werd. Waar Albert Heijn een lade op twee plekken
#     laat terugkomen, staat hij bij ons dus één keer.
# -----------------------------------------------------------------------------
INDELING: dict[str, tuple[str, ...]] = {
    "Groente & aardappelen": (
        "Aardappelen",
        "Sla & rauwkost",
        "Tomaten, komkommer & paprika",
        "Ui, prei & knoflook",
        "Wortel, kool & knolgroente",
        "Sperziebonen, asperges & mais",
        "Champignons & paddenstoelen",
        "Verse kruiden & pepers",
        "Snoepgroente",
        "Verspakketten & groentemixen",
        "Overige verse groente",
    ),
    "Fruit": (
        "Appels & peren",
        "Bananen",
        "Sinaasappels, mandarijnen & citrusfruit",
        "Aardbeien, bessen & frambozen",
        "Perziken, nectarines & pruimen",
        "Druiven & kiwi",
        "Meloen, ananas & exotisch fruit",
        "Vers gesneden fruit & fruitsalade",
        "Gedroogd fruit",
        "Verse sappen & smoothies",
    ),
    "Maaltijden & salades": (
        "Kant-en-klare maaltijden",
        "Verse soep",
        "Maaltijdsalades",
        "Huzarensalade & slaatjes",
        "Verse pizza & pizzabodems",
        "Verse pasta & verse pastasaus",
        "Verse noedels & woksaus",
        "Hartige taart & quiche",
        "Belegde broodjes",
        "Pannenkoeken & poffertjes",
        "Sushi",
        "Warme snacks (vers)",
    ),
    "Vlees": (
        "Kip",
        "Rundvlees",
        "Varkensvlees",
        "Gehakt",
        "Kalkoen",
        "Lams-, wild- & gevogeltevlees",
        "Verse worst",
        "Ovenschotel, hachee & ragout",
        "Gourmet, fondue & barbecuevlees",
        "Halal vlees",
        "Vleesconserven",
    ),
    "Vis": (
        "Verse vis",
        "Gerookte vis",
        "Gepaneerde vis",
        "Haring & zure vis",
        "Schaal- & schelpdieren",
        "Visconserven",
        "Vissalade & visbeleg",
    ),
    "Vegetarisch & plantaardig": (
        "Vleesvervangers",
        "Visvervangers",
        "Tofu, tempeh & seitan",
        "Plantaardige zuivel",
        "Plantaardige kaas",
        "Plantaardige vleeswaren",
        "Hummus & plantaardige spreads",
        "Vegetarische snacks",
    ),
    "Vleeswaren": (
        "Vleeswaren vers gesneden",
        "Vleeswaren voorverpakt",
        "Ham & gekookte vleeswaren",
        "Kip- & kalkoenfilet (beleg)",
        "Rosbief, carpaccio & filet américain",
        "Leverworst, paté & smeerbaar vleesbeleg",
        "Halal vleeswaren",
    ),
    "Kaas": (
        "Kaasplakken",
        "Kaasstukken",
        "Smeerkaas & roomkaas",
        "Borrelkaas",
        "Geraspte kaas & kookkaas",
        "Buitenlandse kaas",
        "Lactosevrije kaas",
    ),
    "Zuivel & eieren": (
        "Melk",
        "Yoghurt & skyr",
        "Kwark",
        "Vla & pap",
        "Toetjes & pudding",
        "Drinkyoghurt & ontbijtdrank",
        "Slagroom, kookroom & crème fraîche",
        "Boter & margarine",
        "Eieren",
        "Lactosevrije zuivel",
        "Zuivel tussendoortjes",
    ),
    "Bakkerij": (
        "Brood",
        "Broodjes & croissants",
        "Afbakbrood",
        "Beschuit, crackers & knäckebröd",
        "Taart & gebak",
        "Zoete bakkerijsnacks",
        "Hartige bakkerijsnacks",
        "Bakproducten & bakmixen",
        "Glutenvrij brood",
    ),
    "Borrel, chips & noten": (
        "Chips",
        "Zoutjes",
        "Noten & pinda's",
        "Popcorn",
        "Borrelhapjes",
        "Borrelplank & tapas",
        "Dips & smeersels",
        "Toast & toastsalade",
        "Droge worst",
    ),
    "Pasta, rijst & wereldkeuken": (
        "Pasta",
        "Rijst",
        "Noedels & mie",
        "Couscous, quinoa & bulgur",
        "Peulvruchten & bonen (droog)",
        "Aziatische keuken",
        "Italiaanse keuken",
        "Mexicaanse keuken",
        "Mediterrane & Midden-Oosterse keuken",
        "Surinaamse & Antilliaanse keuken",
        "Hollandse keuken",
        "Maaltijdmixen",
    ),
    "Soepen, sauzen & smaakmakers": (
        "Soep uit blik of pak",
        "Warme sauzen & maaltijdsauzen",
        "Ketchup, mayonaise & koude sauzen",
        "Bouillon",
        "Kruiden & specerijen",
        "Olie & azijn",
        "Frituurvet",
        "Groente in blik of pot",
        "Fruit in blik of pot",
        "Suiker, zout & peper",
    ),
    "Koek, snoep & chocolade": (
        "Koek",
        "Snoep",
        "Drop",
        "Chocolade",
        "Pepermunt & keelpastilles",
        "Kauwgom",
        "Trakteren & uitdeelzakjes",
    ),
    "Ontbijtgranen & broodbeleg": (
        "Ontbijtgranen & muesli",
        "Havermout",
        "Hagelslag & vlokken",
        "Pindakaas & notenpasta",
        "Jam, honing & stroop",
        "Chocoladepasta",
        "Hartig broodbeleg",
        "Ontbijtkoek",
        "Zaden, pitten & superfoods",
    ),
    "Tussendoortjes": (
        "Mueslirepen & notenrepen",
        "Proteïnerepen",
        "Fruitbiscuit & melkbiscuit",
        "Rijstwafels & maiswafels",
        "Knijpfruit & fruitsnacks",
    ),
    "Diepvries": (
        "Diepvries groente",
        "Diepvries fruit",
        "Diepvries aardappel & friet",
        "Diepvries pizza",
        "Diepvries snacks & frituur",
        "IJs",
        "Diepvries vlees & vis",
        "Diepvries maaltijden",
        "Diepvries brood & gebak",
        "IJsblokjes",
    ),
    "Koffie & thee": (
        "Koffiebonen",
        "Filterkoffie",
        "Koffiecups",
        "Koffiepads",
        "Oploskoffie",
        "IJskoffie",
        "Koffiemelk & creamer",
        "Thee",
        "IJsthee",
        "Cacao & chocolademelk",
        "Koffie- en theebenodigdheden",
    ),
    "Frisdrank, sappen & water": (
        "Cola",
        "Sinas, cassis & limonade",
        "Tonic, ginger ale & bitter lemon",
        "Energiedrank & sportdrank",
        "Water",
        "Vruchtensap & fruitdrank",
        "Groentesap",
        "Limonadesiroop",
        "Drinkpakjes",
        "Trays & multipacks fris",
    ),
    "Bier, wijn & aperitieven": (
        "Bier",
        "Speciaalbier",
        "Alcoholvrij & alcoholarm",
        "Witte wijn",
        "Rode wijn",
        "Rosé",
        "Mousserende wijn & champagne",
        "Mixdranken & seltzers",
        "Aperitief & gedistilleerd",
    ),
    "Drogisterij": (
        "Douche & bad",
        "Deodorant",
        "Haarverzorging",
        "Gezichtsverzorging",
        "Handverzorging & bodylotion",
        "Mondverzorging",
        "Scheren & ontharen",
        "Make-up",
        "Parfum & geuren",
        "Maandverband & tampons",
        "Watten & wattenstaafjes",
        "Zonnebrand",
    ),
    "Gezondheid & sport": (
        "Vitamines & mineralen",
        "Voedingssupplementen",
        "Zelfzorgmiddelen",
        "Pleisters & verband",
        "Sportvoeding & eiwitshakes",
        "Dieetvoeding",
        "Condooms & intimiteit",
        "Zwangerschap & kraamtijd",
    ),
    "Huishouden": (
        "Wasmiddel & wasverzachter",
        "Vaatwas & afwasmiddel",
        "Schoonmaakmiddelen",
        "Toiletpapier",
        "Keukenpapier",
        "Zakdoekjes & tissues",
        "Toiletreiniger & luchtverfrisser",
        "Vuilniszakken & huishoudfolie",
        "Schoonmaakgerei",
        "Batterijen & lampen",
        "Ongediertebestrijding",
    ),
    "Baby & kind": (
        "Luiers & billendoekjes",
        "Flesvoeding",
        "Babyvoeding & hapjes",
        "Peutervoeding",
        "Babyverzorging",
        "Baby- & kindaccessoires",
    ),
    "Huisdier": (
        "Hondenvoer",
        "Kattenvoer",
        "Dierensnacks",
        "Kattenbakvulling",
        "Voer voor knaagdier, vogel & vis",
        "Dierbenodigdheden",
    ),
    "Koken & tafelen": (
        "Pannen & keukengerei",
        "Servies & bestek",
        "Glaswerk",
        "Keukenapparaten",
        "Bewaardozen & lunchtrommels",
    ),
    "Huis, tuin & vrije tijd": (
        "Kaarsen & sfeer",
        "Wonen & slapen",
        "Feestartikelen",
        "Barbecue & buitenleven",
        "Tuin & gereedschap",
        "Kleding & schoenen",
        "Speelgoed & spellen",
        "Boeken & tijdschriften",
        "Kantoorartikelen",
        "Elektronica",
        "Hobby & sportartikelen",
        "Lucifers & aanstekers",
        "Cadeaukaarten",
    ),
    "Bloemen & planten": (
        "Boeketten",
        "Rozen",
        "Kamerplanten",
        "Tuinplanten & bloembollen",
        "Kunstbloemen",
        "Plantverzorging",
    ),
}

# -----------------------------------------------------------------------------
# Een regel uitleg per subgroep, alleen bedoeld voor de AI die de winkelgroepen
# vertaalt. Zonder die uitleg gokt hij bij de randgevallen, en dan landt de ene
# winkel ergens anders dan de andere.
#
# Alleen invullen waar het echt nodig is: bij twee subgroepen die op elkaar
# lijken, en bij groepen die in de ene winkel iets anders betekenen dan in de
# andere. De meeste namen spreken voor zich.
# -----------------------------------------------------------------------------
TOELICHTING: dict[str, str] = {
    # Koffie & thee — de tak waarmee de aanpak beproefd is.
    "Koffiecups": "harde cups en pods: Nespresso, Dolce Gusto, Tassimo. Ook 'koffiepods'.",
    "Koffiepads": "alleen de zachte ronde pads voor een Senseo-apparaat.",
    "Koffiemelk & creamer": "zuivel om ín de koffie te doen, geen koffie.",
    "Thee": "theezakjes en losse thee om te zetten.",
    "IJsthee": "kant-en-klare koude thee in flessen of blikjes, zoals Lipton Ice Tea. "
              "Hoort hier en niet bij de frisdrank.",
    "IJskoffie": "kant-en-klare koude koffie in flesjes of bekers, zoals Starbucks.",
    "Cacao & chocolademelk": "cacaopoeder en chocolademelk, ook de pakken uit de "
                            "koeling. Geen chocoladerepen of chocoladepasta.",
    "Koffie- en theebenodigdheden": "filters, koffiesuiker en siropen. Geen apparaten.",

    # Vers: waar de ene afdeling in de andere overloopt.
    "Verspakketten & groentemixen": "gesneden groente voor één gerecht, met of "
                                    "zonder kruidenmix.",
    "Snoepgroente": "kleine rauwe hapgroente: snoeptomaatjes, mini-komkommers.",
    "Verse soep": "soep uit de koeling. Soep in blik of pak hoort bij de "
                 "houdbare soepen.",
    "Warme snacks (vers)": "kant-en-klare snacks uit de koeling of de warme "
                          "vitrine, niet uit de diepvries.",
    "Gehakt": "los gehakt, gehaktballen en tartaar, ongeacht de diersoort.",
    "Verse worst": "rauwe worst om te bakken. Gerookte of gedroogde worst als "
                  "beleg hoort bij de vleeswaren.",
    "Droge worst": "snack-worstjes voor bij de borrel, zoals cabanossi.",
    "Vissalade & visbeleg": "salades en spreads van vis om op brood te doen.",
    "Haring & zure vis": "haring, rolmops, zure haring en makreel in het zuur.",

    # De plantaardige tak snijdt dwars door de rest heen.
    "Plantaardige zuivel": "sojadrink, amandeldrink, haverdrink en plantaardige "
                          "yoghurt. Geen gewone zuivel.",
    "Vleesvervangers": "vegetarische burgers, schnitzels en stukjes.",

    # Kaas en vleeswaren lijken op elkaar.
    "Kaasplakken": "voorgesneden kaas voor op brood.",
    "Kaasstukken": "kaas aan een stuk, van de versafdeling of voorverpakt.",
    "Borrelkaas": "kaasblokjes en kaas voor op een plank.",
    "Vleeswaren vers gesneden": "van de versafdeling, aan de balie gesneden.",
    "Vleeswaren voorverpakt": "in een pakje uit het schap.",

    # Houdbaar: hier zitten de meeste verwarrende namen.
    "Warme sauzen & maaltijdsauzen": "pastasaus, currysaus en jus: sauzen die "
                                    "warm bij een maaltijd horen.",
    "Ketchup, mayonaise & koude sauzen": "sauzen uit een knijpfles voor bij "
                                        "friet of op brood.",
    "Groente in blik of pot": "houdbare groente en peulvruchten, ook augurken "
                             "en zilveruitjes.",
    "Peulvruchten & bonen (droog)": "gedroogde linzen, kikkererwten en bonen "
                                   "uit een zak.",
    "Maaltijdmixen": "droge mixen en pakketten voor één gerecht, zoals een "
                    "taco-kit of een nasipakket.",
    "Hartig broodbeleg": "smeersels en beleg dat niet zoet is en geen vlees of "
                        "kaas is, zoals sandwichspread.",
    "Chocoladepasta": "smeerbare chocolade, zoals hazelnootpasta.",

    # De diepvries wint van elke andere afdeling.
    "Diepvries snacks & frituur": "frikandellen, kroketten en airfryersnacks uit "
                                 "de diepvries.",
    "IJs": "consumptie-ijs uit de diepvries: ijsjes, schepijs en ijstaart.",
    "IJsblokjes": "ijs om drank mee te koelen, geen consumptie-ijs.",

    # Drank.
    "Alcoholvrij & alcoholarm": "bier en wijn zonder of met weinig alcohol.",
    "Trays & multipacks fris": "hele trays of dozen frisdrank of water in één "
                              "keer, zonder dat de smaak genoemd wordt.",
    "Drinkpakjes": "kleine pakjes met rietje voor in een broodtrommel.",
    "Aperitief & gedistilleerd": "port, sherry, vermout en sterke drank.",

    # Non-food, waar de ketens sterk verschillen.
    "Zelfzorgmiddelen": "vrij verkrijgbare medicijnen: pijnstillers, hoestdrank, "
                       "neusspray.",
    "Schoonmaakgerei": "sponzen, doeken, borstels, dweilen en emmers.",
    "Vuilniszakken & huishoudfolie": "afvalzakken, aluminiumfolie, vershoudfolie "
                                    "en diepvrieszakken.",
    "Keukenapparaten": "apparaten voor in de keuken, zoals een koffiezetapparaat, "
                      "waterkoker of airfryer.",
    "Huis, tuin & vrije tijd": "de wisselende non-food van de folder: kleding, "
                              "gereedschap, elektronica.",
    "Cadeaukaarten": "cadeaubonnen, beltegoed en loten.",
}

# -----------------------------------------------------------------------------
# Trefwoorden: woorden die in een productnaam de subgroep verraden.
#
# Dit is het vangnet voor de twee gevallen waarin de winkelgroep tekortschiet:
# Dirk (die niet fijner indeelt dan "Koffie & cacao") en de voorgelezen
# Vomar-folder (die helemaal geen groep meelevert). Het langste trefwoord dat past
# wint, zodat "koffiemelk" niet als "koffie" wordt gelezen, "theeworst" niet als
# "thee" en "pindakaas" niet als "kaas".
#
# Die lengteregel doet het meeste werk. Waar een kort woord in een langer woord
# zit dat érgens anders hoort, staat dat langere woord er daarom expres bij —
# ook al lijkt het overbodig.
#
# Bewust géén los woord "koffie", "vlees" of "brood": die zeggen alleen iets over
# de afdeling, niet over de precieze plek. Daar is HOOFD_TREFWOORDEN voor.
#
# De lijst hoeft niet compleet te zijn. Voor Albert Heijn, Jumbo en Lidl doet de
# winkelgroep het werk; hier staat wat er in de folders van Dirk en Vomar
# werkelijk langskomt.
# -----------------------------------------------------------------------------
TREFWOORDEN: dict[str, tuple[str, ...]] = {
    # --- Groente & aardappelen ---
    "Aardappelen": ("aardappel", "krieltjes", "kruimige", "vastkokende", "pieper"),
    "Sla & rauwkost": ("ijsbergsla", "kropsla", "veldsla", "rucola", "sla melange",
                       "rauwkost", "little gem", "romaine"),
    "Tomaten, komkommer & paprika": ("tomaten", "komkommer", "paprika", "aubergine",
                                     "courgette", "trostomaat"),
    "Ui, prei & knoflook": ("uien", "prei", "knoflook", "sjalot", "bosui"),
    "Wortel, kool & knolgroente": ("wortelen", "worteltjes", "bospeen", "broccoli",
                                   "bloemkool", "spruitjes", "rode kool", "witte kool",
                                   "spitskool", "koolraap", "knolselderij", "pompoen",
                                   "bieten"),
    "Sperziebonen, asperges & mais": ("sperziebonen", "snijbonen", "haricots verts",
                                      "asperges", "venkel", "verse mais"),
    "Champignons & paddenstoelen": ("champignons", "paddenstoelen", "oesterzwam",
                                    "kastanjechampignon"),
    "Verse kruiden & pepers": ("verse basilicum", "verse peterselie", "verse koriander",
                               "verse gember", "rode peper", "spaanse peper"),
    "Snoepgroente": ("snoeptomaat", "snoepgroente", "mini komkommer", "snacktomaat",
                     "snoeppaprika"),
    "Verspakketten & groentemixen": ("verspakket", "groentemix", "roerbakmix",
                                     "wokgroente", "stamppot", "soepgroente"),
    "Overige verse groente": ("spinazie", "andijvie", "witlof", "boerenkool",
                              "raapstelen", "postelein"),

    # --- Fruit ---
    "Appels & peren": ("appels", "elstar", "jonagold", "granny smith", "handpeer",
                       "conference", "peren"),
    "Bananen": ("bananen", "banaan"),
    "Sinaasappels, mandarijnen & citrusfruit": ("sinaasappel", "mandarijn", "clementine",
                                                "citroenen", "limoen", "grapefruit"),
    "Aardbeien, bessen & frambozen": ("aardbeien", "blauwe bessen", "frambozen",
                                      "bramen", "rode bessen"),
    "Perziken, nectarines & pruimen": ("perziken", "nectarines", "abrikozen", "pruimen",
                                       "kersen"),
    "Druiven & kiwi": ("druiven", "kiwi", "pitloze druiven"),
    "Meloen, ananas & exotisch fruit": ("meloen", "ananas", "mango", "avocado",
                                        "granaatappel", "papaja", "passievrucht"),
    "Vers gesneden fruit & fruitsalade": ("fruitsalade", "gesneden fruit", "fruitmix",
                                          "vers fruit bakje"),
    "Gedroogd fruit": ("gedroogde abrikozen", "rozijnen", "gedroogde dadels", "dadels",
                       "gedroogde vijgen", "cranberries gedroogd"),
    "Verse sappen & smoothies": ("verse jus", "vers geperste", "smoothie", "verse sap"),

    # --- Maaltijden & salades ---
    "Kant-en-klare maaltijden": ("kant en klaar maaltijd", "magnetronmaaltijd",
                                 "verse maaltijd", "maaltijd voor", "ovenschotel maaltijd"),
    "Verse soep": ("verse soep", "soep uit de koeling", "verse tomatensoep"),
    "Maaltijdsalades": ("maaltijdsalade", "salade bowl", "caesar salade"),
    # Zalmsalade hoort bij het visbeleg; hier alleen de salades zonder vis, anders
    # zouden twee even lange trefwoorden om hetzelfde product vechten.
    "Huzarensalade & slaatjes": ("huzarensalade", "slaatje", "eiersalade",
                                 "kip kerrie salade", "selderijsalade"),
    "Verse pizza & pizzabodems": ("verse pizza", "pizzabodem", "pizzadeeg"),
    "Verse pasta & verse pastasaus": ("verse pasta", "verse ravioli", "verse tagliatelle",
                                      "verse pastasaus"),
    "Verse noedels & woksaus": ("verse noedels", "woksaus", "verse mie"),
    "Hartige taart & quiche": ("hartige taart", "quiche"),
    "Belegde broodjes": ("belegd broodje", "belegde broodjes", "broodje gezond"),
    "Pannenkoeken & poffertjes": ("pannenkoek", "poffertjes", "crepes"),
    "Sushi": ("sushi", "maki", "poke bowl"),
    "Warme snacks (vers)": ("saucijzenbroodje", "worstenbroodje", "warme snack"),

    # --- Vlees ---
    "Kip": ("kipfilet", "kippenpoten", "kipdijfilet", "kipreepjes", "hele kip",
            "drumsticks", "kippenvleugels", "kipsate", "kipschnitzel", "kipburger"),
    "Rundvlees": ("biefstuk", "runderlappen", "rosbief rauw", "entrecote", "ribeye",
                  "sucadelappen", "riblappen", "runderbraadstuk", "hamburger rund"),
    "Varkensvlees": ("speklappen", "schnitzel", "varkenshaas", "varkensfilet",
                     "procureur", "spareribs", "karbonade", "shoarma", "bacon"),
    "Gehakt": ("gehakt", "gehaktballen", "tartaar", "slavink", "blinde vink"),
    "Kalkoen": ("kalkoenfilet", "kalkoenschnitzel", "kalkoenreepjes"),
    "Lams-, wild- & gevogeltevlees": ("lamsvlees", "lamskotelet", "lamsrack", "hertenvlees",
                                      "wildzwijn", "eendenborst", "konijn"),
    "Verse worst": ("verse worst", "braadworst", "chipolata", "merguez", "bratwurst"),
    "Ovenschotel, hachee & ragout": ("hachee", "ragout", "ovenschotel"),
    "Gourmet, fondue & barbecuevlees": ("gourmetschotel", "gourmet", "fondue",
                                        "barbecuepakket", "bbq pakket", "grillworst rauw"),
    "Halal vlees": ("halal kip", "halal rund", "halal vlees"),
    "Vleesconserven": ("cornedbeef", "vlees in blik", "knakworst blik", "beenham blik"),

    # --- Vis ---
    "Verse vis": ("zalmfilet", "verse zalm", "kabeljauw", "pangasius", "tilapia",
                  "victoriabaars", "tonijnsteak", "verse vis"),
    "Gerookte vis": ("gerookte zalm", "gerookte makreel", "gerookte forel", "paling"),
    "Gepaneerde vis": ("vissticks", "kibbeling", "lekkerbek", "gepaneerde vis"),
    "Haring & zure vis": ("haring", "rolmops", "maatjes", "zure haring"),
    "Schaal- & schelpdieren": ("garnalen", "mosselen", "scampi", "gamba", "krab",
                               "kreeft", "oesters"),
    "Visconserven": ("tonijn in blik", "sardines", "makreel in blik", "haring in blik"),
    "Vissalade & visbeleg": ("zalmsalade", "krabsalade", "garnalensalade", "vissalade"),

    # --- Vegetarisch & plantaardig ---
    "Vleesvervangers": ("vegetarische burger", "vega burger", "vegetarische schnitzel",
                        "vleesvervanger", "vegetarische balletjes", "quorn",
                        "beyond meat", "vega gehakt"),
    "Visvervangers": ("visvervanger", "vegan garnalen", "vega vis"),
    "Tofu, tempeh & seitan": ("tofu", "tempeh", "seitan"),
    "Plantaardige zuivel": ("sojadrink", "amandeldrink", "haverdrink", "rijstdrink",
                            "kokosdrink", "sojamelk", "amandelmelk", "havermelk",
                            "plantaardige yoghurt", "sojayoghurt", "alpro"),
    "Plantaardige kaas": ("plantaardige kaas", "vegan kaas", "kaasvervanger"),
    "Plantaardige vleeswaren": ("vegetarische vleeswaren", "vega ham", "vegan salami"),
    "Hummus & plantaardige spreads": ("hummus", "falafel", "plantaardige spread"),
    "Vegetarische snacks": ("vegetarische snack", "groentesnack", "vega snack"),

    # --- Vleeswaren ---
    "Vleeswaren vers gesneden": ("vers gesneden vleeswaren", "vleeswaren van het mes"),
    "Vleeswaren voorverpakt": ("vleeswaren", "salami", "cervelaat", "boterhamworst",
                               "bierworst", "gebraden gehakt", "casselerrib",
                               "achterham", "snijworst"),
    "Ham & gekookte vleeswaren": ("beenham", "schouderham", "gekookte ham",
                                  "serranoham", "parmaham", "rauwe ham"),
    "Kip- & kalkoenfilet (beleg)": ("gerookte kipfilet", "kipfilet vleeswaren",
                                    "kalkoenfilet beleg", "gebraden kipfilet"),
    "Rosbief, carpaccio & filet américain": ("rosbief", "carpaccio", "filet americain",
                                             "ossenworst"),
    "Leverworst, paté & smeerbaar vleesbeleg": ("leverworst", "pate", "smeerworst",
                                                "theeworst", "leverpastei", "rillette"),
    "Halal vleeswaren": ("halal vleeswaren", "halal salami"),

    # --- Kaas ---
    "Kaasplakken": ("kaas plakken", "plakken kaas", "kaas gesneden", "jong belegen plakken"),
    "Kaasstukken": ("stuk kaas", "kaas stuk", "goudse kaas", "belegen kaas",
                    "jong belegen", "oude kaas", "komijnekaas", "boerenkaas"),
    "Smeerkaas & roomkaas": ("smeerkaas", "roomkaas", "monchou", "cottage cheese",
                             "philadelphia", "kruidenkaas smeer"),
    "Borrelkaas": ("kaasblokjes", "borrelkaas", "kaas voor de borrel"),
    "Geraspte kaas & kookkaas": ("geraspte kaas", "kaas geraspt", "mozzarella",
                                 "parmezaan", "pizzakaas", "raspkaas"),
    "Buitenlandse kaas": ("brie", "camembert", "feta", "gorgonzola", "manchego",
                          "geitenkaas", "blauwader"),
    "Lactosevrije kaas": ("lactosevrije kaas",),

    # --- Zuivel & eieren ---
    "Melk": ("halfvolle melk", "volle melk", "magere melk", "karnemelk", "melk 1 liter",
             "verse melk", "houdbare melk", "schoolmelk"),
    "Yoghurt & skyr": ("yoghurt", "skyr", "griekse yoghurt", "turkse yoghurt"),
    "Kwark": ("kwark", "magere kwark", "kwarkdessert"),
    "Vla & pap": ("vanillevla", "chocoladevla", "vla ", "griesmeelpudding",
                  "rijstepap", "havermoutpap"),
    "Toetjes & pudding": ("toetje", "pudding", "mousse dessert", "dessert", "flan",
                          "tiramisu"),
    "Drinkyoghurt & ontbijtdrank": ("drinkyoghurt", "yoghurtdrink", "ontbijtdrank",
                                    "yakult", "vifit", "milkshake"),
    "Slagroom, kookroom & crème fraîche": ("slagroom", "kookroom", "creme fraiche",
                                           "zure room", "kokosmelk", "mascarpone"),
    "Boter & margarine": ("roomboter", "margarine", "halvarine", "bakboter",
                          "vloeibaar bakproduct", "becel", "blue band"),
    "Eieren": ("eieren", "scharreleieren", "vrije uitloop eieren"),
    "Lactosevrije zuivel": ("lactosevrije melk", "lactosevrij", "lactosevrije yoghurt"),
    "Zuivel tussendoortjes": ("yoghurt tussendoor", "kwarkje", "danoontje", "monchoutje"),

    # --- Bakkerij ---
    "Brood": ("volkorenbrood", "witbrood", "bruinbrood", "tijgerbrood", "meergranenbrood",
              "casinobrood", "brood heel", "half brood", "spelt brood"),
    "Broodjes & croissants": ("broodjes", "bolletjes", "croissant", "pistolet",
                              "kaiserbroodje", "puntje"),
    "Afbakbrood": ("afbakbrood", "afbakbroodjes", "knoflookbrood", "stokbrood",
                   "ciabatta", "turks brood"),
    "Beschuit, crackers & knäckebröd": ("beschuit", "crackers", "knackebrod", "cracottes",
                                        "wasa", "toastjes"),
    "Taart & gebak": ("appeltaart", "slagroomtaart", "gebakje", "taart", "vlaai",
                      "soesjes", "eclair", "monchoutaart"),
    "Zoete bakkerijsnacks": ("krentenbollen", "rozijnenbrood", "suikerbrood",
                             "bananenbrood", "muffin", "donut", "koffiebroodje",
                             "kaneelbroodje", "oliebollen", "appelflap"),
    "Hartige bakkerijsnacks": ("kaasbroodje", "worstenbroodje hartig", "hartige snack bakkerij"),
    "Bakproducten & bakmixen": ("bakmix", "zelfrijzend bakmeel", "patentbloem", "bloem",
                                "gist", "bakpoeder", "vanillesuiker", "cakemix",
                                "pannenkoekmix", "marsepein", "spijs"),
    "Glutenvrij brood": ("glutenvrij brood", "glutenvrije broodjes"),

    # --- Borrel, chips & noten ---
    "Chips": ("chips", "naturel chips", "paprika chips", "tortilla chips", "nachos",
              "pringles", "lays", "doritos"),
    "Zoutjes": ("zoutjes", "borrelnootjes", "japanse mix", "cocktailnootjes",
                "kaaskoekjes", "grissini", "soepstengels"),
    "Noten & pinda's": ("pinda", "cashewnoten", "amandelen", "walnoten", "hazelnoten",
                        "gemengde noten", "ongezouten noten", "gezouten noten"),
    "Popcorn": ("popcorn", "magnetronpopcorn"),
    # De kaassoufflé staat expres alleen bij de diepvries: hij ligt in beide
    # schappen, maar in de folder komt hij vrijwel altijd uit de vriezer.
    "Borrelhapjes": ("bitterballen", "borrelhapjes", "mini snacks", "borrelbox"),
    "Borrelplank & tapas": ("borrelplank", "tapas", "antipasti", "olijven"),
    "Dips & smeersels": ("dipsaus", "tzatziki", "guacamole", "salsa dip", "kruidenboter",
                         "borrelsaus"),
    "Toast & toastsalade": ("toast", "toastsalade", "broodsalade"),
    "Droge worst": ("cabanossi", "droge worst", "snackworst", "beef jerky"),

    # --- Pasta, rijst & wereldkeuken ---
    "Pasta": ("spaghetti", "penne", "macaroni", "fusilli", "tagliatelle", "lasagnebladen",
              "pasta 500", "farfalle"),
    "Rijst": ("rijst", "basmati", "pandan", "risotto", "zilvervliesrijst"),
    "Noedels & mie": ("mie", "noedels", "bami", "ramen", "glasnoedels"),
    "Couscous, quinoa & bulgur": ("couscous", "quinoa", "bulgur", "gierst"),
    "Peulvruchten & bonen (droog)": ("linzen", "kikkererwten droog", "bruine bonen droog",
                                     "spliterwten"),
    "Aziatische keuken": ("wokolie", "sojasaus", "ketjap", "kroepoek", "sambal",
                          "oosterse", "sushirijst", "nori", "curry pasta"),
    "Italiaanse keuken": ("passata", "pesto", "italiaanse", "polenta", "risottorijst"),
    "Mexicaanse keuken": ("tortilla wraps", "taco", "burrito", "fajita", "jalapeno",
                          "mexicaanse"),
    "Mediterrane & Midden-Oosterse keuken": ("tahin", "harissa", "couscouskruiden",
                                             "griekse", "turkse", "libanese"),
    "Surinaamse & Antilliaanse keuken": ("surinaamse", "antilliaanse", "roti", "masala",
                                         "pom"),
    "Hollandse keuken": ("hutspot", "zuurkool", "erwtensoep", "jus poeder",
                         "stamppotmix"),
    "Maaltijdmixen": ("maaltijdmix", "kruidenmix voor", "nasipakket", "taco kit",
                      "maaltijdpakket", "wokmix pakket"),

    # --- Soepen, sauzen & smaakmakers ---
    "Soep uit blik of pak": ("tomatensoep", "groentesoep", "kippensoep", "soep in blik",
                             "soep pak", "cup a soup", "champignonsoep", "bouillonsoep"),
    "Warme sauzen & maaltijdsauzen": ("pastasaus", "currysaus", "satesaus", "jus",
                                      "stroganoffsaus", "kerriesaus", "bechamel",
                                      "roerbaksaus", "zigeunersaus"),
    "Ketchup, mayonaise & koude sauzen": ("ketchup", "mayonaise", "fritessaus",
                                          "curry saus fles", "mosterd", "barbecuesaus",
                                          "knoflooksaus", "joppiesaus", "cocktailsaus"),
    "Bouillon": ("bouillon", "bouillonblokjes", "runderfond", "kippenfond"),
    "Kruiden & specerijen": ("kruidenmix", "paprikapoeder", "kerriepoeder", "oregano",
                             "italiaanse kruiden", "kaneel", "nootmuskaat", "kurkuma",
                             "knoflookpoeder", "specerijen"),
    "Olie & azijn": ("olijfolie", "zonnebloemolie", "arachideolie", "azijn", "wijnazijn",
                     "balsamico", "bakolie"),
    "Frituurvet": ("frituurvet", "frituurolie"),
    "Groente in blik of pot": ("augurken", "zilveruitjes", "sperziebonen blik",
                               "doperwten", "worteltjes blik", "mais blik", "kidneybonen",
                               "tomatenblokjes", "zuurkool pot", "olijven pot"),
    "Fruit in blik of pot": ("appelmoes", "ananas blik", "perziken blik", "fruit op sap",
                             "abrikozen blik"),
    "Suiker, zout & peper": ("kristalsuiker", "basterdsuiker", "poedersuiker", "zeezout",
                             "keukenzout", "peperkorrels", "zoetjes"),

    # --- Koek, snoep & chocolade ---
    "Koek": ("koekjes", "biscuit", "stroopwafel", "speculaas", "gevulde koek",
             "boterkoek", "kano", "eierkoek", "koek "),
    "Snoep": ("winegums", "zuurtjes", "spekjes", "snoepmix", "haribo", "gummy",
              "lolly", "toffee", "schuimpjes"),
    "Drop": ("drop", "dropjes", "salmiak", "muntdrop"),
    "Chocolade": ("chocoladereep", "melkchocolade", "pure chocolade", "witte chocolade",
                  "bonbons", "chocolade", "tony", "milka", "chocoladeletter",
                  "chocolade eitjes"),
    "Pepermunt & keelpastilles": ("pepermunt", "keelpastilles", "mentos", "king pepermunt",
                                  "hoestbonbon"),
    "Kauwgom": ("kauwgom", "stimorol", "freedent"),
    "Trakteren & uitdeelzakjes": ("uitdeelzakjes", "traktatie", "trakteren",
                                  "kinderfeestje snoep"),

    # --- Ontbijtgranen & broodbeleg ---
    "Ontbijtgranen & muesli": ("muesli", "cruesli", "cornflakes", "ontbijtgranen",
                               "granola", "brinta", "rice krispies"),
    "Havermout": ("havermout", "havervlokken"),
    "Hagelslag & vlokken": ("hagelslag", "vlokken", "chocoladevlokken", "muisjes",
                            "gestampte muisjes"),
    "Pindakaas & notenpasta": ("pindakaas", "notenpasta", "amandelpasta"),
    "Jam, honing & stroop": ("jam", "confiture", "honing", "appelstroop", "marmelade",
                             "hazelnootpasta"),
    "Chocoladepasta": ("chocoladepasta", "chocopasta", "nutella", "duo penotti"),
    "Hartig broodbeleg": ("sandwichspread", "smeersel hartig", "hartig beleg"),
    "Ontbijtkoek": ("ontbijtkoek", "kruidkoek", "peperkoek"),
    "Zaden, pitten & superfoods": ("chiazaad", "lijnzaad", "zonnebloempitten",
                                   "pompoenpitten", "superfood"),

    # --- Tussendoortjes ---
    "Mueslirepen & notenrepen": ("mueslireep", "notenreep", "havermoutreep", "fruitreep"),
    "Proteïnerepen": ("proteinereep", "eiwitreep", "protein bar"),
    "Fruitbiscuit & melkbiscuit": ("fruitbiscuit", "melkbiscuit", "liga", "evergreen"),
    "Rijstwafels & maiswafels": ("rijstwafel", "maiswafel", "linzenwafel"),
    "Knijpfruit & fruitsnacks": ("knijpfruit", "fruitsnack", "appelmoes cup",
                                 "fruitbites"),

    # --- Diepvries ---
    "Diepvries groente": ("diepvries groente", "diepvriesgroente", "spinazie diepvries",
                          "erwten diepvries"),
    "Diepvries fruit": ("diepvries fruit", "bevroren fruit", "diepvries aardbeien"),
    "Diepvries aardappel & friet": ("frites", "friet", "aardappelschijfjes", "rosti",
                                    "aardappelpartjes", "wedges"),
    "Diepvries pizza": ("diepvriespizza", "pizza diepvries", "pizza magnetron"),
    "Diepvries snacks & frituur": ("frikandel", "kroket", "bamischijf", "nasischijf",
                                   "kaassoufflé", "loempia", "airfryersnack",
                                   "gehaktbal snack", "kipnuggets", "berenklauw"),
    "IJs": ("roomijs", "waterijs", "schepijs", "ijstaart", "ijsjes", "magnum",
            "ben en jerry", "cornetto", "raketje"),
    "Diepvries vlees & vis": ("diepvries vlees", "diepvries vis", "vissticks diepvries",
                              "diepvries kip"),
    "Diepvries maaltijden": ("diepvriesmaaltijd", "diepvries maaltijd", "iglo maaltijd"),
    "Diepvries brood & gebak": ("diepvries brood", "bladerdeeg", "diepvries gebak",
                                "croissants diepvries"),
    "IJsblokjes": ("ijsblokjes", "ijsklontjes"),

    # --- Koffie & thee (het beproefde proefstuk; ongewijzigd gelaten) ---
    "Koffiemelk & creamer": ("koffiemelk", "koffieroom", "koffiecreamer", "creamer",
                             "coffee creamer", "opschuimmelk", "barista melk",
                             "koffie melk"),
    "Koffiebonen": ("koffiebonen", "koffie bonen", "espressobonen", "espresso bonen",
                    "bonen koffie", "koffieboon", "hele bonen"),
    "Filterkoffie": ("filterkoffie", "filter koffie", "snelfiltermaling", "gemalen koffie",
                     "koffie gemalen", "filterzakjes koffie"),
    "Koffiecups": ("koffiecups", "koffie cups", "nespresso", "dolce gusto",
                   "koffiecapsules", "koffiepods", "koffie pods", "lungo", "ristretto"),
    "Koffiepads": ("koffiepads", "koffie pads", "senseo", "koffiepad"),
    "Oploskoffie": ("oploskoffie", "oplos koffie", "instant koffie", "koffie instant",
                    "oploscappuccino", "cappuccino poeder", "latte macchiato poeder"),
    "IJskoffie": ("ijskoffie", "ijs koffie", "iced coffee", "cold brew", "frappuccino",
                  "ice cappuccino", "iced cappuccino", "iced latte", "chilled coffee",
                  "koffie klaar om te drinken"),
    "Thee": ("thee", "rooibos", "kruidenthee", "groene thee", "zwarte thee",
             "vruchtenthee", "chai", "earl grey", "kamille",
             # Engelse namen komen los in de schappen voor (Lipton, Pickwick). Ze
             # staan hier alleen met een spatie erin: het kale woord "tea" zit ook
             # in "steak" en zou dan een biefstuk bij de thee zetten.
             "green tea", "black tea", "herbal tea"),
    "IJsthee": ("ijsthee", "ijs thee", "ice tea", "iced tea", "fuze tea"),
    "Cacao & chocolademelk": ("chocolademelk", "chocolade melk", "cacaopoeder",
                              "cacao poeder", "chocomel", "cacao", "warme chocolade",
                              "chocolate drink"),
    "Koffie- en theebenodigdheden": ("koffiefilters", "koffie filters", "theefilters",
                                     "theezakjes leeg", "koffiesiroop", "koffiesiropen",
                                     "koffiesuiker"),

    # --- Frisdrank, sappen & water ---
    "Cola": ("cola", "coca cola", "pepsi"),
    "Sinas, cassis & limonade": ("sinas", "cassis", "fanta", "sprite", "seven up",
                                 "limonade fles", "rivella"),
    "Tonic, ginger ale & bitter lemon": ("tonic", "ginger ale", "bitter lemon",
                                         "gingerbeer"),
    "Energiedrank & sportdrank": ("energydrink", "energy drink", "red bull", "monster energy",
                                  "aa drink", "isostar", "sportdrank"),
    "Water": ("mineraalwater", "bronwater", "spa blauw", "spa rood", "sourcy",
              "water met smaak", "spa reine", "bruisend water", "koolzuurhoudend water"),
    "Vruchtensap & fruitdrank": ("appelsap", "sinaasappelsap", "vruchtensap", "jus d orange",
                                 "multivruchten", "dubbeldrank", "fruitdrank"),
    "Groentesap": ("groentesap", "tomatensap"),
    "Limonadesiroop": ("limonadesiroop", "siroop ranja", "ranja", "diksap"),
    "Drinkpakjes": ("drinkpakjes", "pakjes drinken", "roosvicee pakje"),
    "Trays & multipacks fris": ("tray frisdrank", "multipack fris", "krat frisdrank"),

    # --- Bier, wijn & aperitieven ---
    "Bier": ("pils", "bier krat", "bierkrat", "heineken", "grolsch", "amstel",
             "brand bier", "hertog jan", "bavaria", "jupiler"),
    "Speciaalbier": ("speciaalbier", "witbier", "tripel", "dubbel bier", "ipa",
                     "bok bier", "weizen", "abdijbier"),
    "Alcoholvrij & alcoholarm": ("alcoholvrij", "alcoholarm", "0.0", "radler 0"),
    "Witte wijn": ("witte wijn", "sauvignon blanc", "chardonnay", "pinot grigio",
                   "riesling"),
    "Rode wijn": ("rode wijn", "merlot", "cabernet", "shiraz", "malbec", "rioja",
                  "tempranillo"),
    "Rosé": ("rose wijn", "rosewijn"),
    "Mousserende wijn & champagne": ("prosecco", "champagne", "cava", "mousserend"),
    "Mixdranken & seltzers": ("mixdrank", "seltzer", "breezer", "radler", "gin tonic mix"),
    "Aperitief & gedistilleerd": ("port", "sherry", "vermout", "martini", "likeur",
                                  "jenever", "whisky", "wodka", "rum", "gin"),

    # --- Drogisterij ---
    "Douche & bad": ("douchegel", "badschuim", "zeep", "handzeep", "doucheschuim"),
    "Deodorant": ("deodorant", "deospray", "deoroller", "anti transpirant"),
    "Haarverzorging": ("shampoo", "conditioner", "haarlak", "haargel", "haarverf",
                       "haarmasker"),
    "Gezichtsverzorging": ("gezichtscreme", "dagcreme", "nachtcreme", "reinigingsdoekjes",
                           "gezichtsreiniging", "micellair"),
    "Handverzorging & bodylotion": ("handcreme", "bodylotion", "bodycreme", "voetencreme"),
    "Mondverzorging": ("tandpasta", "tandenborstel", "mondwater", "flosdraad",
                       "tandenstokers"),
    "Scheren & ontharen": ("scheermesjes", "scheerschuim", "scheergel", "ontharings",
                           "epileer"),
    "Make-up": ("mascara", "lippenstift", "foundation", "oogschaduw", "nagellak"),
    "Parfum & geuren": ("eau de toilette", "parfum", "eau de parfum", "geurset"),
    "Maandverband & tampons": ("maandverband", "tampons", "inlegkruisjes",
                               "menstruatie"),
    "Watten & wattenstaafjes": ("wattenschijfjes", "wattenstaafjes", "watten"),
    "Zonnebrand": ("zonnebrand", "zonnemelk", "aftersun", "sunblock"),

    # --- Gezondheid & sport ---
    "Vitamines & mineralen": ("vitamine", "multivitamine", "magnesium tabletten",
                              "ijzertabletten"),
    "Voedingssupplementen": ("supplement", "visolie capsules", "omega 3 capsules",
                             "probiotica capsules"),
    "Zelfzorgmiddelen": ("paracetamol", "ibuprofen", "hoestdrank", "neusspray",
                         "keeltabletten", "maagzuurremmer", "zwitsal zalf"),
    "Pleisters & verband": ("pleisters", "verband", "gaasjes", "wondspray"),
    "Sportvoeding & eiwitshakes": ("eiwitshake", "proteine poeder", "whey", "sportvoeding"),
    "Dieetvoeding": ("dieetvoeding", "maaltijdshake", "afslank"),
    "Condooms & intimiteit": ("condooms", "glijmiddel"),
    "Zwangerschap & kraamtijd": ("zwangerschapstest", "kraampakket", "borstvoeding"),

    # --- Huishouden ---
    "Wasmiddel & wasverzachter": ("wasmiddel", "wasverzachter", "waspoeder", "wascapsules",
                                  "wasparfum", "vlekverwijderaar", "ariel", "robijn",
                                  "omo", "witte reus"),
    "Vaatwas & afwasmiddel": ("afwasmiddel", "vaatwastabletten", "vaatwasmiddel",
                              "glansspoelmiddel", "vaatwaszout", "dreft"),
    "Schoonmaakmiddelen": ("allesreiniger", "schoonmaakmiddel", "glasreiniger",
                           "badkamerreiniger", "keukenreiniger", "ontkalker", "bleek",
                           "schuurmiddel", "ontvetter"),
    "Toiletpapier": ("toiletpapier", "wc papier"),
    "Keukenpapier": ("keukenpapier", "keukenrol"),
    "Zakdoekjes & tissues": ("zakdoekjes", "tissues", "papieren zakdoekjes"),
    "Toiletreiniger & luchtverfrisser": ("toiletblokjes", "toiletreiniger",
                                         "luchtverfrisser", "wc eend", "geurspray",
                                         "geurkaars spray"),
    "Vuilniszakken & huishoudfolie": ("vuilniszakken", "afvalzakken", "aluminiumfolie",
                                      "vershoudfolie", "diepvrieszakken", "bakpapier",
                                      "boterhamzakjes"),
    "Schoonmaakgerei": ("schuursponsjes", "sponzen", "vaatdoekjes", "dweil", "emmer",
                        "stofdoek", "theedoek", "handdoek keuken", "bezem",
                        "stofzuigerzakken", "wasknijpers"),
    "Batterijen & lampen": ("batterijen", "ledlamp", "gloeilamp", "spaarlamp"),
    "Ongediertebestrijding": ("muizenval", "insectenspray", "vliegenvanger",
                              "mierenlokdoos", "muggenstekker"),

    # --- Baby & kind ---
    "Luiers & billendoekjes": ("luiers", "billendoekjes", "luierbroekjes", "pampers",
                               "zwemluiers"),
    "Flesvoeding": ("flesvoeding", "zuigelingenmelk", "opvolgmelk", "nutrilon"),
    "Babyvoeding & hapjes": ("babyvoeding", "babyhapje", "fruithapje", "groentehapje",
                             "olvarit"),
    "Peutervoeding": ("peutermelk", "peutervoeding", "dreumes"),
    "Babyverzorging": ("babyshampoo", "babyzalf", "billenzalf", "babyolie", "babybadje"),
    "Baby- & kindaccessoires": ("fopspeen", "babyfles", "slabbetje", "speenborstel"),

    # --- Huisdier ---
    "Hondenvoer": ("hondenvoer", "hondenbrokken", "natvoer hond", "pedigree", "cesar hond"),
    "Kattenvoer": ("kattenvoer", "kattenbrokken", "whiskas", "felix kat", "sheba"),
    "Dierensnacks": ("hondensnack", "kauwstaaf", "kattensnoepjes", "dentastix"),
    "Kattenbakvulling": ("kattenbakvulling", "kattenbakkorrels"),
    "Voer voor knaagdier, vogel & vis": ("konijnenvoer", "vogelvoer", "hamstervoer",
                                         "vissenvoer", "pindaslinger"),
    "Dierbenodigdheden": ("hondenriem", "kattenspeeltje", "dierenmand", "vlooienband"),

    # --- Koken & tafelen ---
    "Pannen & keukengerei": ("koekenpan", "steelpan", "braadpan", "wokpan", "pannenset",
                             "snijplank", "keukenmes", "garde", "spatel", "vergiet"),
    "Servies & bestek": ("servies", "borden set", "bestek", "mokken", "theepot",
                         "theeglas", "theemuts", "theelepel", "schaal serveer",
                         "koffiekop", "koffiebeker"),
    "Glaswerk": ("glazen set", "wijnglazen", "bierglazen", "drinkglazen", "karaf"),
    "Keukenapparaten": ("koffiezetapparaat", "koffiemachine", "koffiemolen", "waterkoker",
                        "airfryer", "staafmixer", "blender", "tosti ijzer", "keukenmachine"),
    "Bewaardozen & lunchtrommels": ("bewaardozen", "vershouddoos", "lunchtrommel",
                                    "broodtrommel", "drinkbeker kind"),

    # --- Huis, tuin & vrije tijd ---
    "Kaarsen & sfeer": ("kaarsen", "waxinelichtjes", "theelichtjes", "geurkaars",
                        "kandelaar", "lampion"),
    "Wonen & slapen": ("dekbedovertrek", "kussensloop", "hoeslaken", "plaid", "kussen",
                       "handdoeken", "badmat", "gordijn"),
    "Feestartikelen": ("slingers", "ballonnen", "feestartikelen", "versiering",
                       "verjaardagskaars", "servetten feest"),
    "Barbecue & buitenleven": ("barbecue", "houtskool", "aanmaakblokjes", "bbq rooster",
                               "parasol", "tuinstoel", "campingtafel"),
    "Tuin & gereedschap": ("tuingereedschap", "snoeischaar", "gereedschapsset",
                           "schroevendraaier", "boormachine", "tuinslang", "handschoenen tuin"),
    "Kleding & schoenen": ("sokken", "ondergoed", "pyjama", "t shirt", "regenjas",
                           "sportschoenen", "slippers", "sjaal"),
    "Speelgoed & spellen": ("speelgoed", "puzzel", "gezelschapsspel", "lego", "knuffel",
                            "kleurboek"),
    "Boeken & tijdschriften": ("tijdschrift", "boek roman", "puzzelboek", "kookboek"),
    "Kantoorartikelen": ("pennen", "schriften", "printpapier", "plakband", "enveloppen",
                         "wenskaart"),
    "Elektronica": ("koptelefoon", "oplader", "usb kabel", "powerbank", "muis draadloos"),
    "Hobby & sportartikelen": ("yogamat", "halters", "fietsband", "zwembril",
                               "hobbyset", "verf hobby"),
    "Lucifers & aanstekers": ("lucifers", "aanstekers", "aansteker"),
    "Cadeaukaarten": ("cadeaukaart", "cadeaubon", "beltegoed", "staatslot", "kraslot"),

    # --- Bloemen & planten ---
    "Boeketten": ("boeket", "bos bloemen", "bloemen boeket", "veldboeket"),
    "Rozen": ("rozen", "roos bloem"),
    "Kamerplanten": ("kamerplant", "groene plant", "orchidee", "vetplant"),
    "Tuinplanten & bloembollen": ("tuinplant", "bloembollen", "perkplanten", "zaden tuin",
                                  "violen plant"),
    "Kunstbloemen": ("kunstbloemen", "kunstplant"),
    "Plantverzorging": ("plantenvoeding", "potgrond", "bloempot", "gieter"),
}

# Woorden die alleen de afdeling aanwijzen, niet de precieze plek. Nodig wanneer
# er helemaal geen winkelgroep is (de voorgelezen Vomar-folder) en geen enkel
# trefwoord past. Ze worden pas geraadpleegd als de trefwoorden niets opleveren.
HOOFD_TREFWOORDEN: dict[str, tuple[str, ...]] = {
    "Groente & aardappelen": ("groente", "verse groente"),
    "Fruit": ("fruit", "vers fruit"),
    "Maaltijden & salades": ("maaltijd", "salade", "verse maaltijden"),
    "Vlees": ("vlees", "rundvlees", "varkensvlees", "biefstuk", "sate"),
    "Vis": ("vis", "verse vis", "zalm", "tonijn"),
    "Vegetarisch & plantaardig": ("vegetarisch", "vegetarische", "plantaardig",
                                  "plantaardige", "vegan"),
    "Vleeswaren": ("vleeswaren", "broodbeleg vlees", "ham"),
    "Kaas": ("kaas",),
    "Zuivel & eieren": ("zuivel", "melk", "yoghurt", "eieren"),
    "Bakkerij": ("brood", "bakkerij", "broodje", "gebak"),
    "Borrel, chips & noten": ("borrel", "chips", "noten", "zoutjes"),
    "Pasta, rijst & wereldkeuken": ("pasta", "rijst", "wereldkeuken", "mie"),
    "Soepen, sauzen & smaakmakers": ("soep", "saus", "kruiden", "olie", "specerijen"),
    "Koek, snoep & chocolade": ("koek", "snoep", "chocolade", "zoetwaren"),
    "Ontbijtgranen & broodbeleg": ("ontbijt", "broodbeleg", "beleg", "muesli"),
    "Tussendoortjes": ("tussendoortje", "reep", "tussendoor"),
    "Diepvries": ("diepvries", "bevroren", "vriezer"),
    "Koffie & thee": ("koffie", "thee", "espresso", "cappuccino", "cacao", "koffiebonen"),
    "Frisdrank, sappen & water": ("frisdrank", "fris", "sap", "water", "limonade",
                                  "drinken"),
    "Bier, wijn & aperitieven": ("bier", "wijn", "alcohol", "aperitief"),
    "Drogisterij": ("verzorging", "drogisterij", "cosmetica", "lichaamsverzorging"),
    "Gezondheid & sport": ("gezondheid", "vitamines", "supplementen", "sportvoeding"),
    "Huishouden": ("huishouden", "schoonmaak", "wasmiddel", "reiniger"),
    "Baby & kind": ("baby", "peuter", "kind verzorging"),
    "Huisdier": ("huisdier", "hond", "kat", "dierenvoeding"),
    "Koken & tafelen": ("koken", "tafelen", "keukengerei", "servies"),
    "Huis, tuin & vrije tijd": ("wonen", "tuin", "vrije tijd", "non food", "textiel",
                                "gereedschap", "kleding"),
    "Bloemen & planten": ("bloemen", "planten", "boeket"),
}

# Regels uit een folder die helemaal geen product zijn. Ze halen soms wel een
# trefwoord aan ("statiegeld op de kratten bier") en zouden dan als aanbieding
# in een schap belanden.
#
# De lijst is kort gebleven, en dat is met opzet: sinds de indeling het hele
# assortiment dekt, hoeven misleidende woorden hier niet meer geblokkeerd te
# worden. "Theeworst" is gewoon vleeswaren en "theedoek" is schoonmaakgerei — dat
# lossen de trefwoorden zelf op, want het langste woord wint.
UITZONDERINGEN: tuple[str, ...] = (
    "statiegeld", "emballage", "draagtas", "boodschappentas",
    "spaarzegels", "spaaractie", "zegelboekje", "kortingsbon", "actiecode",
)

# De afdeling die van alle andere wint, met de woorden die haar aanwijzen.
#
# Vissticks zijn vis, maar wie ze zoekt loopt naar de vriezer — en zo staat het
# ook in elke winkel. Zegt de productnaam dus dat iets uit de vriezer komt, dan
# gaat dat vóór de afdeling waar het product inhoudelijk bij hoort.
DIEPVRIES = "Diepvries"
VRIEZERWOORDEN: tuple[str, ...] = ("diepvries", "diepgevroren", "bevroren", "vriezer")

# Waar een product landt dat uit de vriezer komt terwijl zijn naam een heel
# andere afdeling aanwijst. "Diepvries spinazie" zegt genoeg voor de groentelade
# van de vriezer; zonder deze vertaling bleef het steken op alleen "Diepvries".
VRIEZERPLEK: dict[str, str] = {
    "Groente & aardappelen": "Diepvries groente",
    "Fruit": "Diepvries fruit",
    "Vlees": "Diepvries vlees & vis",
    "Vis": "Diepvries vlees & vis",
    "Maaltijden & salades": "Diepvries maaltijden",
    "Bakkerij": "Diepvries brood & gebak",
    "Borrel, chips & noten": "Diepvries snacks & frituur",
}


@dataclass(frozen=True)
class Plek:
    """
    Waar een product in onze indeling hangt.

    De subgroep mag leeg zijn: dan weten we wél de hoofdgroep maar niet de
    precieze plek. Dat is eerlijk bij een winkel als Dirk, die zijn koffiebonen
    en zijn cacao in één groep gooit en waarvan de productnaam niets prijsgeeft.
    """

    hoofdgroep: str
    subgroep: str | None = None
    herkomst: str = ""          # 'winkelgroep', 'productnaam' of 'winkelgroep+productnaam'

    @property
    def volledig(self) -> bool:
        return bool(self.subgroep)


def schoon(tekst: str | None) -> str:
    """
    Maakt een naam vergelijkbaar: kleine letters, geen accenten, enkele spaties.

    Jumbo zet bij een deel van zijn groepen "lokaal" ervoor ("lokaal
    Koffiebonen"). Dat voorvoegsel gaat er hier af, zodat die groep op dezelfde
    plek landt als de gewone. Wat het bij Jumbo precies betekent weten we niet,
    maar voor de indeling maakt het geen verschil: het blijven koffiebonen.
    """
    if not tekst:
        return ""
    plat = unicodedata.normalize("NFKD", tekst)
    plat = "".join(teken for teken in plat if not unicodedata.combining(teken))
    plat = plat.lower().replace("&", " en ")
    plat = re.sub(r"[^a-z0-9]+", " ", plat).strip()
    plat = re.sub(r"^lokaal\s+", "", plat)
    return re.sub(r"\s+", " ", plat)


def _op_lengte(woordenboek: dict[str, tuple[str, ...]]) -> tuple[tuple[str, str], ...]:
    """
    Schoont de trefwoorden één keer op en zet ze op lengte, langste eerst.

    Dit gebeurde eerder bij élk product opnieuw. Met één tak viel dat niet op,
    maar met ruim tweeduizend trefwoorden en tienduizenden aanbiedingen zou het
    indelen daardoor minutenlang duren. Nu is het één keer werk bij het opstarten
    en is het zoeken zelf niets meer dan tekst vergelijken.

    Langste eerst betekent bovendien dat de eerste treffer meteen de goede is:
    "koffiemelk" wordt gevonden vóór "koffie".
    """
    paren: list[tuple[str, str]] = []
    for groep, woorden in woordenboek.items():
        for woord in woorden:
            plat = schoon(woord)
            if plat:
                paren.append((plat, groep))
    paren.sort(key=lambda paar: len(paar[0]), reverse=True)
    return tuple(paren)


# Bij welke hoofdgroep hoort elke subgroep. Eén keer opgezocht, omdat elke
# aanbieding er langs komt en de indeling inmiddels ruim 280 subgroepen telt.
# Dat elke subgroepnaam maar één keer voorkomt is hier de voorwaarde: zou hij
# onder twee afdelingen hangen, dan won stilzwijgend de laatste.
_HOOFDGROEP_BIJ_SUB: dict[str, str] = {
    sub: hoofd for hoofd, subs in INDELING.items() for sub in subs
}

_PLATTE_TREFWOORDEN = _op_lengte(TREFWOORDEN)
_PLATTE_HOOFDWOORDEN = _op_lengte(HOOFD_TREFWOORDEN)
_PLATTE_UITZONDERINGEN = tuple(
    plat for plat in (schoon(woord) for woord in UITZONDERINGEN) if plat
)
_PLATTE_VRIEZERWOORDEN = tuple(schoon(woord) for woord in VRIEZERWOORDEN)

# Alleen de trefwoorden van de diepvriesafdeling, om een product dat uit de
# vriezer blijkt te komen alsnog een fijne plek te kunnen geven.
_PLATTE_DIEPVRIES = tuple(
    (woord, groep) for woord, groep in _PLATTE_TREFWOORDEN
    if _HOOFDGROEP_BIJ_SUB[groep] == DIEPVRIES
)


def hoofdgroepen() -> tuple[str, ...]:
    """Alle hoofdgroepen van onze indeling, op volgorde."""
    return tuple(INDELING)


def subgroepen(hoofdgroep: str) -> tuple[str, ...]:
    """De subgroepen onder één hoofdgroep; leeg als die hoofdgroep niet bestaat."""
    return INDELING.get(hoofdgroep, ())


def hoofdgroep_van(subgroep: str | None) -> str | None:
    """Bij welke hoofdgroep hoort deze subgroep? Niets als hij niet bestaat."""
    if not subgroep:
        return None
    return _HOOFDGROEP_BIJ_SUB.get(subgroep)


def bestaat(hoofdgroep: str | None, subgroep: str | None = None) -> bool:
    """Is dit een combinatie die in onze indeling voorkomt?"""
    if not hoofdgroep or hoofdgroep not in INDELING:
        return False
    return not subgroep or subgroep in INDELING[hoofdgroep]


def _eerste_treffer(
    naam: str, tabel: tuple[tuple[str, str], ...]
) -> tuple[str | None, str]:
    """
    Het langste trefwoord dat in de naam voorkomt, met de groep waar het bij hoort.

    De tabel staat op lengte, dus de eerste die past is meteen de langste. Het
    langste wint omdat de korte woorden in de lange zitten: "koffiemelk" bevat
    "koffie", en zonder deze regel zou een pak koffiemelk bij de bonen belanden.
    """
    for woord, groep in tabel:
        if woord in naam:
            return groep, woord
    return None, ""


def _uit_de_vriezer(naam: str, gevonden_woord: str) -> bool:
    """
    Zegt de naam dat dit product uit de vriezer komt?

    Het vriezerwoord telt alleen als het losstaat van het trefwoord dat al
    gevonden is. Anders zou "diepvrieszakken" — een rol zakken uit het
    huishoudschap — als diepvriesproduct worden gelezen, en die liggen echt niet
    in de vriezer.
    """
    return any(
        woord in naam and woord not in gevonden_woord
        for woord in _PLATTE_VRIEZERWOORDEN
    )


def uit_naam(product_naam: str | None) -> Plek | None:
    """
    Leest uit de productnaam af waar het product hoort. Het vangnet.

    Dit is minder zeker dan de winkelindeling en wordt daarom alleen gebruikt
    waar die indeling tekortschiet. Bij twijfel geeft deze functie liever niets
    terug dan een gok: een product op de verkeerde plek is vervelender dan een
    product in de restbak.
    """
    naam = schoon(product_naam)
    if not naam:
        return None

    if any(woord in naam for woord in _PLATTE_UITZONDERINGEN):
        return None

    subgroep, woord = _eerste_treffer(naam, _PLATTE_TREFWOORDEN)
    if subgroep and not (
        _HOOFDGROEP_BIJ_SUB[subgroep] != DIEPVRIES and _uit_de_vriezer(naam, woord)
    ):
        return Plek(_HOOFDGROEP_BIJ_SUB[subgroep], subgroep, herkomst="productnaam")

    # De naam noemt de vriezer, maar het gevonden trefwoord wijst een ander schap
    # aan. Dan wint de vriezer: vissticks liggen bij de diepvries, niet bij de vis.
    # Wat het product ís blijft daarbij overeind — spinazie wordt diepvriesgroente.
    if _uit_de_vriezer(naam, woord):
        diepvries_sub, _ = _eerste_treffer(naam, _PLATTE_DIEPVRIES)
        if not diepvries_sub and subgroep:
            diepvries_sub = VRIEZERPLEK.get(_HOOFDGROEP_BIJ_SUB[subgroep])
        return Plek(DIEPVRIES, diepvries_sub, herkomst="productnaam")

    hoofdgroep, _ = _eerste_treffer(naam, _PLATTE_HOOFDWOORDEN)
    if hoofdgroep:
        return Plek(hoofdgroep, None, herkomst="productnaam")

    return None


def plaats(
    product_naam: str | None,
    uit_winkelgroep: Plek | None = None,
    winkel_heeft_groep: bool = False,
    gemengd: bool = False,
) -> Plek | None:
    """
    De eindregel: waar hangt dit product?

    De winkelgroep is leidend voor de hoofdgroep. Een winkel zet zijn eigen
    product in zijn eigen indeling, dus dat de bonen bij de koffie liggen klopt
    vrijwel altijd — ook bij een grove indeling als die van Dirk.

    Alleen de fijne plek ontbreekt daar. Die mag de productnaam aanvullen, maar
    uitsluitend met een subgroep die ónder de al vastgestelde hoofdgroep hangt.
    Zo kan één verdwaald woord een product nooit naar een heel andere afdeling
    schieten: "Chocomel chocolademelk" in Dirks koffiegroep landt op
    "Cacao & chocolademelk", maar een pak hagelslag dat daar per ongeluk in zit
    blijft gewoon bij de hoofdgroep staan.

    Belangrijk is het verschil tussen drie soorten winkelgroep.

    1. De winkel levert hélemaal geen groep — de voorgelezen Vomar-folder. Dan is
       de productnaam het enige houvast en beslist die alles.
    2. De winkel levert een groep die niet onder onze indeling valt. Dan heeft de
       winkel al gezegd wat voor product het is en gaan we daar niet overheen.
       Anders belandt "Nivea Men Espresso deodorant" bij de koffie.
    3. De groep is gemengd: er ligt van alles door elkaar, waarvan een deel van
       ons is. "IJskoffie en milkshakes" is zo'n groep. Dan telt een product pas
       mee als de naam zelf laat zien dat het erbij hoort — het voordeel van de
       twijfel gaat hier naar de productnaam, niet naar de groep.

    Levert niets een plek op, dan komt het product in de restbak — zichtbaar,
    zodat we kunnen bijsturen.
    """
    if uit_winkelgroep is None:
        return None if winkel_heeft_groep else uit_naam(product_naam)

    uit_de_naam = uit_naam(product_naam)
    past_eronder = bool(
        uit_de_naam
        and uit_de_naam.subgroep
        and hoofdgroep_van(uit_de_naam.subgroep) == uit_winkelgroep.hoofdgroep
    )

    if gemengd:
        if not past_eronder:
            return None
        return Plek(
            uit_winkelgroep.hoofdgroep,
            uit_de_naam.subgroep,          # type: ignore[union-attr]
            herkomst="gemengde winkelgroep+productnaam",
        )

    if uit_winkelgroep.volledig:
        return uit_winkelgroep

    if past_eronder:
        return Plek(
            uit_winkelgroep.hoofdgroep,
            uit_de_naam.subgroep,          # type: ignore[union-attr]
            herkomst="winkelgroep+productnaam",
        )

    return uit_winkelgroep
