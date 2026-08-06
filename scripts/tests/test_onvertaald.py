"""
===============================================================================
 Dealbot — controle op het tellen van onvertaalde winkelgroepen

 Versie      : 1.0
 Reden       : De ochtendronde deelt sinds 06-08-2026 zelf in, maar mag daarbij
               nooit een AI-vraag stellen. Daarmee ontstaat een blinde vlek:
               brengt een winkel nieuwe groepsnamen mee — en een nieuwe keten
               brengt er honderden — dan blijven die onvertaald en hangen hun
               producten nergens onder.

               Deze telling is het enige dat dat zichtbaar maakt, zowel in het
               logboek van de ronde als op de beheerpagina. Telt hij verkeerd,
               dan blijft het probleem onopgemerkt terwijl de ronde elke ochtend
               groen afsluit. Vandaar dat hij hier vastligt, inclusief de rand
               die er in het echt toe doet: hoofdletters.
 Datum       : 06-08-2026 16:00

 Uitvoeren met: python scripts/tests/test_onvertaald.py
===============================================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indeel import tel_onvertaald  # noqa: E402

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


class NepDatabase:
    """
    Een database die alleen teruggeeft wat deze telling nodig heeft.

    De echte klasse praat over het net met Supabase; hier gaat het puur om de
    rekensom die daar bovenop zit.
    """

    def __init__(self, groepen, boekje):
        self._groepen = groepen
        self._boekje = boekje

    def winkelgroepen(self):
        return [{"winkel_id": w, "productgroep": naam} for w, naam in self._groepen]

    def koppelingen(self):
        return [{"winkel_id": w, "productgroep": naam} for w, naam in self._boekje]

    def winkels(self):
        return {1: "Albert Heijn", 2: "Aldi", 3: "Vomar"}


# --- Alles staat al in het boekje -------------------------------------------
# Het normale geval, elke ochtend: dan hoort er niets gemeld te worden.
controleer(
    "alles vertaald geeft niets terug",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Koffiebonen"), (1, "Toiletpapier")],
        boekje=[(1, "Koffiebonen"), (1, "Toiletpapier")],
    )),
    {},
)


# --- Een nieuwe winkel brengt zijn hele lijst mee ----------------------------
# Dit is waar het om begonnen is: Aldi erbij, en zijn groepsnamen staan nergens.
controleer(
    "een nieuwe winkel telt volledig mee",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Koffiebonen"), (2, "Kaffee"), (2, "Brot"), (2, "Obst")],
        boekje=[(1, "Koffiebonen")],
    )),
    {2: 3},
)


# --- Hoofdletters tellen niet mee -------------------------------------------
# Het indeelscript vergelijkt zonder hoofdletters. Zou deze telling dat wél
# doen, dan meldde de beheerpagina werk dat allang gedaan is — en dan ga je een
# vertaalronde starten die AI-vragen kost en niets oplevert.
controleer(
    "hoofdletters maken geen verschil",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Koffiebonen"), (1, "TOILETPAPIER")],
        boekje=[(1, "koffiebonen"), (1, "toiletpapier")],
    )),
    {},
)


# --- Dezelfde naam bij een andere winkel ------------------------------------
# Een vertaling geldt per winkel. "Koffiebonen" bij Albert Heijn zegt niets over
# "Koffiebonen" bij Aldi: die kan een heel ander schap bedoelen.
controleer(
    "een vertaling van winkel 1 dekt winkel 2 niet",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Koffiebonen"), (2, "Koffiebonen")],
        boekje=[(1, "Koffiebonen")],
    )),
    {2: 1},
)


# --- Een winkel zonder groepenlijst -----------------------------------------
# Vomar levert alleen een voorgelezen folder en dus geen groepsnamen. Die hoort
# niet als "niets te doen" gemeld te worden, maar helemaal niet voor te komen.
controleer(
    "een folderwinkel komt niet in de telling voor",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Koffiebonen"), (2, "Kaffee")],
        boekje=[(1, "Koffiebonen")],
    )).get(3),
    None,
)


# --- Een groep die bewust is afgevallen -------------------------------------
# Het boekje bevat ook regels zonder plek in onze indeling ("Kerstartikelen valt
# er niet onder"). Die zijn beantwoord en horen dus niet opnieuw gevraagd te
# worden — de telling kijkt alleen of de naam in het boekje staat, niet wat het
# antwoord was.
controleer(
    "een bekeken en afgevallen groep telt niet mee",
    tel_onvertaald(NepDatabase(
        groepen=[(1, "Tuinmeubelen")],
        boekje=[(1, "Tuinmeubelen")],
    )),
    {},
)


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op de onvertaalde groepen geslaagd.")
