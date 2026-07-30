"""
===============================================================================
 Dealbot — aanbiedingen ophalen bij Jumbo

 Versie      : 1.1
 Reden       : De productgroep van Jumbo (category) gaat nu naar het veld
               "productgroep" in plaats van "variant" — zelfde gegeven, eerlijke
               naam. Jumbo deelt grof in ("Koffie en thee"), Albert Heijn fijn;
               daarom staat de winkelnaam bij de keuzelijst op het scherm.
 Datum       : 31-07-2026 01:12

 Onderdelen:
   haal_op()        - geeft alle actuele weekaanbiedingen terug
   _vraag_folder()  - haalt het aanbiedingenblad op bij Jumbo
   _aanbiedingen()  - pelt de losse aanbiedingen uit het antwoord
   _actie_tekst()   - kiest het label dat de korting beschrijft
   _inhoud_tekst()  - maakt van "570.0" + "ml" een leesbare inhoud
===============================================================================
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

import requests

from ..model import Aanbieding, maak_aanbieding

log = logging.getLogger(__name__)

WINKEL_ID = 2
WINKEL_NAAM = "Jumbo"

_URL = "https://www.jumbo.com/api/graphql"
_PRODUCT_URL = "https://www.jumbo.com{pad}"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Jumbo kent twee bladen: de weekaanbiedingen en een blad met bezorgkortingen.
# Alleen het eerste hoort in Dealbot thuis.
_BLAD = "actieprijs"

# Zonder deze koppen weigert Jumbo elk verzoek met "No client headers set".
_KOPPEN = {
    "User-Agent": _USER_AGENT,
    "Content-Type": "application/json",
    "Origin": "https://www.jumbo.com",
    "Referer": "https://www.jumbo.com/aanbiedingen",
    "apollographql-client-name": "jumbo-web",
    "apollographql-client-version": "1.0.0",
}

_VRAAG = """
query Aanbiedingen($blad: String!) {
  promotionTab(id: $blad) {
    runtimes {
      id
      active
      sections {
        promotions { ...Actie }
        categories { promotions { ...Actie } }
      }
    }
  }
}

fragment Actie on Promotion {
  id
  active
  hidden
  start { iso }
  end { iso }
  tags { text }
  products { ...Artikel }
}

fragment Artikel on Product {
  sku
  title
  brand
  category: rootCategory
  netContent
  weightMeasure
  image
  link
  price { price promoPrice }
}
"""

# Jumbo noemt de eenheden in het Engels; wij rekenen in Nederlandse eenheden.
_EENHEDEN = {"pieces": "stuks"}

# Naast de korting hangt Jumbo er soms een label bij als "Alleen online". Dat
# zegt niets over de prijs, dus daar mag niet mee gerekend worden.
_KORTINGSWOORDEN = ("gratis", "korting", "halve")

# Een enkel product staat bij Jumbo met een prijs van een paar cent in de lijst.
# Dat is geen winkelprijs maar een fout in hun gegevens, en zo'n product zou de
# lijst met "goedkoopste per kilo" onterecht aanvoeren.
_LAAGSTE_ECHTE_PRIJS = 0.10


class JumboFout(RuntimeError):
    """Het ophalen bij Jumbo is niet gelukt."""


def _vraag_folder(sessie: requests.Session) -> dict[str, Any]:
    """Haalt het aanbiedingenblad in één keer op bij Jumbo."""
    try:
        antwoord = sessie.post(
            _URL,
            json={"query": _VRAAG, "variables": {"blad": _BLAD}},
            headers=_KOPPEN,
            timeout=60,
        )
        antwoord.raise_for_status()
        inhoud = antwoord.json()
    except (requests.RequestException, ValueError) as fout:
        raise JumboFout(f"Kon de aanbiedingen van Jumbo niet ophalen: {fout}") from fout

    if inhoud.get("errors"):
        eerste = inhoud["errors"][0].get("message", "onbekende fout")
        raise JumboFout(f"Jumbo gaf een foutmelding terug: {eerste}")

    blad = (inhoud.get("data") or {}).get("promotionTab")
    if not blad:
        raise JumboFout("Jumbo gaf geen aanbiedingenblad terug.")

    return blad


def _aanbiedingen(blad: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Loopt alle lopende acties van deze week langs.

    Het blad is opgebouwd als folder: per looptijd een aantal onderdelen, en
    daarbinnen losse acties of acties per gangpad. Wij willen ze allemaal.
    """
    for looptijd in blad.get("runtimes") or []:
        if not looptijd.get("active"):
            continue

        for onderdeel in looptijd.get("sections") or []:
            acties = list(onderdeel.get("promotions") or [])
            for gangpad in onderdeel.get("categories") or []:
                acties.extend(gangpad.get("promotions") or [])

            for actie in acties:
                if actie.get("active") and not actie.get("hidden"):
                    yield actie


def _actie_tekst(actie: dict[str, Any]) -> str | None:
    """
    De tekst die de korting beschrijft, zoals "2 voor 6,00" of "1+1 gratis".

    Labels als "Alleen online" laten we liggen: die gaan over waar je de
    aanbieding krijgt, niet over wat je betaalt.
    """
    for label in actie.get("tags") or []:
        tekst = (label.get("text") or "").strip()
        if not tekst:
            continue
        if any(teken.isdigit() for teken in tekst):
            return tekst
        if any(woord in tekst.lower() for woord in _KORTINGSWOORDEN):
            return tekst
    return None


def _inhoud_tekst(product: dict[str, Any]) -> str | None:
    """Maakt van de losse velden 570.0 en "ml" de omschrijving "570 ml"."""
    hoeveelheid = product.get("netContent")
    eenheid = product.get("weightMeasure")
    if hoeveelheid is None or not eenheid:
        return None

    try:
        getal = float(hoeveelheid)
    except (TypeError, ValueError):
        return None

    return f"{getal:g} {_EENHEDEN.get(eenheid, eenheid)}"


def _datum(moment: dict[str, Any] | None) -> str | None:
    """Alleen de datum uit "2026-07-29T00:01:00+02:00"."""
    tekst = (moment or {}).get("iso")
    return tekst[:10] if tekst else None


def _euro(bedrag: Any) -> float | None:
    """Jumbo rekent in centen; wij in euro's."""
    if bedrag is None:
        return None
    try:
        return round(float(bedrag) / 100, 2)
    except (TypeError, ValueError):
        return None


def _prijs_is_geloofwaardig(product: dict[str, Any]) -> bool:
    """
    Houdt producten met een onmogelijke prijs buiten de lijst.

    Een product zonder prijs mag blijven — dat komt voor bij verse producten en
    die zakken vanzelf naar onderen. Een prijs van twee cent voor een kilo kaas
    is een fout bij de bron en zou juist bovenaan komen te staan.
    """
    normaal = _euro((product.get("price") or {}).get("price"))
    return normaal is None or normaal >= _LAAGSTE_ECHTE_PRIJS


def _naar_aanbieding(product: dict[str, Any], actie: dict[str, Any]) -> Aanbieding:
    """Vertaalt één product van Jumbo naar onze eigen vorm."""
    prijzen = product.get("price") or {}
    pad = product.get("link") or ""

    return maak_aanbieding(
        winkel_id=WINKEL_ID,
        bron_id=str(product["sku"]),
        product_naam=product.get("title") or "",
        merk=product.get("brand"),
        productgroep=product.get("category"),
        actie_tekst=_actie_tekst(actie),
        actieprijs=_euro(prijzen.get("promoPrice")),
        normale_prijs=_euro(prijzen.get("price")),
        inhoud_tekst=_inhoud_tekst(product),
        geldig_van=_datum(actie.get("start")),
        geldig_tot=_datum(actie.get("end")),
        product_url=_PRODUCT_URL.format(pad=pad) if pad else None,
        afbeelding_url=product.get("image"),
    )


def _voordeligste(nieuw: Aanbieding, bestaand: Aanbieding | None) -> Aanbieding:
    """
    Kiest welke aanbieding blijft staan als een product in meerdere acties zit.

    Dat komt bij Jumbo geregeld voor: hetzelfde pak zit dan zowel in een
    merkactie als in een gangpadactie. We houden de goedkoopste, want dat is de
    prijs die je uiteindelijk betaalt.
    """
    if bestaand is None or bestaand.prijs is None:
        return nieuw
    if nieuw.prijs is None:
        return bestaand
    return nieuw if nieuw.prijs < bestaand.prijs else bestaand


def haal_op() -> list[Aanbieding]:
    """
    Haalt alle actuele weekaanbiedingen van Jumbo op.

    Lukt het ophalen zelf niet, dan stopt het met een foutmelding: dan is er
    iets structureel mis. Losse producten die niet te vertalen zijn, worden
    overgeslagen zodat één raar product de hele ronde niet onderuit haalt.
    """
    sessie = requests.Session()
    blad = _vraag_folder(sessie)

    gevonden: dict[str, Aanbieding] = {}
    bekeken = 0
    acties = 0

    for actie in _aanbiedingen(blad):
        acties += 1
        for product in actie.get("products") or []:
            bekeken += 1
            if not product.get("sku") or not product.get("title"):
                continue
            if not _prijs_is_geloofwaardig(product):
                log.warning(
                    "Product %s van Jumbo overgeslagen: prijs van %s euro klopt niet.",
                    product.get("sku"), _euro((product.get("price") or {}).get("price")),
                )
                continue
            try:
                aanbieding = _naar_aanbieding(product, actie)
            except (KeyError, TypeError, ValueError) as fout:
                log.warning(
                    "Product %s van Jumbo overgeslagen: %s", product.get("sku"), fout
                )
                continue

            gevonden[aanbieding.bron_id] = _voordeligste(
                aanbieding, gevonden.get(aanbieding.bron_id)
            )

    zonder_kiloprijs = sum(1 for a in gevonden.values() if a.prijs_per_eenheid is None)
    log.info(
        "%s: %s acties met %s producten bekeken, %s aanbiedingen overgehouden "
        "(%s zonder kiloprijs).",
        WINKEL_NAAM, acties, bekeken, len(gevonden), zonder_kiloprijs,
    )

    return list(gevonden.values())
