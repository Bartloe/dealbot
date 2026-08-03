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
    INDELING,
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

# De valstrikken: hier hoort níets uit te komen.
controleer("theeworst is worst", uit_naam("Unox theeworst 250 g"), None)
controleer("theedoek is een doek", uit_naam("Blokker theedoek katoen"), None)
controleer("koffiezetapparaat is geen koffie", uit_naam("Philips koffiezetapparaat"), None)
controleer("hagelslag hoort hier niet", uit_naam("De Ruijter hagelslag puur 400 g"), None)
controleer("lege naam", uit_naam(""), None)


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
    "zonder winkelgroep en zonder aanwijzing: niets",
    plaats("Goudse kaas jong belegen", None),
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
# schieten. Er is nu maar één hoofdgroep, dus dit is vooral een afspraak voor
# later: de subgroep uit de naam moet ónder de hoofdgroep van de winkel hangen.
verzonnen = Plek("Zuivel", None, "winkelgroep")
controleer(
    "subgroep van een andere hoofdgroep telt niet mee",
    plaats("Douwe Egberts koffiebonen 500 g", verzonnen),
    verzonnen,
)


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de eigen indeling geslaagd.")
