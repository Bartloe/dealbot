"""
===============================================================================
 Dealbot — controle op de eigenschapgroep

 Versie      : 1.0
 Reden       : Bijna 2500 producten stonden nergens omdat een grove winkelgroep
               als "Soepen" pas meetelde wanneer de productnaam zelf bewees waar
               het hoorde. Dat is omgedraaid: zo'n product valt terug op de
               afdeling van de groep.

               Dat terugvallen mag alleen niet altijd, en juist die grens staat
               hier vast. "Glutenvrij" noemt geen afdeling — die producten liggen
               door de hele winkel — dus daar zou terugvallen de hele groep op
               één hoop gooien. Zulke groepen komen zonder afdeling binnen en
               moeten dat ook blijven, ook als de AI er tóch een noemt.
 Datum       : 06-08-2026 01:40

 Uitvoeren met: python scripts/tests/test_eigenschapgroep.py
===============================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.groepvertaler import _lees_antwoord  # noqa: E402
from dealbot.kenmerken import Woordenlijst  # noqa: E402
from indeel import Boekjeregel, _plek_van  # noqa: E402

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


def lees(*antwoorden: dict):
    """Laat de vertaler één AI-antwoord verwerken en geeft de koppelingen terug."""
    gevraagd = {a["groepsnaam"].lower(): a["groepsnaam"] for a in antwoorden}
    koppelingen, afgekeurd = _lees_antwoord(
        {"koppelingen": list(antwoorden)}, 1, gevraagd, Woordenlijst()
    )
    return koppelingen, afgekeurd


# --- Wat de AI terugstuurt --------------------------------------------------
# Een gewone grove groep: de afdeling telt, meer valt er niet over te zeggen.
koppelingen, _ = lees({
    "groepsnaam": "Soepen", "hoofdgroep": "Soepen, sauzen & smaakmakers",
    "subgroep": "", "kenmerk": "", "eigenschapgroep": False,
})
controleer("grove groep houdt zijn afdeling",
           koppelingen[0].hoofdgroep, "Soepen, sauzen & smaakmakers")
controleer("en is geen eigenschapgroep", koppelingen[0].eigenschapgroep, False)

# Een eigenschapgroep hoort zonder afdeling binnen te komen.
koppelingen, _ = lees({
    "groepsnaam": "Glutenvrij", "hoofdgroep": "", "subgroep": "",
    "kenmerk": "", "eigenschapgroep": True,
})
controleer("eigenschapgroep komt binnen", koppelingen[0].eigenschapgroep, True)
controleer("zonder afdeling", koppelingen[0].hoofdgroep, None)

# En blijft zonder afdeling, ook als de AI er tóch eentje noemt. Anders belandt
# alles wat "Glutenvrij" heet alsnog bij de bakkerij.
koppelingen, _ = lees({
    "groepsnaam": "Glutenvrij", "hoofdgroep": "Bakkerij", "subgroep": "Brood",
    "kenmerk": "glutenvrij", "eigenschapgroep": True,
})
controleer("een opgedrongen afdeling valt weg", koppelingen[0].hoofdgroep, None)
controleer("de lade ook", koppelingen[0].subgroep, None)
controleer("en het kenmerk ook", koppelingen[0].kenmerk, None)

# "Hoort nergens bij ons" is iets anders dan een eigenschapgroep: daar tellen de
# producten helemaal niet mee. Beide hebben een lege afdeling, dus het vlaggetje
# is het enige verschil.
koppelingen, _ = lees({
    "groepsnaam": "Statiegeld", "hoofdgroep": "", "subgroep": "",
    "kenmerk": "", "eigenschapgroep": False,
})
controleer("afgevallen groep", koppelingen[0].hoofdgroep, None)
controleer("en is geen eigenschapgroep", koppelingen[0].eigenschapgroep, False)

# Een verzonnen afdeling wordt nog steeds geweigerd.
koppelingen, afgekeurd = lees({
    "groepsnaam": "Soepen", "hoofdgroep": "Warme maaltijden",
    "subgroep": "", "kenmerk": "", "eigenschapgroep": False,
})
controleer("verzonnen afdeling telt niet", koppelingen, [])
controleer("en wordt geteld als afgekeurd", afgekeurd, 1)


# --- Wat het indelen ermee doet ---------------------------------------------
def plek(naam: str, groep: str, regel: Boekjeregel | None):
    boekje = {(1, groep.lower()): regel} if regel else {}
    return _plek_van({"winkel_id": 1, "product_naam": naam, "productgroep": groep},
                     boekje)


# De grove groep: de afdeling is het vangnet. Dit is het geval dat bijna 2500
# producten kostte.
soepen = Boekjeregel("Soepen, sauzen & smaakmakers", None, False, None)
gevonden = plek("Knorr Good noodles kip", "Soepen", soepen)
controleer("naam zegt niets, afdeling blijft staan",
           gevonden.hoofdgroep, "Soepen, sauzen & smaakmakers")
controleer("zonder lade", gevonden.subgroep, None)

# De eigenschapgroep: geen afdeling om op terug te vallen, de naam beslist vrij.
glutenvrij = Boekjeregel(None, None, True, None)
gevonden = plek("Schar glutenvrij meergranenbrood", "Glutenvrij", glutenvrij)
controleer("eigenschapgroep, de naam wijst de afdeling aan",
           gevonden.hoofdgroep, "Bakkerij")

gevonden = plek("Voordeel van de week", "Glutenvrij", glutenvrij)
controleer("eigenschapgroep zonder aanwijzing: restbak", gevonden, None)

# Een groep die niet in het boekje staat blijft buiten de indeling: de winkel
# heeft al gezegd wat het is, dus een trefwoord mag daar niet overheen.
gevonden = plek("Nivea Men Deep Espresso deodorant", "Deodorant", None)
controleer("groep buiten onze indeling: geen plek", gevonden, None)


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de eigenschapgroep geslaagd.")
