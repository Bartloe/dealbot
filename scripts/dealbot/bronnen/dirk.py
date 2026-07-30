"""
===============================================================================
 Dealbot — aanbiedingen ophalen bij Dirk van den Broek

 Versie      : 1.0
 Reden       : Derde databron voor fase 1. Vomar bleek onbruikbaar: die zet zijn
               aanbiedingen alleen in een digitale folder, waar geen betrouwbare
               koppeling tussen product, prijs en inhoud uit te halen is. Dirk
               levert de folder wél als geordende gegevens, per afdeling, met
               per product de normale prijs en de actieprijs.
 Datum       : 31-07-2026 00:12

 Onderdelen:
   haal_op()        - geeft alle actuele weekaanbiedingen terug
   _vraag()         - stelt één vraag aan de gegevensingang van Dirk
   _afdelingen()    - welke afdelingen er zijn (groente, zuivel, ...)
   _actie_tekst()   - alleen een label als het iets toevoegt, zoals "VR, ZA & ZO"
   _webadres()      - bouwt de link naar de productpagina op dirk.nl
===============================================================================
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from typing import Any
from urllib.parse import quote

import requests

from ..model import Aanbieding, maak_aanbieding

log = logging.getLogger(__name__)

WINKEL_ID = 4
WINKEL_NAAM = "Dirk"

_URL = "https://web-gateway.dirk.nl/graphql"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Deze sleutel staat open en bloot in de website van Dirk zelf; hij hoort bij de
# publieke gegevensingang en geeft geen toegang tot klantgegevens.
_SLEUTEL = "6d3a42a3-6d93-4f98-838d-bcc0ab2307fd"

# De standaardwinkel van dirk.nl. De weekaanbiedingen zijn landelijk gelijk,
# dus één winkelnummer volstaat.
_WINKEL_NUMMER = 66

_KOPPEN = {
    "User-Agent": _USER_AGENT,
    "Content-Type": "application/json",
    "api_key": _SLEUTEL,
    "Origin": "https://www.dirk.nl",
    "Referer": "https://www.dirk.nl/",
}

_PRODUCT_URL = "https://www.dirk.nl/boodschappen/{afdeling}/{groep}/{naam}/{nummer}"
_AFBEELDING_URL = "https://web-fileserver.dirk.nl/{pad}?width=400"

_PAUZE_SECONDEN = 0.2      # rustig aan, afdeling voor afdeling

# Dirk zet boven elke aanbieding een label. "ACTIE" zegt niets extra's — dat de
# prijs lager is, blijkt al uit de prijzen zelf. Een label als "VR, ZA & ZO"
# zegt wél iets: dan geldt de aanbieding maar een paar dagen.
_LOZE_LABELS = {"actie"}

_VRAAG_AFDELINGEN = """
query Afdelingen {
  listDepartments { departments { id description } }
}
"""

_VRAAG_AANBIEDINGEN = """
query Aanbiedingen($winkel: Int, $afdeling: Int) {
  listOffers(store: $winkel, department: $afdeling) {
    currentOffers {
      offerId
      headerText
      packaging
      textPriceSign1
      startDate
      endDate
      products {
        productId
        normalPrice
        offerPrice
        productInformation {
          headerText
          packaging
          brand
          department
          webgroup
          image
        }
      }
    }
  }
}
"""

# Als de afdelingenlijst niet op te halen is, lopen we deze nummers langs. Dat
# is het bereik dat Dirk in de praktijk gebruikt.
_AFDELINGEN_TERUGVAL = list(range(1, 21))


class DirkFout(RuntimeError):
    """Het ophalen bij Dirk is niet gelukt."""


def _vraag(sessie: requests.Session, query: str, variabelen: dict[str, Any]) -> dict[str, Any]:
    """Stelt één vraag aan de gegevensingang van Dirk."""
    try:
        antwoord = sessie.post(
            _URL,
            json={"query": query, "variables": variabelen},
            headers=_KOPPEN,
            timeout=45,
        )
        antwoord.raise_for_status()
        inhoud = antwoord.json()
    except (requests.RequestException, ValueError) as fout:
        raise DirkFout(f"Kon Dirk niet bereiken: {fout}") from fout

    if inhoud.get("errors"):
        eerste = inhoud["errors"][0].get("message", "onbekende fout")
        raise DirkFout(f"Dirk gaf een foutmelding terug: {eerste}")

    return inhoud.get("data") or {}


def _afdelingen(sessie: requests.Session) -> list[int]:
    """De afdelingen waarin Dirk zijn aanbiedingen indeelt."""
    try:
        data = _vraag(sessie, _VRAAG_AFDELINGEN, {})
        nummers = [
            afdeling["id"]
            for afdeling in (data.get("listDepartments") or {}).get("departments") or []
            if afdeling.get("id") is not None
        ]
    except DirkFout as fout:
        log.warning("Afdelingenlijst van Dirk niet opgehaald (%s); vaste lijst gebruikt.", fout)
        return _AFDELINGEN_TERUGVAL

    return nummers or _AFDELINGEN_TERUGVAL


def _slug(tekst: str | None) -> str:
    """Maakt van "Aardappelen, groente & fruit" het stukje "aardappelen-groente-fruit"."""
    if not tekst:
        return "-"
    schoon = unicodedata.normalize("NFKD", tekst.lower())
    schoon = "".join(teken for teken in schoon if not unicodedata.combining(teken))
    schoon = re.sub(r"[^a-z0-9]+", "-", schoon)
    return schoon.strip("-") or "-"


def _webadres(product: dict[str, Any], info: dict[str, Any]) -> str | None:
    """De link naar de productpagina op dirk.nl."""
    nummer = product.get("productId")
    if not nummer:
        return None

    return _PRODUCT_URL.format(
        afdeling=_slug(info.get("department")),
        groep=_slug(info.get("webgroup")),
        naam=quote((info.get("headerText") or "product").lower(), safe=""),
        nummer=nummer,
    )


def _afbeelding(info: dict[str, Any]) -> str | None:
    """De productfoto bij Dirk staat op een aparte bestandsserver."""
    pad = info.get("image")
    if not pad:
        return None
    return _AFBEELDING_URL.format(pad=quote(pad, safe=""))


def _actie_tekst(actie: dict[str, Any]) -> str | None:
    """Het label boven de aanbieding, tenzij dat niets toevoegt."""
    label = (actie.get("textPriceSign1") or "").strip()
    if not label or label.lower() in _LOZE_LABELS:
        return None
    return label


def _datum(moment: str | None) -> str | None:
    """Alleen de datum uit "2026-07-29T00:00:00.000Z"."""
    return moment[:10] if moment else None


def _bedrag(waarde: Any) -> float | None:
    """Een prijs van nul betekent bij Dirk "niet bekend", niet "gratis"."""
    try:
        bedrag = float(waarde)
    except (TypeError, ValueError):
        return None
    return bedrag if bedrag > 0 else None


def _naar_aanbieding(product: dict[str, Any], actie: dict[str, Any]) -> Aanbieding:
    """Vertaalt één product uit de folder van Dirk naar onze eigen vorm."""
    info = product.get("productInformation") or {}

    # De verpakking bij het product ("500 g") is nauwkeuriger dan de tekst bij de
    # aanbieding ("Bak 500 gram of 1 kilo"); die laatste is de terugval.
    inhoud = info.get("packaging") or actie.get("packaging")

    return maak_aanbieding(
        winkel_id=WINKEL_ID,
        bron_id=str(product["productId"]),
        product_naam=info.get("headerText") or actie.get("headerText") or "",
        merk=info.get("brand"),
        variant=info.get("department"),
        actie_tekst=_actie_tekst(actie),
        actieprijs=_bedrag(product.get("offerPrice")),
        normale_prijs=_bedrag(product.get("normalPrice")),
        inhoud_tekst=inhoud,
        geldig_van=_datum(actie.get("startDate")),
        geldig_tot=_datum(actie.get("endDate")),
        product_url=_webadres(product, info),
        afbeelding_url=_afbeelding(info),
    )


def _voordeligste(nieuw: Aanbieding, bestaand: Aanbieding | None) -> Aanbieding:
    """Zit een product in twee aanbiedingen, dan houden we de goedkoopste."""
    if bestaand is None or bestaand.prijs is None:
        return nieuw
    if nieuw.prijs is None:
        return bestaand
    return nieuw if nieuw.prijs < bestaand.prijs else bestaand


def haal_op() -> list[Aanbieding]:
    """
    Haalt alle actuele weekaanbiedingen van Dirk op.

    De folder komt per afdeling binnen. Gaat één afdeling mis, dan gaat het
    script door met de rest: liever een lijst die een hoek mist dan helemaal
    geen lijst.
    """
    sessie = requests.Session()

    gevonden: dict[str, Aanbieding] = {}
    acties = 0
    bekeken = 0

    for afdeling in _afdelingen(sessie):
        try:
            data = _vraag(
                sessie, _VRAAG_AANBIEDINGEN,
                {"winkel": _WINKEL_NUMMER, "afdeling": afdeling},
            )
        except DirkFout as fout:
            log.warning("Afdeling %s van Dirk overgeslagen: %s", afdeling, fout)
            continue

        for actie in (data.get("listOffers") or {}).get("currentOffers") or []:
            acties += 1
            for product in actie.get("products") or []:
                if not product or not product.get("productId"):
                    continue
                bekeken += 1

                info = product.get("productInformation") or {}
                if not (info.get("headerText") or actie.get("headerText")):
                    continue

                try:
                    aanbieding = _naar_aanbieding(product, actie)
                except (KeyError, TypeError, ValueError) as fout:
                    log.warning(
                        "Product %s van Dirk overgeslagen: %s",
                        product.get("productId"), fout,
                    )
                    continue

                gevonden[aanbieding.bron_id] = _voordeligste(
                    aanbieding, gevonden.get(aanbieding.bron_id)
                )

        time.sleep(_PAUZE_SECONDEN)

    if not gevonden:
        raise DirkFout("Dirk gaf geen enkele aanbieding terug.")

    zonder_kiloprijs = sum(1 for a in gevonden.values() if a.prijs_per_eenheid is None)
    log.info(
        "%s: %s acties met %s producten bekeken, %s aanbiedingen overgehouden "
        "(%s zonder kiloprijs).",
        WINKEL_NAAM, acties, bekeken, len(gevonden), zonder_kiloprijs,
    )

    return list(gevonden.values())
