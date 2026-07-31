"""
===============================================================================
 Dealbot — het dagelijkse ophalen van aanbiedingen

 Versie      : 1.3
 Reden       : Elke ronde geeft nu ook door welke productgroepen zijn gezien, zodat
               de keuzelijst op het profielscherm blijft groeien en je een
               zoekvraag kunt zetten op een groep die deze week niet in de bonus is.
 Datum       : 31-07-2026 11:31

 Onderdelen:
   main()          - gaat alle winkels langs en vat het resultaat samen
   verwerk_winkel() - haalt op, schrijft weg, ruimt het oude op en onthoudt de
                      gevonden productgroepen

 Uitvoeren:
   python scripts/scan.py            alle winkels
   python scripts/scan.py --proef    alleen ophalen, niets wegschrijven
===============================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dealbot.bronnen import albert_heijn, dirk, jumbo  # noqa: E402
from dealbot.database import Database, DatabaseFout  # noqa: E402

# Elke winkel met de module die zijn aanbiedingen ophaalt.
WINKELS = [
    (albert_heijn.WINKEL_ID, albert_heijn.WINKEL_NAAM, albert_heijn.haal_op),
    (jumbo.WINKEL_ID, jumbo.WINKEL_NAAM, jumbo.haal_op),
    (dirk.WINKEL_ID, dirk.WINKEL_NAAM, dirk.haal_op),
]

log = logging.getLogger("dealbot")


def _laad_env() -> None:
    """
    Leest een .env-bestand uit de projectmap, als dat er staat.

    Zo werkt het script op de laptop zonder gedoe met omgevingsvariabelen. Op
    GitHub staat dat bestand er niet; daar komen de gegevens uit de beveiligde
    instellingen van de repo.
    """
    bestand = Path(__file__).resolve().parents[1] / ".env"
    if not bestand.exists():
        return

    try:
        for regel in bestand.read_text(encoding="utf-8").splitlines():
            regel = regel.strip()
            if not regel or regel.startswith("#") or "=" not in regel:
                continue
            naam, waarde = regel.split("=", 1)
            os.environ.setdefault(naam.strip(), waarde.strip().strip("\"'"))
    except OSError as fout:
        log.warning("Kon .env niet lezen: %s", fout)


def _stel_logging_in(uitgebreid: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if uitgebreid else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def verwerk_winkel(database: Database, winkel_id: int, naam: str, haal_op) -> int:
    """
    Haalt de aanbiedingen van één winkel op en zet ze in de database.

    Gaat er iets mis, dan blijft wat er al stond gewoon staan en gaat het script
    door met de volgende winkel. Eén kapotte bron mag de rest niet meeslepen.
    """
    log.info("== %s ==", naam)
    log_id, moment = database.start_ronde(winkel_id)

    try:
        aanbiedingen = haal_op()
    except Exception as fout:  # noqa: BLE001 - elke bronfout netjes vastleggen
        log.error("%s: ophalen mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Ophalen mislukt: {fout}")
        return 0

    if not aanbiedingen:
        log.warning("%s: geen aanbiedingen gevonden, oude lijst blijft staan.", naam)
        database.sluit_ronde(log_id, "mislukt", 0, "Geen aanbiedingen gevonden.")
        return 0

    try:
        aantal = database.schrijf(aanbiedingen, moment)
        database.ruim_oude_op(winkel_id, moment)
        # Pas hierna: de groepenlijst is een naslagwerk, geen voorwaarde. Mislukt
        # hij, dan zijn de aanbiedingen zelf al veilig binnen.
        database.onthoud_groepen(winkel_id, aanbiedingen)
    except DatabaseFout as fout:
        log.error("%s: wegschrijven mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Wegschrijven mislukt: {fout}")
        return 0

    database.sluit_ronde(log_id, "gelukt", aantal)
    log.info("%s: %s aanbiedingen klaargezet.", naam, aantal)
    return aantal


def proefdraai() -> int:
    """Haalt alles op zonder de database aan te raken, om te kunnen kijken."""
    totaal = 0
    for _, naam, haal_op in WINKELS:
        log.info("== %s (proef) ==", naam)
        try:
            aanbiedingen = haal_op()
        except Exception as fout:  # noqa: BLE001
            log.error("%s: ophalen mislukt: %s", naam, fout)
            continue

        totaal += len(aanbiedingen)
        met_kiloprijs = sum(1 for a in aanbiedingen if a.prijs_per_eenheid is not None)
        log.info(
            "%s: %s aanbiedingen, waarvan %s met kilo- of literprijs.",
            naam, len(aanbiedingen), met_kiloprijs,
        )
        for aanbieding in sorted(
            (a for a in aanbiedingen if a.prijs_per_eenheid),
            key=lambda a: a.prijs_per_eenheid,
        )[:10]:
            log.info(
                "   %-45s %-18s € %-7s per %s: € %s",
                aanbieding.product_naam[:45],
                (aanbieding.actie_tekst or "")[:18],
                aanbieding.prijs,
                aanbieding.eenheid_norm,
                aanbieding.prijs_per_eenheid,
            )
    return totaal


def main() -> int:
    argumenten = argparse.ArgumentParser(description="Aanbiedingen ophalen voor Dealbot.")
    argumenten.add_argument("--proef", action="store_true",
                            help="alleen ophalen en tonen, niets wegschrijven")
    argumenten.add_argument("--uitgebreid", action="store_true",
                            help="meer meldingen tonen")
    keuzes = argumenten.parse_args()

    _stel_logging_in(keuzes.uitgebreid)
    _laad_env()

    if keuzes.proef:
        totaal = proefdraai()
        log.info("Proef klaar: %s aanbiedingen opgehaald, niets weggeschreven.", totaal)
        return 0

    try:
        database = Database()
    except DatabaseFout as fout:
        log.error("%s", fout)
        return 1

    totaal = 0
    mislukt = []
    for winkel_id, naam, haal_op in WINKELS:
        aantal = verwerk_winkel(database, winkel_id, naam, haal_op)
        totaal += aantal
        if aantal == 0:
            mislukt.append(naam)

    log.info("Klaar: %s aanbiedingen in de database.", totaal)
    if mislukt:
        log.error("Niet gelukt bij: %s", ", ".join(mislukt))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
