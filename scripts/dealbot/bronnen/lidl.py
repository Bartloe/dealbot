"""
===============================================================================
 Dealbot — aanbiedingen ophalen bij Lidl

 Versie      : 1.0
 Reden       : Lidl is de vijfde winkel. Zijn aanbiedingenpagina draagt de
               prijzen zelf bij zich: in de opmaak zit per product een blokje
               met titel, prijs, van-prijs, inhoud, indeling en looptijd. Eén
               verzoek levert de hele week, inclusief de acties die pas op
               woensdag of vrijdag beginnen.
 Datum       : 03-08-2026 13:05

 Onderdelen:
   haal_op()          - alle lopende aanbiedingen plus de groepen die langskwamen
   _haal_pagina()     - de aanbiedingenpagina, met een paar pogingen
   _blokken()         - vist de productblokjes uit de opmaak
   _prijsblok()       - de gewone prijs, of anders die van de Lidl Plus-kaart
   _actie_tekst()     - het label bij de aanbieding, inclusief "met Lidl Plus"
   _productgroep()    - de onderste laag van de indeling ("Yoghurt")
   _datum()           - van een tijdstempel naar een datum in Nederlandse tijd
   _loopt_nog()       - houdt afgelopen aanbiedingen buiten de lijst
===============================================================================
"""

from __future__ import annotations

import html
import json
import logging
import re
import time
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from ..model import Aanbieding, Oogst, maak_aanbieding

log = logging.getLogger(__name__)

WINKEL_ID = 6
WINKEL_NAAM = "Lidl"

# Deze verwijst door naar de campagnepagina van deze week; die hoeven we dus
# niet zelf te kennen.
_URL = "https://www.lidl.nl/aanbiedingen"
_BASIS = "https://www.lidl.nl"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Lidl weigert het verzoek (foutcode 503) als er geen gewone browserkoppen bij
# zitten; met name de regel hieronder over het soort antwoord is nodig.
_KOPPEN = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9",
}

_POGINGEN = 3
_WACHT_NA_FOUT = 3.0

# Elk product zit als een blokje gegevens in de opmaak van de pagina.
_BLOK = re.compile(r'data-grid-data="([^"]*)"')

# Labels die niets toevoegen: dat het een aanbieding is, blijkt al uit de rest.
_LOZE_LABELS = {"actie", "mega deal!"}

# Het veld waarin Lidl het hele indelingspad meegeeft.
_INDELING_VELD = "wonCategoryPrimary"


def _nederlandse_tijd() -> Any:
    """
    De Nederlandse tijdzone, of wereldtijd als het tijdzonebestand ontbreekt.

    Zonder tijdzone zou een aanbieding die om middernacht ingaat een dag te
    vroeg in de lijst komen. Ontbreekt het bestand (dat kan op Windows zonder
    het pakket tzdata), dan gaat de ronde gewoon door — met die kanttekening.
    """
    try:
        return ZoneInfo("Europe/Amsterdam")
    except ZoneInfoNotFoundError:
        log.warning(
            "Tijdzonebestand ontbreekt (pakket tzdata); de begindatums van Lidl "
            "kunnen een dag te vroeg staan."
        )
        return timezone.utc


_TIJDZONE = _nederlandse_tijd()


class LidlFout(RuntimeError):
    """Het ophalen bij Lidl is niet gelukt."""


def _haal_pagina(sessie: requests.Session) -> str:
    """
    Haalt de aanbiedingenpagina op, met een paar pogingen.

    Lidl blokkeert af en toe kort. Eén weigering hoort de ronde niet te
    bederven, dus we wachten even en proberen het opnieuw.
    """
    laatste = ""

    for poging in range(1, _POGINGEN + 1):
        try:
            antwoord = sessie.get(_URL, headers=_KOPPEN, timeout=45)
        except requests.RequestException as fout:
            laatste = str(fout)
            log.warning("Lidl niet bereikbaar, poging %s van %s: %s", poging, _POGINGEN, fout)
            time.sleep(_WACHT_NA_FOUT * poging)
            continue

        if antwoord.ok:
            # De pagina is UTF-8, maar Lidl zegt dat niet altijd; zonder deze
            # regel worden accenten onleesbaar.
            antwoord.encoding = antwoord.encoding or "utf-8"
            return antwoord.text

        laatste = f"foutcode {antwoord.status_code}"
        log.warning(
            "Lidl gaf foutcode %s, poging %s van %s.",
            antwoord.status_code, poging, _POGINGEN,
        )
        time.sleep(_WACHT_NA_FOUT * poging)

    raise LidlFout(f"Kon de aanbiedingenpagina van Lidl niet ophalen ({laatste}).")


def _blokken(pagina: str) -> list[dict[str, Any]]:
    """
    Vist de productblokjes uit de opmaak van de pagina.

    Een blokje dat niet te lezen is slaan we over: liever één aanbieding minder
    dan een hele ronde die strandt op een rare tekst.
    """
    blokken = []
    onleesbaar = 0

    for ruw in _BLOK.findall(pagina):
        try:
            blok = json.loads(html.unescape(ruw))
        except ValueError:
            onleesbaar += 1
            continue
        if isinstance(blok, dict):
            blokken.append(blok)

    if onleesbaar:
        log.warning("%s productblokjes van Lidl waren niet te lezen.", onleesbaar)

    return blokken


def _bedrag(waarde: Any) -> float | None:
    """Een bedrag van nul betekent bij Lidl "niet ingevuld", niet "gratis"."""
    try:
        bedrag = float(waarde)
    except (TypeError, ValueError):
        return None
    return bedrag if bedrag > 0 else None


def _prijsblok(blok: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Het prijsblokje van deze aanbieding, en of het een kaartprijs is.

    Ongeveer een derde van de aanbiedingen heeft geen gewone prijs maar alleen
    een prijs met de Lidl Plus-kaart. Die tellen gewoon mee — het is een echte
    aanbieding — maar de klant moet wel weten dat hij zijn kaart nodig heeft.
    Dat komt in de actietekst te staan.
    """
    gewoon = blok.get("price") or {}
    if _bedrag(gewoon.get("price")) is not None:
        return gewoon, False

    for kaart in blok.get("lidlPlus") or []:
        kaartprijs = (kaart or {}).get("price") or {}
        if _bedrag(kaartprijs.get("price")) is not None:
            return kaartprijs, True

    return {}, False


def _normale_prijs(prijs: dict[str, Any]) -> float | None:
    """De doorgestreepte prijs, als die er is."""
    korting = prijs.get("discount") or {}
    return _bedrag(prijs.get("oldPrice")) or _bedrag(korting.get("deletedPrice"))


def _inhoud_tekst(blok: dict[str, Any], prijs: dict[str, Any]) -> str | None:
    """De verpakking ("500 g", "6 x 0,33 l"), waar hij ook staat."""
    for bron in (prijs, blok.get("price") or {}):
        tekst = ((bron.get("packaging") or {}).get("text") or "").strip()
        if tekst:
            return tekst
    return None


def _actie_tekst(prijs: dict[str, Any], met_kaart: bool) -> str | None:
    """
    Het label bij de aanbieding, zoals de klant het op de pagina ziet.

    Drie dingen kunnen erin staan: de korting zelf ("-30%", "Elders €4.49"),
    de waarschuwing dat het een vanafprijs is, en of de kaart nodig is. Loze
    labels als "Actie" laten we weg: dat het een aanbieding is, is al bekend.
    """
    delen = []

    label = ((prijs.get("discount") or {}).get("discountText") or "").strip()
    if label and label.lower() not in _LOZE_LABELS:
        delen.append(label)

    if (prijs.get("prefix") or "").strip().lower() == "vanaf":
        delen.append("vanafprijs")

    if met_kaart:
        delen.append("met Lidl Plus")

    return ", ".join(delen) or None


def _productgroep(blok: dict[str, Any]) -> str | None:
    """
    De onderste laag van de indeling van Lidl: "Yoghurt", "Bier & Cider".

    Lidl levert een heel pad mee ("…/Kaas, zuivelproducten & eieren/Yoghurt").
    Het laatste stuk is wat de klant als groep herkent. De hoofdletter zetten we
    zelf, want Lidl doet dat niet altijd: anders staan "rundvlees" en
    "Rundvlees" allebei in de keuzelijst.
    """
    pad = ((blok.get("keyfacts") or {}).get(_INDELING_VELD) or "").strip()
    if not pad:
        return None

    groep = pad.rsplit("/", 1)[-1].strip()
    if not groep:
        return None

    return groep[0].upper() + groep[1:]


def _datum(tijdstempel: Any) -> str | None:
    """
    Van een tijdstempel naar een datum, in Nederlandse tijd.

    Lidl telt in seconden sinds 1970. Een aanbieding begint om middernacht
    Nederlandse tijd; zouden we in wereldtijd rekenen, dan kwam die dag een dag
    te vroeg te staan.
    """
    try:
        moment = datetime.fromtimestamp(int(tijdstempel), timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
    return moment.astimezone(_TIJDZONE).date().isoformat()


def _loopt_nog(geldig_tot: str | None) -> bool:
    """Aanbiedingen die gisteren zijn afgelopen horen niet meer in de lijst."""
    return not geldig_tot or geldig_tot >= date.today().isoformat()


def _naar_aanbieding(blok: dict[str, Any]) -> Aanbieding | None:
    """
    Vertaalt één productblokje van Lidl naar onze eigen vorm.

    Geeft niets terug als er geen prijs of geen naam in staat: zo'n blokje is
    geen aanbieding maar een plaatje of een verwijzing.
    """
    prijs, met_kaart = _prijsblok(blok)
    bedrag = _bedrag(prijs.get("price"))
    naam = (blok.get("fullTitle") or blok.get("title") or "").strip()
    nummer = blok.get("productId")

    if bedrag is None or not naam or not nummer:
        return None

    merk = blok.get("brand") or {}
    pad = (blok.get("canonicalPath") or blok.get("canonicalUrl") or "").strip()

    return maak_aanbieding(
        winkel_id=WINKEL_ID,
        bron_id=str(nummer),
        product_naam=naam,
        merk=(merk.get("name") or "").strip() or None,
        productgroep=_productgroep(blok),
        actie_tekst=_actie_tekst(prijs, met_kaart),
        actieprijs=bedrag,
        normale_prijs=_normale_prijs(prijs),
        inhoud_tekst=_inhoud_tekst(blok, prijs),
        geldig_van=_datum(blok.get("storeStartDate")),
        geldig_tot=_datum(blok.get("storeEndDate")),
        product_url=f"{_BASIS}{pad}" if pad.startswith("/") else None,
        afbeelding_url=(blok.get("image") or None),
    )


def haal_op() -> Oogst:
    """
    Haalt alle aanbiedingen op die deze week bij Lidl lopen.

    Alles staat op één pagina: de acties die maandag zijn begonnen én die van
    woensdag en vrijdag. Die laatste laten we staan, met hun eigen begindatum —
    ze horen bij deze week en de klant ziet zo wanneer hij ze kan halen.

    Wat Lidl níét geeft is een winkelindeling los van de aanbiedingen. De
    keuzelijst op het profielscherm krijgt daarom de groepen die deze week in de
    folder voorkwamen; volgende week kunnen dat er andere zijn.
    """
    sessie = requests.Session()
    pagina = _haal_pagina(sessie)

    blokken = _blokken(pagina)
    if not blokken:
        raise LidlFout("De aanbiedingenpagina van Lidl bevatte geen enkel product.")

    gevonden: dict[str, Aanbieding] = {}
    zonder_prijs = 0
    afgelopen = 0
    met_kaart = 0

    for blok in blokken:
        try:
            aanbieding = _naar_aanbieding(blok)
        except (KeyError, TypeError, ValueError) as fout:
            log.warning("Product %s van Lidl overgeslagen: %s", blok.get("productId"), fout)
            continue

        if aanbieding is None:
            zonder_prijs += 1
            continue

        if not _loopt_nog(aanbieding.geldig_tot):
            afgelopen += 1
            continue

        if aanbieding.actie_tekst and "Lidl Plus" in aanbieding.actie_tekst:
            met_kaart += 1

        gevonden[aanbieding.bron_id] = aanbieding

    if not gevonden:
        raise LidlFout("Lidl gaf geen enkele lopende aanbieding terug.")

    zonder_kiloprijs = sum(1 for a in gevonden.values() if a.prijs_per_eenheid is None)
    log.info(
        "%s: %s productblokjes bekeken, %s aanbiedingen overgehouden "
        "(%s alleen met Lidl Plus, %s zonder prijs, %s afgelopen, %s zonder kiloprijs).",
        WINKEL_NAAM, len(blokken), len(gevonden), met_kaart,
        zonder_prijs, afgelopen, zonder_kiloprijs,
    )

    oogst = Oogst(list(gevonden.values()))
    log.info("  %s groepen kwamen langs in de aanbiedingen van Lidl.", len(oogst.alle_groepen()))
    return oogst
