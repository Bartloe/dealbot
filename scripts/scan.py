"""
===============================================================================
 Dealbot — het dagelijkse ophalen van aanbiedingen

 Versie      : 1.8
 Reden       : Lidl komt erbij als vijfde winkel. Zijn aanbiedingen staan met
               prijs en al op zijn eigen aanbiedingenpagina, dus hij werkt als
               Albert Heijn, Jumbo en Dirk: gewoon elke ochtend ophalen.
 Datum       : 03-08-2026 13:10

 Onderdelen:
   main()               - gaat alle winkels langs en vat het resultaat samen
   verwerk_winkel()     - aanbiedingen: ophalen, wegschrijven, oude opruimen
   verwerk_assortiment()- hetzelfde voor het gewone schap
   verwerk_folder()     - de weekfolder laten aflezen, alleen als hij nieuw is

 Uitvoeren:
   python scripts/scan.py            alles
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

from dealbot.bronnen import albert_heijn, dirk, jumbo, lidl, vomar, vomar_folder  # noqa: E402
from dealbot.database import Database, DatabaseFout  # noqa: E402

# Elke winkel met de module die zijn aanbiedingen ophaalt.
WINKELS = [
    (albert_heijn.WINKEL_ID, albert_heijn.WINKEL_NAAM, albert_heijn.haal_op),
    (jumbo.WINKEL_ID, jumbo.WINKEL_NAAM, jumbo.haal_op),
    (dirk.WINKEL_ID, dirk.WINKEL_NAAM, dirk.haal_op),
    (lidl.WINKEL_ID, lidl.WINKEL_NAAM, lidl.haal_op),
]

# Winkels die hun hele assortiment met gewone prijzen publiceren. Dat is iets
# anders dan een aanbiedingenbron: dit zijn de gewone schapprijzen.
ASSORTIMENTEN = [
    (vomar.WINKEL_ID, vomar.WINKEL_NAAM, vomar.haal_assortiment),
]

# Winkels waarvan de aanbiedingen alleen in een digitale folder staan. Die wordt
# door een AI afgelezen, en dat kost tientallen vragen per folder. Daarom worden
# deze bronnen anders behandeld dan de rest: eerst kijken of de folder die er nu
# hangt al ingelezen is, en alleen lezen als hij nieuw is.
FOLDERS = [
    (vomar_folder.WINKEL_ID, vomar_folder.WINKEL_NAAM, vomar_folder),
]

# Zoveel folderpagina's leest een proefdraai; genoeg om te zien of het klopt,
# zonder de dagvoorraad AI-vragen op te maken.
PROEFPAGINAS = 2

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

    # De AI-bibliotheek meldt elk verzoek apart. Bij een folder van veertig
    # pagina's verdrinkt het echte verhaal daarin, dus die houden we stil tenzij
    # er om uitgebreide meldingen is gevraagd.
    if not uitgebreid:
        for naam in ("httpx", "httpcore", "google_genai", "google.genai"):
            logging.getLogger(naam).setLevel(logging.WARNING)


def verwerk_winkel(database: Database, winkel_id: int, naam: str, haal_op) -> int:
    """
    Haalt de aanbiedingen van één winkel op en zet ze in de database.

    Gaat er iets mis, dan blijft wat er al stond gewoon staan en gaat het script
    door met de volgende winkel. Eén kapotte bron mag de rest niet meeslepen.
    """
    log.info("== %s ==", naam)
    log_id, moment = database.start_ronde(winkel_id)

    try:
        oogst = haal_op()
    except Exception as fout:  # noqa: BLE001 - elke bronfout netjes vastleggen
        log.error("%s: ophalen mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Ophalen mislukt: {fout}")
        return 0

    if not oogst.aanbiedingen:
        log.warning("%s: geen aanbiedingen gevonden, oude lijst blijft staan.", naam)
        database.sluit_ronde(log_id, "mislukt", 0, "Geen aanbiedingen gevonden.")
        return 0

    try:
        aantal = database.schrijf(oogst.aanbiedingen, moment)
        database.ruim_oude_op(winkel_id, moment)
        # Pas hierna: de groepenlijst is een naslagwerk, geen voorwaarde. Mislukt
        # hij, dan zijn de aanbiedingen zelf al veilig binnen.
        database.bewaar_groepen(winkel_id, oogst.alle_groepen())
    except DatabaseFout as fout:
        log.error("%s: wegschrijven mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Wegschrijven mislukt: {fout}")
        return 0

    database.sluit_ronde(log_id, "gelukt", aantal)
    log.info("%s: %s aanbiedingen klaargezet.", naam, aantal)
    return aantal


def verwerk_assortiment(database: Database, winkel_id: int, naam: str, haal_op) -> int:
    """
    Haalt het hele assortiment van één winkel op en zet het in de database.

    Werkt net als verwerk_winkel(), maar dan voor het gewone schap. Er komen
    hier geen aanbiedingen binnen, dus de winkelindeling gaat bewust níet naar
    de keuzelijst van het profielscherm: een zoekvraag op zo'n groep zou nooit
    een treffer opleveren. De groepen komen wel op de standaardprijzen-pagina
    zelf terecht, rechtstreeks uit de producten.
    """
    log.info("== %s (assortiment) ==", naam)
    log_id, moment = database.start_ronde(winkel_id)

    try:
        assortiment = haal_op()
    except Exception as fout:  # noqa: BLE001 - elke bronfout netjes vastleggen
        log.error("%s: ophalen mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Ophalen mislukt: {fout}")
        return 0

    if not assortiment.producten:
        log.warning("%s: geen producten gevonden, oude lijst blijft staan.", naam)
        database.sluit_ronde(log_id, "mislukt", 0, "Geen producten gevonden.")
        return 0

    try:
        aantal = database.schrijf_standaardprijzen(assortiment.producten, moment)
        database.ruim_oude_prijzen_op(winkel_id, moment)
    except DatabaseFout as fout:
        log.error("%s: wegschrijven mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Wegschrijven mislukt: {fout}")
        return 0

    database.sluit_ronde(log_id, "gelukt", aantal)
    log.info("%s: %s standaardprijzen klaargezet.", naam, aantal)
    return aantal


def verwerk_folder(database: Database, winkel_id: int, naam: str, bron) -> int:
    """
    Leest de weekfolder van één winkel, maar alleen als hij nieuw is.

    Een folder laten aflezen kost tientallen AI-vragen en de folder verandert
    maar één keer per week. Staat de uitgave die nu op de site hangt al in de
    database, dan is er niets te doen: de aanbiedingen blijven gewoon staan.

    Geeft het aantal aanbiedingen terug, of -1 als er niets te doen was. Dat
    verschil telt: niets te doen is een goede uitkomst, nul aanbiedingen niet.
    """
    log.info("== %s (folder) ==", naam)

    try:
        folder = bron.zoek_folder()
    except Exception as fout:  # noqa: BLE001 - elke bronfout netjes vastleggen
        log.error("%s: de folder is niet te vinden: %s", naam, fout)
        return 0

    if database.folder_al_gelezen(winkel_id, folder.voorvoegsel):
        log.info("%s: '%s' staat al in de database; niets te lezen.", naam, folder.titel)
        return -1

    log_id, moment = database.start_ronde(winkel_id)

    try:
        oogst = bron.haal_op(folder=folder)
    except Exception as fout:  # noqa: BLE001
        log.error("%s: het lezen van de folder mislukte: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Folder lezen mislukt: {fout}")
        return 0

    if not oogst.aanbiedingen:
        log.warning("%s: geen aanbiedingen uit de folder, oude lijst blijft staan.", naam)
        database.sluit_ronde(log_id, "mislukt", 0, "Geen aanbiedingen in de folder gevonden.")
        return 0

    try:
        aantal = database.schrijf(oogst.aanbiedingen, moment)
        database.ruim_oude_op(winkel_id, moment)
    except DatabaseFout as fout:
        log.error("%s: wegschrijven mislukt: %s", naam, fout)
        database.sluit_ronde(log_id, "mislukt", 0, f"Wegschrijven mislukt: {fout}")
        return 0

    database.sluit_ronde(log_id, "gelukt", aantal)
    log.info("%s: %s aanbiedingen uit '%s' klaargezet.", naam, aantal, folder.titel)
    return aantal


def proefdraai() -> int:
    """Haalt alles op zonder de database aan te raken, om te kunnen kijken."""
    totaal = 0
    for _, naam, haal_op in WINKELS:
        log.info("== %s (proef) ==", naam)
        try:
            oogst = haal_op()
        except Exception as fout:  # noqa: BLE001
            log.error("%s: ophalen mislukt: %s", naam, fout)
            continue

        aanbiedingen = oogst.aanbiedingen
        totaal += len(aanbiedingen)
        met_kiloprijs = sum(1 for a in aanbiedingen if a.prijs_per_eenheid is not None)
        log.info(
            "%s: %s aanbiedingen, waarvan %s met kilo- of literprijs; "
            "%s productgroepen in de winkelindeling.",
            naam, len(aanbiedingen), met_kiloprijs, len(oogst.alle_groepen()),
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

    for _, naam, haal_op in ASSORTIMENTEN:
        log.info("== %s (assortiment, proef) ==", naam)
        try:
            assortiment = haal_op()
        except Exception as fout:  # noqa: BLE001
            log.error("%s: ophalen mislukt: %s", naam, fout)
            continue

        producten = assortiment.producten
        met_ean = sum(1 for p in producten if p.ean)
        log.info(
            "%s: %s producten met een gewone prijs, waarvan %s met streepjescode; "
            "%s productgroepen in de winkelindeling.",
            naam, len(producten), met_ean, len(assortiment.productgroepen),
        )

    # Van een folder worden in de proef maar een paar pagina's gelezen: elke
    # pagina kost een AI-vraag en die zijn per dag beperkt.
    for _, naam, bron in FOLDERS:
        log.info("== %s (folder, proef: %s pagina's) ==", naam, PROEFPAGINAS)
        try:
            folder = bron.zoek_folder()
            log.info("%s: er hangt nu '%s'.", naam, folder.titel)
            oogst = bron.haal_op(folder=folder, laatste_pagina=PROEFPAGINAS)
        except Exception as fout:  # noqa: BLE001
            log.error("%s: het lezen van de folder mislukte: %s", naam, fout)
            continue

        for aanbieding in oogst.aanbiedingen:
            log.info(
                "   %-45s %-22s € %-7s (was %s) per %s: € %s",
                aanbieding.product_naam[:45],
                (aanbieding.actie_tekst or "")[:22],
                aanbieding.prijs,
                aanbieding.normale_prijs,
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

    prijzen = 0
    for winkel_id, naam, haal_op in ASSORTIMENTEN:
        aantal = verwerk_assortiment(database, winkel_id, naam, haal_op)
        prijzen += aantal
        if aantal == 0:
            mislukt.append(f"{naam} (assortiment)")

    for winkel_id, naam, bron in FOLDERS:
        aantal = verwerk_folder(database, winkel_id, naam, bron)
        if aantal > 0:
            totaal += aantal
        elif aantal == 0:
            mislukt.append(f"{naam} (folder)")

    log.info(
        "Klaar: %s aanbiedingen en %s standaardprijzen in de database.", totaal, prijzen
    )
    if mislukt:
        log.error("Niet gelukt bij: %s", ", ".join(mislukt))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
