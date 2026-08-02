"""
===============================================================================
 Dealbot — het assortiment ophalen bij Vomar

 Versie      : 1.0
 Reden       : Vomar stond uit omdat zijn aanbiedingen alleen in een digitale
               folder staan. Uitgezocht op 02-08-2026: hun webshop-ingang geeft
               wél het hele assortiment met de gewone winkelprijs, het merk, de
               inhoud en bij élk product een streepjescode. Dat is de bron voor
               de standaardprijzen-pagina.
 Datum       : 02-08-2026 11:30

 Let op: hier komen geen aanbiedingen vandaan, en dat kan ook niet. De ingang
 kent geen actieprijs of einddatum, en de folder bevat alleen drukwerk waarin
 productnamen en bedragen los van elkaar staan ("99 3." voor € 3,99).

 Onderdelen:
   haal_assortiment() - het hele assortiment plus de winkelindeling
   _vraag()           - stelt één vraag aan de webshop-ingang van Vomar
   _indeling()        - de drie lagen: afdeling, hoofdgroep, groep
   _inhoud_tekst()    - plakt "1000" en "gram" aan elkaar tot iets leesbaars
   _webadres()        - bouwt de link naar de productpagina op vomar.nl
===============================================================================
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import requests

from ..model import Assortiment, Standaardprijs, maak_standaardprijs

log = logging.getLogger(__name__)

WINKEL_ID = 5
WINKEL_NAAM = "Vomar"

# De webshop-ingang van Vomar zelf. Geen sleutel nodig; hij staat open en levert
# het hele assortiment in één antwoord.
_URL = "https://gateway.vomar.nl"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_KOPPEN = {
    "User-Agent": _USER_AGENT,
    "Accept": "application/json",
    "Origin": "https://www.vomar.nl",
    "Referer": "https://www.vomar.nl/",
}

# Ruim boven de ruim zesduizend producten die Vomar voert, zodat alles in één
# antwoord meekomt. Het antwoord vertelt zelf hoeveel producten er zijn; wijkt
# dat af, dan zegt het logboek dat.
_PAGINAGROOTTE = 100_000

_PRODUCT_URL = "https://www.vomar.nl/producten/{afdeling}/{hoofdgroep}/{naam}/{nummer}"
_AFBEELDING_URL = "https://d3vricquk1sjgf.cloudfront.net/{pad}?width=400&height=400&mode=fill"


class VomarFout(RuntimeError):
    """Het ophalen bij Vomar is niet gelukt."""


def _vraag(sessie: requests.Session, pad: str, **parameters: Any) -> dict[str, Any]:
    """Stelt één vraag aan de webshop-ingang van Vomar."""
    try:
        antwoord = sessie.get(
            f"{_URL}/{pad}", params=parameters or None, headers=_KOPPEN, timeout=90
        )
        antwoord.raise_for_status()
        inhoud = antwoord.json()
    except (requests.RequestException, ValueError) as fout:
        raise VomarFout(f"Kon Vomar niet bereiken ({pad}): {fout}") from fout

    if not isinstance(inhoud, dict):
        raise VomarFout(f"Vomar gaf een onverwacht antwoord bij {pad}.")

    return inhoud


def _indeling(sessie: requests.Session) -> dict[tuple[int, int, int], tuple[str, str, str]]:
    """
    De winkelindeling van Vomar: afdeling, hoofdgroep en groep.

    Vomar deelt dieper in dan de andere ketens: onder "Frisdrank, sappen, koffie
    & thee" en "Koffie, Cacao en Thee" zit nog "Koffiebonen". Die onderste laag
    is wat wij als productgroep tonen — hetzelfde niveau als de laden van Albert
    Heijn. Op de producten staan alleen de nummers van de drie lagen, dus deze
    lijst is nodig om er namen bij te vinden.
    """
    data = _vraag(sessie, "departments")

    paden: dict[tuple[int, int, int], tuple[str, str, str]] = {}
    for afdeling in data.get("departments") or []:
        afdeling_naam = (afdeling.get("departmentDescription") or "").strip()
        for hoofdgroep in afdeling.get("mainGroups") or []:
            hoofd_naam = (hoofdgroep.get("mainGroupDescription") or "").strip()
            for groep in hoofdgroep.get("subGroups") or []:
                sleutel = (
                    afdeling.get("departmentNumber"),
                    hoofdgroep.get("mainGroupNumber"),
                    groep.get("subGroupNumber"),
                )
                if None in sleutel:
                    continue
                paden[sleutel] = (
                    afdeling_naam, hoofd_naam, (groep.get("subGroupDescription") or "").strip()
                )

    if not paden:
        raise VomarFout("Vomar gaf geen winkelindeling terug.")

    return paden


def _slug(tekst: str | None) -> str:
    """Maakt van "Koffie, Cacao en Thee" het stukje "koffie-cacao-en-thee"."""
    if not tekst:
        return "-"
    schoon = unicodedata.normalize("NFKD", tekst.lower())
    schoon = "".join(teken for teken in schoon if not unicodedata.combining(teken))
    schoon = re.sub(r"[^a-z0-9]+", "-", schoon)
    return schoon.strip("-") or "-"


def _webadres(product: dict[str, Any], afdeling: str, hoofdgroep: str) -> str | None:
    """De link naar de productpagina op vomar.nl."""
    nummer = product.get("articleNumber")
    if not nummer:
        return None

    return _PRODUCT_URL.format(
        afdeling=_slug(afdeling),
        hoofdgroep=_slug(hoofdgroep),
        naam=_slug(product.get("description")),
        nummer=nummer,
    )


def _afbeelding(product: dict[str, Any]) -> str | None:
    """De productfoto staat op een aparte beeldserver."""
    for afbeelding in product.get("images") or []:
        pad = (afbeelding.get("fileName") or "").strip()
        if pad:
            return _AFBEELDING_URL.format(pad=pad)
    return None


def _inhoud_tekst(product: dict[str, Any]) -> str | None:
    """
    Plakt de losse inhoud en eenheid aan elkaar tot "1000 gram" of "6 stuks".

    Vomar levert die twee apart, waar de andere ketens er één tekst van maken.
    Staat er onzin in, dan blijft de inhoud leeg en krijgt het product geen
    kiloprijs — het verdwijnt daarmee niet, maar zakt naar onderen.
    """
    hoeveelheid = str(product.get("contents") or "").strip()
    eenheid = str(product.get("unit") or "").strip()
    if not hoeveelheid or not eenheid:
        return None
    return f"{hoeveelheid} {eenheid}"


def _bedrag(waarde: Any) -> float | None:
    """Een prijs van nul betekent "niet bekend", niet "gratis"."""
    try:
        bedrag = float(waarde)
    except (TypeError, ValueError):
        return None
    return bedrag if bedrag > 0 else None


def _naar_standaardprijs(
    product: dict[str, Any], paden: dict[tuple[int, int, int], tuple[str, str, str]]
) -> Standaardprijs:
    """Vertaalt één product van Vomar naar onze eigen vorm."""
    sleutel = (
        product.get("departmentWebShopNumber"),
        product.get("mainGroupWebShopNumber"),
        product.get("subGroupWebShopNumber"),
    )
    afdeling, hoofdgroep, groep = paden.get(sleutel, ("", "", ""))

    # De onderste laag is de productgroep. Kent Vomar het nummer niet in zijn
    # eigen indeling, dan is de hoofdgroep de terugval — liever iets grovers dan
    # een product zonder groep.
    productgroep = groep or hoofdgroep or None

    return maak_standaardprijs(
        winkel_id=WINKEL_ID,
        bron_id=str(product["articleNumber"]),
        product_naam=product.get("description") or "",
        prijs=_bedrag(product.get("price")),
        merk=(product.get("brand") or "").strip() or None,
        afdeling=afdeling or None,
        productgroep=productgroep,
        inhoud_tekst=_inhoud_tekst(product),
        ean=(product.get("primaryEan") or "").strip() or None,
        product_url=_webadres(product, afdeling, hoofdgroep),
        afbeelding_url=_afbeelding(product),
    )


def _goedkoopste(nieuw: Standaardprijs, bestaand: Standaardprijs | None) -> Standaardprijs:
    """
    Staat een artikelnummer twee keer in de lijst, dan houden we de laagste prijs.

    Vomar levert een handvol artikelnummers dubbel, soms met een verschillend
    bedrag (€ 2,49 naast € 2,69). Welke van de twee de kassa rekent weten we
    niet; de laagste tonen is dan de eerlijkste keuze naar de winkel toe.
    """
    if bestaand is None or bestaand.prijs is None:
        return nieuw
    if nieuw.prijs is None:
        return bestaand
    return nieuw if nieuw.prijs < bestaand.prijs else bestaand


def haal_assortiment() -> Assortiment:
    """
    Haalt het hele assortiment van Vomar op, plus zijn winkelindeling.

    Twee vragen zijn genoeg: één voor de indeling en één voor alle producten.
    Samen duurt dat ongeveer een seconde.

    Gaat één product mis, dan gaat het script door met de rest: liever een lijst
    die een enkel product mist dan helemaal geen lijst.
    """
    sessie = requests.Session()
    paden = _indeling(sessie)
    log.info(
        "%s: winkelindeling met %s groepen opgehaald.",
        WINKEL_NAAM, len({pad[2] for pad in paden.values() if pad[2]}),
    )

    data = _vraag(sessie, "products", pageSize=_PAGINAGROOTTE)
    ruwe_producten = data.get("products") or []

    gemeld = data.get("totalCount")
    if gemeld and len(ruwe_producten) < gemeld:
        log.warning(
            "%s: %s van de %s producten binnengekregen; de rest valt buiten deze ronde.",
            WINKEL_NAAM, len(ruwe_producten), gemeld,
        )

    gevonden: dict[str, Standaardprijs] = {}
    overgeslagen = 0
    dubbel = 0

    for product in ruwe_producten:
        if not product or not product.get("articleNumber") or not product.get("description"):
            overgeslagen += 1
            continue

        try:
            schapproduct = _naar_standaardprijs(product, paden)
        except (KeyError, TypeError, ValueError) as fout:
            log.warning(
                "Product %s van Vomar overgeslagen: %s", product.get("articleNumber"), fout
            )
            overgeslagen += 1
            continue

        if schapproduct.prijs is None:
            overgeslagen += 1
            continue

        if schapproduct.bron_id in gevonden:
            dubbel += 1
        gevonden[schapproduct.bron_id] = _goedkoopste(
            schapproduct, gevonden.get(schapproduct.bron_id)
        )

    if not gevonden:
        raise VomarFout("Vomar gaf geen enkel bruikbaar product terug.")

    zonder_kiloprijs = sum(1 for p in gevonden.values() if p.prijs_per_eenheid is None)
    zonder_groep = sum(1 for p in gevonden.values() if not p.productgroep)
    log.info(
        "%s: %s producten overgehouden van %s bekeken (%s overgeslagen, "
        "%s dubbel, %s zonder kiloprijs, %s zonder groep).",
        WINKEL_NAAM, len(gevonden), len(ruwe_producten), overgeslagen, dubbel,
        zonder_kiloprijs, zonder_groep,
    )

    groepen = sorted({pad[2] for pad in paden.values() if pad[2]})
    return Assortiment(list(gevonden.values()), groepen)
