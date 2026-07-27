"""
===============================================================================
 Dealbot — prijsnormalisatie

 Versie      : 1.0
 Reden       : Aanbiedingen van verschillende winkels vergelijkbaar maken door de
               inhoud te herkennen en de prijs om te rekenen naar kilo of liter.
 Datum       : 27-07-2026 21:04

 Onderdelen:
   lees_inhoud()        - herkent "400 g", "2 x 125 g", "1,5 l", "5 stuks"
   effectieve_prijs()   - rekent "2 voor 3.50" of "25% korting" om naar stuksprijs
   prijs_per_eenheid()  - de kilo- of literprijs, of niets als die onbekend is
   product_sleutel()    - sleutel om hetzelfde product bij winkels te groeperen
===============================================================================
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Eenheden die we herkennen, met de omrekenfactor naar de standaardeenheid.
_EENHEDEN = {
    "kg": ("kg", 1.0),
    "kilo": ("kg", 1.0),
    "g": ("kg", 0.001),
    "gr": ("kg", 0.001),
    "gram": ("kg", 0.001),
    "mg": ("kg", 0.000001),
    "l": ("l", 1.0),
    "liter": ("l", 1.0),
    "ltr": ("l", 1.0),
    "cl": ("l", 0.01),
    "ml": ("l", 0.001),
}

# Woorden die op losse exemplaren duiden in plaats van op gewicht of inhoud.
_STUKS_WOORDEN = {
    "stuk", "stuks", "st", "pack", "pak", "pakket", "rollen", "rol",
    "zakken", "zak", "blikken", "blik", "flessen", "fles", "bossen", "bos",
}


@dataclass(frozen=True)
class Inhoud:
    """De inhoud van een verpakking, omgerekend naar kilo, liter of stuks."""

    waarde: float          # de oorspronkelijke hoeveelheid, bijv. 400
    eenheid: str           # de oorspronkelijke eenheid, bijv. "g"
    norm_waarde: float     # omgerekend, bijv. 0.4
    norm_eenheid: str      # "kg", "l" of "stuk"


def _getal(tekst: str) -> float | None:
    """Zet "1,5" of "0.75" om naar een getal. Geeft niets terug bij onzin."""
    try:
        return float(tekst.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def lees_inhoud(tekst: str | None) -> Inhoud | None:
    """
    Herkent de inhoud in een omschrijving als "400 g", "2 x 125 g" of "5 stuks".

    Geeft niets terug als de inhoud niet met zekerheid af te leiden is; die
    aanbiedingen horen onderaan de lijst en niet met een verzonnen kiloprijs
    bovenaan.
    """
    if not tekst:
        return None

    schoon = unicodedata.normalize("NFKD", tekst).lower().strip()
    schoon = schoon.replace("×", "x").replace("*", "x")

    eenheden = "|".join(sorted(_EENHEDEN, key=len, reverse=True))

    # "2 x 125 g" of "6 x 90 ml" — aantal maal inhoud
    match = re.search(
        rf"(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*({eenheden})\b", schoon
    )
    if match:
        aantal = _getal(match.group(1))
        per_stuk = _getal(match.group(2))
        eenheid = match.group(3)
        if aantal and per_stuk:
            norm_eenheid, factor = _EENHEDEN[eenheid]
            totaal = aantal * per_stuk
            return Inhoud(totaal, eenheid, totaal * factor, norm_eenheid)

    # "400 g", "1,5 l", "0,52 l"
    match = re.search(rf"(\d+(?:[.,]\d+)?)\s*({eenheden})\b", schoon)
    if match:
        waarde = _getal(match.group(1))
        eenheid = match.group(2)
        if waarde:
            norm_eenheid, factor = _EENHEDEN[eenheid]
            return Inhoud(waarde, eenheid, waarde * factor, norm_eenheid)

    # "5 stuks", "2 rollen"
    woorden = "|".join(sorted(_STUKS_WOORDEN, key=len, reverse=True))
    match = re.search(rf"(\d+)\s*({woorden})\b", schoon)
    if match:
        aantal = _getal(match.group(1))
        if aantal:
            return Inhoud(aantal, match.group(2), aantal, "stuk")

    # "2-pack"
    match = re.search(r"(\d+)\s*-\s*pack\b", schoon)
    if match:
        aantal = _getal(match.group(1))
        if aantal:
            return Inhoud(aantal, "pack", aantal, "stuk")

    # "per stuk"
    if re.search(r"\bper\s+stuk\b", schoon) or schoon in _STUKS_WOORDEN:
        return Inhoud(1.0, "stuk", 1.0, "stuk")

    return None


def effectieve_prijs(
    actie_tekst: str | None,
    actieprijs: float | None,
    normale_prijs: float | None,
) -> float | None:
    """
    De prijs die je per stuk betaalt als je van de aanbieding gebruikmaakt.

    Winkels geven lang niet altijd een kant-en-klare actieprijs mee. Bij
    "2 voor 3.50" of "1 + 1 gratis" moeten we die zelf uitrekenen, anders zou een
    aanbieding met korting duurder lijken dan hij is.
    """
    if actieprijs is not None:
        return round(float(actieprijs), 4)

    if not actie_tekst or normale_prijs is None:
        return round(float(normale_prijs), 4) if normale_prijs is not None else None

    tekst = actie_tekst.lower().strip()
    basis = float(normale_prijs)

    # "2 voor 3.50"
    match = re.search(r"(\d+)\s*voor\s*€?\s*(\d+(?:[.,]\d+)?)", tekst)
    if match:
        aantal = _getal(match.group(1))
        totaal = _getal(match.group(2))
        if aantal and totaal:
            return round(totaal / aantal, 4)

    # "voor 3.49"
    match = re.search(r"^voor\s*€?\s*(\d+(?:[.,]\d+)?)", tekst)
    if match:
        bedrag = _getal(match.group(1))
        if bedrag:
            return round(bedrag, 4)

    # "1 + 1 gratis", "2 + 1 gratis"
    match = re.search(r"(\d+)\s*\+\s*(\d+)\s*gratis", tekst)
    if match:
        betaald = _getal(match.group(1))
        gratis = _getal(match.group(2))
        if betaald and gratis is not None:
            return round(basis * betaald / (betaald + gratis), 4)

    # "2e halve prijs", "2e gratis"
    if re.search(r"2e\s+halve\s+prijs", tekst):
        return round(basis * 0.75, 4)
    if re.search(r"2e\s+gratis", tekst):
        return round(basis * 0.5, 4)

    # "25% korting", "15% volume voordeel"
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", tekst)
    if match:
        percentage = _getal(match.group(1))
        if percentage is not None and 0 < percentage < 100:
            return round(basis * (1 - percentage / 100), 4)

    return round(basis, 4)


def prijs_per_eenheid(prijs: float | None, inhoud: Inhoud | None) -> float | None:
    """De prijs per kilo of liter. Geeft niets terug als de inhoud onbekend is."""
    if prijs is None or inhoud is None or not inhoud.norm_waarde:
        return None
    return round(float(prijs) / inhoud.norm_waarde, 4)


def product_sleutel(merk: str | None, product_naam: str) -> str:
    """
    Sleutel waarmee hetzelfde product bij verschillende winkels wordt gegroepeerd.

    Zonder EAN-codes is dit een benadering: merk en productnaam ontdaan van
    hoofdletters, leestekens en de inhoudsaanduiding. Vanaf fase 2 neemt de
    productendatabase met EAN-codes dit over.
    """
    ruw = f"{merk or ''} {product_naam}".lower()
    ruw = unicodedata.normalize("NFKD", ruw)
    ruw = "".join(teken for teken in ruw if not unicodedata.combining(teken))

    # Inhoudsaanduidingen weglaten, die horen niet bij de productnaam.
    eenheden = "|".join(sorted(_EENHEDEN, key=len, reverse=True))
    ruw = re.sub(rf"\b\d+(?:[.,]\d+)?\s*(?:{eenheden})\b", " ", ruw)
    ruw = re.sub(r"\b\d+\s*x\s*\d+\b", " ", ruw)
    ruw = re.sub(r"\b\d+\s*-?\s*(?:pack|stuks?|rollen)\b", " ", ruw)

    ruw = re.sub(r"[^a-z0-9]+", " ", ruw)
    return " ".join(ruw.split())
