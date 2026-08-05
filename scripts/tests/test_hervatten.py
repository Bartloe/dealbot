"""
===============================================================================
 Dealbot — controle op het hervatten van een afgebroken vertaalronde

 Versie      : 1.0
 Reden       : Een vertaalronde valt stil zodra de dagvoorraad AI-vragen op is.
               Zonder hervatten is de keuze dan: alles opnieuw vragen (en dus
               het werk van gisteravond weggooien) of niets doen. Beide zijn
               fout, en het gaat om schaarse vragen die dezelfde dag ook de
               folderlezer nodig heeft.

               Het gaat mis op de randen, en juist die staan hier vast: een
               ronde die over middernacht heen loopt mag niet als twee rondes
               gelden, en een regel uit een oudere ronde moet wél opnieuw langs.
 Datum       : 06-08-2026 00:45

 Uitvoeren met: python scripts/tests/test_hervatten.py
===============================================================================
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indeel import _grens_van, _moment  # noqa: E402

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen != verwacht:
        fouten.append(f"{omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")


NL = ZoneInfo("Europe/Amsterdam")


def regel(moment: str | None):
    """Eén regel uit het vertaalboekje, met alleen het moment dat hier telt."""
    return {"winkel_id": 1, "productgroep": "iets", "gewijzigd_op": moment}


# --- Het moment lezen -------------------------------------------------------
controleer("gewone tijdstempel",
           _moment("2026-08-05T21:00:00+00:00"),
           datetime(2026, 8, 5, 21, 0, tzinfo=timezone.utc))
controleer("met een Z erachter",
           _moment("2026-08-05T21:00:00Z"),
           datetime(2026, 8, 5, 21, 0, tzinfo=timezone.utc))
# Zonder tijdzone komt het uit de database en is het altijd UTC. Zou dat als
# lokale tijd gelezen worden, dan schuift alles twee uur op en valt de grens
# midden in de ronde.
controleer("zonder tijdzone geldt als UTC",
           _moment("2026-08-05T21:00:00"),
           datetime(2026, 8, 5, 21, 0, tzinfo=timezone.utc))
controleer("leeg moment", _moment(None), None)
controleer("lege tekst", _moment(""), None)
controleer("onleesbaar moment", _moment("gisteravond laat"), None)


# --- De grens zonder eigen datum --------------------------------------------
# Een ronde die om 23.50 begint en na middernacht doorloopt, is één ronde. Op
# een kalenderdag afgaan zou de regels van vóór twaalven opnieuw laten vragen.
rond_middernacht = [
    regel("2026-08-04T09:00:00+00:00"),   # de oude ronde, moet opnieuw
    regel("2026-08-05T21:50:00+00:00"),   # 23.50 Nederlandse tijd
    regel("2026-08-05T22:30:00+00:00"),   # 00.30, dus dezelfde ronde
]
grens = _grens_van(rond_middernacht, "auto")
controleer("de grens ligt vóór het begin van de ronde",
           grens < _moment("2026-08-05T21:50:00+00:00"), True)
controleer("en ná de vorige ronde",
           grens > _moment("2026-08-04T09:00:00+00:00"), True)

controleer("zonder regels geen grens", _grens_van([], "auto"), None)
controleer("zonder bruikbare momenten geen grens",
           _grens_van([regel(None), regel("onzin")], "auto"), None)


# --- De grens met een eigen datum -------------------------------------------
controleer("Nederlandse schrijfwijze",
           _grens_van([], "05-08-2026"),
           datetime(2026, 8, 5, 0, 0, tzinfo=NL))
controleer("omgekeerde schrijfwijze mag ook",
           _grens_van([], "2026-08-05"),
           datetime(2026, 8, 5, 0, 0, tzinfo=NL))
# Een eigen datum gaat vóór de afleiding: anders zou een ronde van drie dagen
# alsnog op één etmaal teruggebracht worden.
controleer("de eigen datum wint van de afleiding",
           _grens_van(rond_middernacht, "05-08-2026"),
           datetime(2026, 8, 5, 0, 0, tzinfo=NL))

try:
    _grens_van([], "vorige week dinsdag")
    fouten.append("onleesbare datum: verwacht een foutmelding, kreeg er geen")
except ValueError as fout:
    controleer("de melding noemt de schrijfwijze", "05-08-2026" in str(fout), True)


# --- Wat er dan overgeslagen wordt ------------------------------------------
# Dit is de rekensom die stap_vertalen maakt: alles ná de grens is al gevraagd.
nu = datetime.now(timezone.utc)
boekje = [
    {"winkel_id": 1, "productgroep": "Toiletpapier",
     "gewijzigd_op": (nu - timedelta(minutes=30)).isoformat()},
    {"winkel_id": 1, "productgroep": "Koffiebonen",
     "gewijzigd_op": (nu - timedelta(hours=6)).isoformat()},
    {"winkel_id": 2, "productgroep": "Melk",
     "gewijzigd_op": (nu - timedelta(days=3)).isoformat()},
]
grens = _grens_van(boekje, "auto")
gedaan = sorted(
    rij["productgroep"] for rij in boekje
    if (moment := _moment(rij.get("gewijzigd_op"))) and moment >= grens
)
controleer("alleen de oude regel komt opnieuw aan de beurt",
           gedaan, ["Koffiebonen", "Toiletpapier"])


# --- Uitslag ----------------------------------------------------------------
if fouten:
    print(f"{len(fouten)} controle(s) mislukt:")
    for fout in fouten:
        print("  -", fout)
    sys.exit(1)

print("Alle controles op het hervatten geslaagd.")
