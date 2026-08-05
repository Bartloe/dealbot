"""
===============================================================================
 Dealbot — controle op de kenmerken

 Versie      : 1.0
 Reden       : Het kenmerk is de derde laag onder onze indeling: "vochtig"
               binnen de lade Toiletpapier. Het wordt niet met de hand
               onderhouden maar afgeleid uit de groepsnamen van de winkels, en
               juist daarom moet het strak dichtgetimmerd zijn. Gaat het mis,
               dan krijgt een lade drie knopjes voor hetzelfde ding, of erger:
               een knopje dat producten toont die er niet in horen.

               Deze controles leggen de regels vast. Met nadruk op de randen:
               een leeg antwoord, een kenmerk dat de ladenaam herhaalt, een
               woord dat halverwege een ander woord staat, en twee schrijfwijzen
               van hetzelfde.
 Datum       : 05-08-2026 16:25

 Uitvoeren met: python scripts/tests/test_kenmerken.py
===============================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot.kenmerken import (  # noqa: E402
    MAXIMUM_WOORDEN,
    Woordenlijst,
    opschonen,
    stam,
    tel_per_lade,
)

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


HUIS = "Huishouden"
PAPIER = "Toiletpapier"
KOFFIE = "Koffie & thee"
BONEN = "Koffiebonen"


# --- Opschonen: wat is een bruikbaar kenmerk? -------------------------------
controleer("gewoon woord", opschonen("Vochtig", HUIS, PAPIER), "vochtig")
controleer("hoofdletters en spaties", opschonen("  VOCHTIG ", HUIS, PAPIER), "vochtig")
controleer("accenten eraf", opschonen("crème", HUIS, PAPIER), "creme")

# De ladenaam herhalen voegt niets toe: die staat al boven het knopje. Ook niet
# als de winkel hem anders vervoegt of er een streepje in zet.
controleer("ladenaam eraf", opschonen("Toiletpapier Vochtig", HUIS, PAPIER), "vochtig")
controleer("met streepje", opschonen("Toiletpapier - vochtig", HUIS, PAPIER), "vochtig")
controleer("andere volgorde", opschonen("vochtig toiletpapier", HUIS, PAPIER), "vochtig")
controleer("afdelingsnaam telt ook", opschonen("huishouden vochtig", HUIS, PAPIER),
           "vochtig")
controleer("alleen de ladenaam", opschonen("Toiletpapier", HUIS, PAPIER), None)

# Woorden die niets verbijzonderen. "Overige koffie" is geen soort koffie.
controleer("overig is geen kenmerk", opschonen("overig", KOFFIE, BONEN), None)
controleer("diversen is geen kenmerk", opschonen("Diversen", KOFFIE, BONEN), None)
controleer("koppelwoorden eruit", opschonen("van het", KOFFIE, BONEN), None)

# Grenzen: leeg, te lang, en getallen.
controleer("leeg antwoord", opschonen("", HUIS, PAPIER), None)
controleer("niets meegegeven", opschonen(None, HUIS, PAPIER), None)
controleer("alleen leestekens", opschonen("---", HUIS, PAPIER), None)
controleer("te kort", opschonen("ab", HUIS, PAPIER), None)
controleer("een getal is geen kenmerk", opschonen("500", HUIS, PAPIER), None)
controleer(
    "hele zin afgekeurd",
    opschonen("papier voor in het toilet dat vochtig is", HUIS, PAPIER),
    None,
)
controleer("twee woorden mag", opschonen("biologisch halfvol", "Zuivel", "Melk"),
           "biologisch halfvol")
# Het kenmerk wordt niet vertaald naar de stam: het knopje toont het woord zoals
# het binnenkwam. De stam dient alleen om twee schrijfwijzen te herkennen.
controleer("verbogen vorm blijft staan", opschonen("halfvolle melk", "Zuivel", "Melk"),
           "halfvolle")
controleer("maximum staat op twee", MAXIMUM_WOORDEN, 2)

# Zonder lade geen kenmerk: "vochtig" bestaat ook bij de doekjes.
lijst = Woordenlijst()
controleer("geen lade, geen kenmerk", lijst.pas_in(HUIS, None, "vochtig"), None)
controleer("geen afdeling, geen kenmerk", lijst.pas_in(None, PAPIER, "vochtig"), None)


# --- De woordenlijst houdt zichzelf bij elkaar ------------------------------
controleer("stam van een lang woord", stam("vochtige"), stam("vochtig"))
controleer("korte woorden blijven heel", stam("vol"), "vol")
controleer("pads blijft pads", stam("pads"), "pads")

lijst = Woordenlijst()
controleer("eerste winkel benoemt het", lijst.pas_in(HUIS, PAPIER, "vochtig"), "vochtig")
controleer("tweede winkel valt erop terug",
           lijst.pas_in(HUIS, PAPIER, "vochtige"), "vochtig")
controleer("derde winkel ook",
           lijst.pas_in(HUIS, PAPIER, "Toiletpapier Vochtige"), "vochtig")
controleer("één kenmerk in de lade", lijst.bekend(HUIS, PAPIER), ("vochtig",))

# Een écht ander woord hoort er wél bij te komen.
controleer("nieuw kenmerk erbij", lijst.pas_in(HUIS, PAPIER, "gekleurd"), "gekleurd")
controleer("nu twee kenmerken", len(lijst.bekend(HUIS, PAPIER)), 2)

# Wat de ene lade kent, geldt niet voor de andere.
controleer("andere lade kent het niet", lijst.bekend(KOFFIE, BONEN), ())


# --- Het vangnet: het kenmerk uit de productnaam ----------------------------
lijst = Woordenlijst()
lijst.leer(HUIS, PAPIER, "vochtig")

controleer(
    "vochtig staat in de naam",
    lijst.uit_naam(HUIS, PAPIER, "Page vochtig toiletpapier navulling 3 x 42 stuks"),
    "vochtig",
)
controleer(
    "verbogen in de naam telt ook",
    lijst.uit_naam(HUIS, PAPIER, "Edet vochtige toiletdoekjes"),
    "vochtig",
)
controleer(
    "gewoon toiletpapier krijgt niets",
    lijst.uit_naam(HUIS, PAPIER, "Page toiletpapier 3-laags 8 rollen"),
    None,
)
controleer(
    "onbekende lade levert niets",
    lijst.uit_naam(KOFFIE, BONEN, "vochtig iets"),
    None,
)
controleer("lege naam levert niets", lijst.uit_naam(HUIS, PAPIER, None), None)

# Op hele woorden, niet op letterreeksen. Anders zou "vol" aanslaan op
# "volkoren" en stond de halfvolle melk ineens bij de volle.
melk = Woordenlijst()
melk.leer("Zuivel", "Melk", "vol")
melk.leer("Zuivel", "Melk", "halfvol")
controleer(
    "volle melk is vol",
    melk.uit_naam("Zuivel", "Melk", "Campina volle melk 1 liter"),
    "vol",
)
controleer(
    "halfvolle melk is halfvol",
    melk.uit_naam("Zuivel", "Melk", "Campina halfvolle melk 1 liter"),
    "halfvol",
)
controleer(
    "volkoren is geen vol",
    melk.uit_naam("Zuivel", "Melk", "Volkoren beschuit"),
    None,
)

# De verbogen vorm van een andere winkel valt op het bestaande woord terug. Dit
# is de dubbele medeklinker: "halfvolle" hoort bij "halfvol", niet ernaast.
controleer("halfvolle valt op halfvol", melk.pas_in("Zuivel", "Melk", "halfvolle"),
           "halfvol")
controleer("er komt geen woord bij", len(melk.bekend("Zuivel", "Melk")), 2)


# --- Wat er in de opdracht aan de AI belandt --------------------------------
controleer("lege lijst geeft lege tekst", Woordenlijst().als_tekst(), "")
tekst = melk.als_tekst()
controleer("de lade staat erin", "Zuivel / Melk" in tekst, True)
controleer("beide woorden staan erin", "halfvol" in tekst and "vol" in tekst, True)


# --- Tellen, om ruis te kunnen herkennen ------------------------------------
producten = [
    {"hoofdgroep": HUIS, "subgroep": PAPIER, "kenmerk": "vochtig"},
    {"hoofdgroep": HUIS, "subgroep": PAPIER, "kenmerk": "vochtig"},
    {"hoofdgroep": HUIS, "subgroep": PAPIER, "kenmerk": None},
    {"hoofdgroep": HUIS, "subgroep": None, "kenmerk": "vochtig"},
    {"hoofdgroep": None, "subgroep": None, "kenmerk": None},
]
telling = tel_per_lade(producten)
controleer("alleen volledige regels tellen", len(telling), 1)
controleer("twee keer vochtig", telling[(HUIS, PAPIER, "vochtig")], 2)
controleer("niets in te tellen", tel_per_lade([]), {})


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de kenmerken geslaagd.")
