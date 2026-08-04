"""
===============================================================================
 Dealbot — controle op de eigen productindeling

 Versie      : 1.0
 Reden       : De eigen indeling van twee lagen bepaalt straks waar élk product
               terechtkomt. Gaat daar iets mis, dan verdwijnt een aanbieding uit
               het zicht of duikt hij op bij de verkeerde boodschap. Deze
               controles leggen de regels vast die daarbij horen — met name de
               valstrikken: "theeworst" is worst en "koffiemelk" is geen koffie.
 Datum       : 03-08-2026 22:10

 Uitvoeren met: python scripts/tests/test_indeling.py
===============================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.indeling import (  # noqa: E402
    HOOFD_TREFWOORDEN,
    INDELING,
    TOELICHTING,
    TREFWOORDEN,
    VRIEZERPLEK,
    Plek,
    bestaat,
    hoofdgroep_van,
    plaats,
    schoon,
    subgroepen,
    uit_naam,
)

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


KOFFIE = "Koffie & thee"


# --- De indeling zelf is heel ----------------------------------------------
controleer("hoofdgroep bestaat", bestaat(KOFFIE), True)
controleer("subgroep bestaat", bestaat(KOFFIE, "Koffiebonen"), True)
controleer("verzonnen subgroep", bestaat(KOFFIE, "Rookworst"), False)
controleer("verzonnen hoofdgroep", bestaat("Gereedschap"), False)
controleer("hoofdgroep bij subgroep", hoofdgroep_van("Thee"), KOFFIE)
controleer("hoofdgroep bij onzin", hoofdgroep_van("Rookworst"), None)
controleer("subgroepen komen terug", len(subgroepen(KOFFIE)), len(INDELING[KOFFIE]))

for hoofd, subs in INDELING.items():
    controleer(f"geen dubbele subgroepen in {hoofd}", len(set(subs)), len(subs))
    controleer(f"{hoofd} heeft subgroepen", bool(subs), True)

# Elke subgroepnaam mag in de héle indeling maar één keer voorkomen: de naam is
# de sleutel waarmee de hoofdgroep wordt opgezocht. Stond "Verspakketten" onder
# twee afdelingen, dan was niet meer te zeggen welke van de twee bedoeld werd.
alle_subgroepen = [sub for subs in INDELING.values() for sub in subs]
controleer(
    "elke subgroepnaam komt maar één keer voor",
    sorted(naam for naam in set(alle_subgroepen)
           if alle_subgroepen.count(naam) > 1),
    [],
)

# De trefwoordenlijsten wijzen naar groepen; wijst er eentje naar een groep die
# niet bestaat, dan verdwijnt dat product stilletjes in de restbak.
controleer(
    "trefwoorden horen bij een bestaande subgroep",
    sorted(naam for naam in TREFWOORDEN if naam not in alle_subgroepen),
    [],
)
controleer(
    "elke afdeling heeft eigen trefwoorden",
    sorted(naam for naam in INDELING if naam not in HOOFD_TREFWOORDEN),
    [],
)
controleer(
    "toelichting hoort bij een bestaande groep",
    sorted(naam for naam in TOELICHTING
           if naam not in alle_subgroepen and naam not in INDELING),
    [],
)
controleer(
    "elke vriezerplek bestaat in de diepvries",
    sorted(sub for sub in VRIEZERPLEK.values() if sub not in INDELING["Diepvries"]),
    [],
)

# Twee even lange trefwoorden voor verschillende groepen betekent dat het toeval
# beslist welk schap wint. Dat mag niet: dan is de uitkomst niet te voorspellen.
_gezien: dict[str, str] = {}
_botsingen: list[str] = []
for _groep, _woorden in TREFWOORDEN.items():
    for _woord in _woorden:
        _plat = schoon(_woord)
        if _plat in _gezien and _gezien[_plat] != _groep:
            _botsingen.append(f"{_woord} ({_gezien[_plat]} én {_groep})")
        _gezien[_plat] = _groep
controleer("geen trefwoord bij twee groepen tegelijk", sorted(_botsingen), [])


# --- Namen opschonen --------------------------------------------------------
controleer("hoofdletters weg", schoon("Koffiebonen"), "koffiebonen")
controleer("accenten weg", schoon("Café crème"), "cafe creme")
controleer("ampersand wordt en", schoon("Koffie & cacao"), "koffie en cacao")
controleer("voorvoegsel lokaal weg", schoon("lokaal Koffiebonen"), "koffiebonen")
controleer("leeg blijft leeg", schoon(None), "")


# --- Het vangnet: aflezen uit de productnaam --------------------------------
controleer(
    "bonen uit de naam",
    uit_naam("Douwe Egberts Aroma Rood koffiebonen 500 g"),
    Plek(KOFFIE, "Koffiebonen", "productnaam"),
)
controleer(
    "koffiemelk wint van koffie",
    uit_naam("Friesche Vlag koffiemelk halfvol 930 ml"),
    Plek(KOFFIE, "Koffiemelk & creamer", "productnaam"),
)
controleer(
    "senseo is een pad",
    uit_naam("Senseo Classic 36 pads"),
    Plek(KOFFIE, "Koffiepads", "productnaam"),
)
controleer(
    "nespresso is een cup",
    uit_naam("Nespresso Lungo capsules 10 stuks"),
    Plek(KOFFIE, "Koffiecups", "productnaam"),
)
controleer(
    "chocomel is cacao",
    uit_naam("Chocomel vol 1 liter"),
    Plek(KOFFIE, "Cacao & chocolademelk", "productnaam"),
)
controleer(
    "los woord koffie geeft alleen de hoofdgroep",
    uit_naam("Perla huismerk koffie 250 g"),
    Plek(KOFFIE, None, "productnaam"),
)

# De valstrikken. Toen de indeling alleen uit koffie en thee bestond, hoorde hier
# níets uit te komen. Nu de hele winkel erin staat is het scherper te controleren:
# deze producten horen niet bij de koffie, maar wél op hun eigen plek.
controleer(
    "theeworst is smeerbaar vleesbeleg",
    uit_naam("Unox theeworst 250 g"),
    Plek("Vleeswaren", "Leverworst, paté & smeerbaar vleesbeleg", "productnaam"),
)
controleer(
    "theedoek is schoonmaakgerei",
    uit_naam("Blokker theedoek katoen"),
    Plek("Huishouden", "Schoonmaakgerei", "productnaam"),
)
controleer(
    "koffiezetapparaat is een keukenapparaat",
    uit_naam("Philips koffiezetapparaat"),
    Plek("Koken & tafelen", "Keukenapparaten", "productnaam"),
)
controleer(
    "hagelslag is broodbeleg",
    uit_naam("De Ruijter hagelslag puur 400 g"),
    Plek("Ontbijtgranen & broodbeleg", "Hagelslag & vlokken", "productnaam"),
)
controleer(
    "chocoladereep is snoep, geen chocolademelk",
    uit_naam("Tony Chocolonely melkchocolade reep 180 g"),
    Plek("Koek, snoep & chocolade", "Chocolade", "productnaam"),
)
controleer(
    "pindakaas is geen kaas",
    uit_naam("Calvé pindakaas 650 g"),
    Plek("Ontbijtgranen & broodbeleg", "Pindakaas & notenpasta", "productnaam"),
)
controleer(
    "wascapsules zijn geen koffiecups",
    uit_naam("Ariel wasmiddel capsules 38 stuks"),
    Plek("Huishouden", "Wasmiddel & wasverzachter", "productnaam"),
)
controleer("lege naam", uit_naam(""), None)

# Folderregels die helemaal geen product zijn horen in de restbak te blijven.
controleer("statiegeld is geen boodschap", uit_naam("Statiegeld emballage krat"), None)
controleer("een spaaractie is geen boodschap", uit_naam("Spaarzegels sparen voor"), None)


# --- De diepvries wint van elke andere afdeling -----------------------------
controleer(
    "vissticks liggen in de vriezer, niet bij de vis",
    uit_naam("Iglo vissticks 15 stuks diepvries"),
    Plek("Diepvries", "Diepvries vlees & vis", "productnaam"),
)
controleer(
    "diepvriesgroente blijft groente, maar dan uit de vriezer",
    uit_naam("Diepvries spinazie 450 g"),
    Plek("Diepvries", "Diepvries groente", "productnaam"),
)
controleer(
    "diepvrieszakken liggen niet in de vriezer",
    uit_naam("Diepvrieszakken 1 liter 40 stuks"),
    Plek("Huishouden", "Vuilniszakken & huishoudfolie", "productnaam"),
)


# --- De eindregel: winkelgroep eerst, productnaam als aanvulling ------------
fijn = Plek(KOFFIE, "Koffiebonen", "winkelgroep")
grof = Plek(KOFFIE, None, "winkelgroep")

controleer(
    "een fijne winkelgroep is genoeg",
    plaats("Douwe Egberts snelfiltermaling 500 g", fijn),
    fijn,
)
controleer(
    "grove winkelgroep, naam vult aan (Dirk)",
    plaats("Douwe Egberts koffiebonen 500 g", grof),
    Plek(KOFFIE, "Koffiebonen", "winkelgroep+productnaam"),
)
controleer(
    "grove winkelgroep, naam zegt niets: hoofdgroep blijft staan",
    plaats("Perla mild 250 g", grof),
    grof,
)
controleer(
    "zonder winkelgroep beslist de naam (Vomar-folder)",
    plaats("Lipton green tea 20 zakjes", None),
    Plek(KOFFIE, "Thee", "productnaam"),
)
controleer(
    "zonder winkelgroep beslist de naam ook voor de kaas",
    plaats("Goudse kaas jong belegen stuk", None),
    Plek("Kaas", "Kaasstukken", "productnaam"),
)
controleer(
    "zonder winkelgroep en zonder aanwijzing: niets",
    plaats("3 halen 2 betalen deze week", None),
    None,
)

# Het verschil dat er echt toe doet: de winkel heeft wél een groep, maar die
# valt buiten onze indeling. Dan heeft de winkel al gezegd wat het is en gaan we
# daar niet met een trefwoord overheen — anders belandt deodorant bij de koffie.
controleer(
    "winkel zegt deodorant, dus geen koffie",
    plaats("Nivea Men Deep Espresso deodorant 150 ml", None, winkel_heeft_groep=True),
    None,
)
controleer(
    "winkel zegt gebak, dus geen koffie",
    plaats("AH Brownie espresso", None, winkel_heeft_groep=True),
    None,
)
controleer(
    "ijsthee is geen theezakje",
    plaats("Lipton Ice Tea Green 1,5 L", None),
    Plek(KOFFIE, "IJsthee", "productnaam"),
)
controleer(
    "ijskoffie blijft ijskoffie",
    plaats("Starbucks Caffe Latte ijskoffie 220 ml", None),
    Plek(KOFFIE, "IJskoffie", "productnaam"),
)

# Een gemengde winkelgroep ("IJskoffie en milkshakes"): het product moet zichzelf
# bewijzen met zijn naam, anders telt het niet mee.
gemengde_groep = Plek(KOFFIE, None, "winkelgroep")
controleer(
    "gemengde groep, naam bewijst het: telt mee",
    plaats("Starbucks Caffe Latte ijskoffie 220 ml", gemengde_groep, True, gemengd=True),
    Plek(KOFFIE, "IJskoffie", "gemengde winkelgroep+productnaam"),
)
controleer(
    "gemengde groep, naam bewijst niets: telt niet mee",
    plaats("Optimel milkshake aardbei 250 ml", gemengde_groep, True, gemengd=True),
    None,
)

# Een verdwaald product in een grove winkelgroep mag niet naar een andere tak
# schieten: de subgroep uit de naam moet ónder de hoofdgroep van de winkel
# hangen. Zegt de winkel "Kaas", dan blijft het bij de kaas staan, hoe hard het
# woord koffiebonen ook roept.
andere_afdeling = Plek("Kaas", None, "winkelgroep")
controleer(
    "subgroep van een andere hoofdgroep telt niet mee",
    plaats("Douwe Egberts koffiebonen 500 g", andere_afdeling),
    andere_afdeling,
)
controleer(
    "binnen de eigen afdeling vult de naam wél aan",
    plaats("Goudse belegen kaas stuk 500 g", andere_afdeling),
    Plek("Kaas", "Kaasstukken", "winkelgroep+productnaam"),
)


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de eigen indeling geslaagd.")
