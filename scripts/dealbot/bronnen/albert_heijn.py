"""
===============================================================================
 Dealbot — aanbiedingen ophalen bij Albert Heijn

 Versie      : 1.1
 Reden       : De productgroep van Albert Heijn (subCategory) gaat nu naar het
               veld "productgroep" in plaats van "variant" — zelfde gegeven,
               eerlijke naam.
 Datum       : 31-07-2026 01:12

 Onderdelen:
   haal_op()          - geeft alle actuele weekaanbiedingen terug
   _anoniem_token()   - haalt de tijdelijke toegangssleutel op
   _is_weekaanbieding - houdt doorlopende online kortingen buiten de lijst
===============================================================================
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterator

import requests

from ..model import Aanbieding, maak_aanbieding

log = logging.getLogger(__name__)

WINKEL_ID = 1
WINKEL_NAAM = "Albert Heijn"

_TOKEN_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
_ZOEK_URL = "https://api.ah.nl/mobile-services/product/search/v2"
_PRODUCT_URL = "https://www.ah.nl/producten/product/wi{webshop_id}"
_USER_AGENT = "Appie/8.22.3 Model/phone Android/6.0-API23"

_PAGINA_GROOTTE = 100
_MAX_PAGINAS = 30          # verder bladeren staat Albert Heijn niet toe
_PAUZE_SECONDEN = 0.4      # rustig aan, we willen niet geblokkeerd worden

# Doorlopende online kortingen (multipacks) krijgen deze einddatum mee. Het zijn
# geen weekaanbiedingen en ze zouden de lijst overspoelen.
_EINDDATUM_ONBEPAALD = "2999"


class AlbertHeijnFout(RuntimeError):
    """Het ophalen bij Albert Heijn is niet gelukt."""


def _anoniem_token(sessie: requests.Session) -> str:
    """Haalt een tijdelijke toegangssleutel op; die is een week geldig."""
    try:
        antwoord = sessie.post(
            _TOKEN_URL,
            json={"clientId": "appie"},
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
        )
        antwoord.raise_for_status()
        return antwoord.json()["access_token"]
    except (requests.RequestException, KeyError, ValueError) as fout:
        raise AlbertHeijnFout(
            f"Kon geen toegangssleutel krijgen bij Albert Heijn: {fout}"
        ) from fout


def _is_weekaanbieding(product: dict[str, Any]) -> bool:
    """
    Alleen echte aanbiedingen van deze week doorlaten.

    Albert Heijn zet ook permanente staffelkortingen op multipacks in dezelfde
    lijst ("10% volume voordeel", einddatum in het jaar 2999). Die horen niet in
    een wekelijkse aanbiedingenlijst thuis.
    """
    if not product.get("isBonus"):
        return False
    if product.get("isInfiniteBonus"):
        return False

    einddatum = product.get("bonusEndDate")
    if not einddatum or einddatum.startswith(_EINDDATUM_ONBEPAALD):
        return False

    return True


def _paginas(sessie: requests.Session, token: str) -> Iterator[list[dict[str, Any]]]:
    """Bladert door de bonuslijst tot er niets nieuws meer komt."""
    koppen = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
        "X-Application": "AHWEBSHOP",
    }

    for paginanummer in range(_MAX_PAGINAS):
        try:
            antwoord = sessie.get(
                _ZOEK_URL,
                params={
                    "query": "",
                    "filters": "bonus=true",
                    "size": _PAGINA_GROOTTE,
                    "page": paginanummer,
                },
                headers=koppen,
                timeout=30,
            )
        except requests.RequestException as fout:
            log.warning("Pagina %s van Albert Heijn mislukt: %s", paginanummer, fout)
            return

        if antwoord.status_code == 400:
            log.info("Albert Heijn laat niet verder bladeren dan pagina %s.", paginanummer)
            return
        if not antwoord.ok:
            log.warning(
                "Pagina %s van Albert Heijn gaf foutcode %s.",
                paginanummer, antwoord.status_code,
            )
            return

        try:
            producten = antwoord.json().get("products", [])
        except ValueError as fout:
            log.warning("Onleesbaar antwoord van Albert Heijn: %s", fout)
            return

        if not producten:
            return

        yield producten
        time.sleep(_PAUZE_SECONDEN)


def _naar_aanbieding(product: dict[str, Any]) -> Aanbieding:
    """Vertaalt één product van Albert Heijn naar onze eigen vorm."""
    afbeeldingen = product.get("images") or []
    afbeelding = None
    if afbeeldingen:
        # De middelste maat is groot genoeg voor de website en blijft klein.
        gesorteerd = sorted(afbeeldingen, key=lambda a: a.get("width") or 0)
        afbeelding = gesorteerd[len(gesorteerd) // 2].get("url")

    return maak_aanbieding(
        winkel_id=WINKEL_ID,
        bron_id=str(product["webshopId"]),
        product_naam=product.get("title") or "",
        merk=product.get("brand"),
        productgroep=product.get("subCategory"),
        actie_tekst=product.get("bonusMechanism"),
        actieprijs=product.get("currentPrice"),
        normale_prijs=product.get("priceBeforeBonus"),
        inhoud_tekst=product.get("salesUnitSize"),
        geldig_van=product.get("bonusStartDate"),
        geldig_tot=product.get("bonusEndDate"),
        product_url=_PRODUCT_URL.format(webshop_id=product["webshopId"]),
        afbeelding_url=afbeelding,
    )


def haal_op() -> list[Aanbieding]:
    """
    Haalt alle actuele weekaanbiedingen van Albert Heijn op.

    Geeft een lege lijst terug als er niets te halen valt; alleen als de
    toegangssleutel al niet lukt, stopt het met een foutmelding, want dan is er
    iets structureel mis.
    """
    sessie = requests.Session()
    token = _anoniem_token(sessie)

    gevonden: dict[str, Aanbieding] = {}
    bekeken = 0

    for producten in _paginas(sessie, token):
        bekeken += len(producten)
        for product in producten:
            if not _is_weekaanbieding(product):
                continue
            if not product.get("title") or not product.get("webshopId"):
                continue
            try:
                aanbieding = _naar_aanbieding(product)
            except (KeyError, TypeError, ValueError) as fout:
                log.warning(
                    "Product %s van Albert Heijn overgeslagen: %s",
                    product.get("webshopId"), fout,
                )
                continue
            gevonden[aanbieding.bron_id] = aanbieding

    zonder_kiloprijs = sum(1 for a in gevonden.values() if a.prijs_per_eenheid is None)
    log.info(
        "%s: %s producten bekeken, %s weekaanbiedingen overgehouden "
        "(%s zonder kiloprijs).",
        WINKEL_NAAM, bekeken, len(gevonden), zonder_kiloprijs,
    )

    return list(gevonden.values())
