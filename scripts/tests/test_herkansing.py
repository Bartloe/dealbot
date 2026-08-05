"""
===============================================================================
 Dealbot — controle op de herkansing bij een hapering

 Versie      : 1.0
 Reden       : Op 05-08-2026 sneuvelde de hele ronde van Albert Heijn op één
               afgebroken verbinding. Sindsdien probeert elke vraag aan de
               database het bij een hapering nog drie keer opnieuw. Dat is
               precies het soort ding dat je niet merkt als het stukgaat — het
               werkt immers alleen op de zeldzame ochtend dat het misgaat — dus
               wordt het hier bewezen met een nagebootste database.
 Datum       : 05-08-2026 13:30

 Onderdelen:
   hapering en dan goed  - een afgebroken verbinding houdt de ronde niet tegen
   tijdelijke storing    - foutcode 503 en 429 leveren een nieuwe poging op
   echte fout            - foutcode 400 stopt meteen, zonder zinloos herhalen
   blijvend stuk         - na alle pogingen een melding die dat ook zegt
   geduld                - er wordt echt gewacht tussen de pogingen

 Raakt de echte database niet aan en heeft geen sleutels nodig.

 Uitvoeren met: python scripts/tests/test_herkansing.py
===============================================================================
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dealbot import database as db  # noqa: E402
from dealbot.database import Database, DatabaseFout  # noqa: E402

fouten: list[str] = []


def controleer(omschrijving: str, gekregen, verwacht) -> None:
    if gekregen == verwacht:
        print(f"  [goed] {omschrijving}")
    else:
        print(f"  [FOUT] {omschrijving}: verwacht {verwacht!r}, gekregen {gekregen!r}")
        fouten.append(omschrijving)


class NepAntwoord:
    """Een antwoord van de database, zo mager als het hier nodig is."""

    def __init__(self, code: int) -> None:
        self.status_code = code
        self.ok = 200 <= code < 300
        self.text = f"nagebootst antwoord {code}"


class NepSessie:
    """
    Speelt de database na volgens een afgesproken lijstje uitkomsten.

    Elk item is een foutcode of een fout die opgeworpen moet worden. Zo is per
    poging te bepalen wat er gebeurt, en achteraf te tellen hoe vaak er is
    geprobeerd.
    """

    def __init__(self, uitkomsten: list) -> None:
        self.uitkomsten = list(uitkomsten)
        self.pogingen = 0
        self.headers: dict[str, str] = {}

    def request(self, methode, adres, **_opties):
        self.pogingen += 1
        uitkomst = self.uitkomsten.pop(0) if self.uitkomsten else self.uitkomsten
        if isinstance(uitkomst, Exception):
            raise uitkomst
        return NepAntwoord(uitkomst)


def maak_database(uitkomsten: list) -> tuple[Database, NepSessie]:
    verbinding = Database(url="https://nep.dealbot", sleutel="nep-sleutel")
    sessie = NepSessie(uitkomsten)
    verbinding.sessie = sessie
    return verbinding, sessie


# De pauzes worden niet echt uitgezeten; ze worden wel opgeschreven, zodat te
# controleren valt dat er tussen de pogingen gewacht wordt en hoe lang.
gewacht: list[float] = []
db.time.sleep = gewacht.append

AFGEBROKEN = requests.ConnectionError(
    "('Connection aborted.', TimeoutError('The write operation timed out'))"
)


print("1. Een hapering houdt de ronde niet tegen")
verbinding, sessie = maak_database([AFGEBROKEN, AFGEBROKEN, 200])
antwoord = verbinding._rest("POST", "aanbiedingen")
controleer("twee haperingen en dan toch weggeschreven", antwoord.status_code, 200)
controleer("daar waren drie pogingen voor nodig", sessie.pogingen, 3)
controleer("met een pauze tussen elke poging", gewacht, [0.5, 2])

print("\n2. Een database die het even te druk heeft")
gewacht.clear()
verbinding, sessie = maak_database([503, 429, 200])
antwoord = verbinding._rest("POST", "aanbiedingen")
controleer("na een storing en een drukke database toch gelukt", antwoord.status_code, 200)
controleer("ook hier drie pogingen", sessie.pogingen, 3)

print("\n3. Een echte fout wordt niet zinloos herhaald")
gewacht.clear()
verbinding, sessie = maak_database([400, 200])
try:
    verbinding._rest("POST", "aanbiedingen")
    melding = "(geen fout gekregen)"
except DatabaseFout as fout:
    melding = str(fout)
controleer("een foutcode 400 stopt meteen", "foutcode 400" in melding, True)
controleer("en wordt niet nog eens geprobeerd", sessie.pogingen, 1)
controleer("er is dus ook niet gewacht", gewacht, [])

print("\n4. Blijft het stuk, dan zegt de melding dat ook")
gewacht.clear()
verbinding, sessie = maak_database([AFGEBROKEN] * 4)
try:
    verbinding._rest("POST", "aanbiedingen")
    melding = "(geen fout gekregen)"
except DatabaseFout as fout:
    melding = str(fout)
controleer("vier pogingen gedaan", sessie.pogingen, 4)
controleer("de melding vertelt hoe vaak het geprobeerd is",
           "ook na 4 pogingen" in melding, True)
controleer("en waar het op strandde", "niet bereikbaar" in melding, True)
controleer("het wachten liep op", gewacht, [0.5, 2, 5])

print("\n5. Een blijvende storing van de database zelf")
gewacht.clear()
verbinding, sessie = maak_database([503] * 4)
try:
    verbinding._rest("GET", "winkels")
    melding = "(geen fout gekregen)"
except DatabaseFout as fout:
    melding = str(fout)
controleer("ook hier vier pogingen", sessie.pogingen, 4)
controleer("met een begrijpelijke melding", "ook na 4 pogingen" in melding, True)

print("\n6. Gaat het meteen goed, dan verandert er niets")
gewacht.clear()
verbinding, sessie = maak_database([200])
antwoord = verbinding._rest("GET", "winkels")
controleer("één poging is genoeg", sessie.pogingen, 1)
controleer("en er wordt niet gewacht", gewacht, [])

print(f"\n{'Alles goed.' if not fouten else str(len(fouten)) + ' fout:'}")
for regel in fouten:
    print(f"  - {regel}")
sys.exit(1 if fouten else 0)
