"""
===============================================================================
 Dealbot — aanbiedingen ophalen bij Albert Heijn

 Versie      : 2.0
 Reden       : We zagen maar een deel van de bonus. De zoekingang van Albert
               Heijn laat niet verder kijken dan 3000 producten, terwijl er ruim
               17.000 in de bonus zitten; alles daarna viel buiten beeld. Zo
               ontbraken bijvoorbeeld alle koffiebonen. Voortaan lopen we de
               bonusfolder van de week af — die is per definitie compleet, want
               dat is precies wat de winkel aanbiedt.
 Datum       : 01-08-2026 14:07

 Onderdelen:
   haal_op()          - geeft alle weekaanbiedingen van de lopende bonusperiode
   _anoniem_token()   - haalt de tijdelijke toegangssleutel op
   _periode()         - de bonusweek waarin vandaag valt
   _segmenten()       - alle aanbiedingen (segmenten) uit de folder
   _producten()       - de producten die bij één aanbieding horen
   _is_weekaanbieding - houdt doorlopende online kortingen buiten de lijst
===============================================================================
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Iterator

import requests

from ..model import Aanbieding, maak_aanbieding

log = logging.getLogger(__name__)

WINKEL_ID = 1
WINKEL_NAAM = "Albert Heijn"

_TOKEN_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
_BASIS_URL = "https://api.ah.nl/mobile-services"
_METADATA_PAD = "bonuspage/v3/metadata"
_SEGMENT_PAD = "bonuspage/v1/segment"
_PRODUCT_URL = "https://www.ah.nl/producten/product/wi{webshop_id}"
_USER_AGENT = "Appie/8.22.3 Model/phone Android/6.0-API23"

_PAUZE_SECONDEN = 0.25     # rustig aan, we willen niet geblokkeerd worden
_POGINGEN = 3              # een tijdelijke blokkade mag de ronde niet slopen
_WACHT_NA_FOUT = 2.0

# Aanbiedingen van Gall & Gall en Etos staan in dezelfde folder, maar die koop
# je niet in de supermarkt. Alleen wat Albert Heijn zelf verkoopt telt mee.
_EIGEN_ACTIES = {"NATIONAL", "AHONLINE"}

# Boven dit aandeel mislukte onderdelen vertrouwen we de oogst niet meer en
# laten we liever de lijst van gisteren staan dan een halve lijst neer te zetten.
_MAX_MISLUKT_DEEL = 0.2

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


def _haal_json(
    sessie: requests.Session, koppen: dict[str, str], adres: str, **params: Any
) -> Any | None:
    """
    Haalt één stuk van de folder op, met een paar pogingen.

    Albert Heijn blokkeert af en toe kort (foutcode 403 of 429). Eén zo'n
    weigering hoort de hele ronde niet te bederven, dus we wachten even en
    proberen het opnieuw. Lukt het daarna nog niet, dan geeft deze functie niets
    terug en telt de aanroeper dat als mislukt onderdeel.
    """
    for poging in range(1, _POGINGEN + 1):
        try:
            antwoord = sessie.get(adres, params=params, headers=koppen, timeout=30)
        except requests.RequestException as fout:
            log.warning("Albert Heijn niet bereikbaar (%s), poging %s: %s", adres, poging, fout)
            time.sleep(_WACHT_NA_FOUT * poging)
            continue

        if antwoord.ok:
            try:
                return antwoord.json()
            except ValueError as fout:
                log.warning("Onleesbaar antwoord van Albert Heijn (%s): %s", adres, fout)
                return None

        if antwoord.status_code in (403, 429) or antwoord.status_code >= 500:
            log.warning(
                "Albert Heijn gaf foutcode %s (%s), poging %s van %s.",
                antwoord.status_code, adres, poging, _POGINGEN,
            )
            time.sleep(_WACHT_NA_FOUT * poging)
            continue

        log.warning("Albert Heijn gaf foutcode %s bij %s.", antwoord.status_code, adres)
        return None

    return None


def _periode(sessie: requests.Session, koppen: dict[str, str]) -> dict[str, Any]:
    """
    De bonusweek waarin vandaag valt.

    Albert Heijn toont tegen het eind van de week alvast de folder van volgende
    week. Die laten we links liggen: de aanbiedingenlijst hoort te gaan over wat
    je vandaag in de winkel kunt halen.
    """
    metadata = _haal_json(sessie, koppen, f"{_BASIS_URL}/{_METADATA_PAD}")
    periodes = (metadata or {}).get("periods") or []
    if not periodes:
        raise AlbertHeijnFout("Albert Heijn gaf geen bonusperiodes terug.")

    vandaag = date.today().isoformat()
    for periode in periodes:
        start = periode.get("bonusStartDate") or ""
        eind = periode.get("bonusEndDate") or ""
        if start <= vandaag <= eind:
            return periode

    log.warning("Geen bonusperiode gevonden voor vandaag; de eerste wordt gebruikt.")
    return periodes[0]


def _segmenten(
    sessie: requests.Session, koppen: dict[str, str], periode: dict[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    """
    Alle losse aanbiedingen ("segmenten") uit de folder van deze week.

    De folder is opgebouwd uit hoofdstukken ("Koffie, thee", "Vlees"), en elk
    hoofdstuk bevat aanbiedingen als "Alle Douwe Egberts, Senseo en L'OR".
    Achter zo'n aanbieding zitten de losse producten.

    Geeft de segmenten terug plus het aantal hoofdstukken dat niet gelukt is.
    """
    tabbladen = periode.get("tabs") or []
    alle_bonus = next(
        (t for t in tabbladen if "alle" in (t.get("description") or "").lower()),
        None,
    )
    if alle_bonus is None:
        raise AlbertHeijnFout("De bonusfolder van Albert Heijn had geen overzicht 'Alle Bonus'.")

    segmenten: dict[int, dict[str, Any]] = {}
    mislukt = 0

    for hoofdstuk in alle_bonus.get("urlMetadataList") or []:
        soort = (hoofdstuk.get("bonusType") or "").upper()
        pad = hoofdstuk.get("url") or ""
        if soort == "SPOTLIGHT":
            # Uitgelichte aanbiedingen staan verderop nog een keer in hun eigen
            # hoofdstuk; ze hier overslaan scheelt verzoeken.
            continue
        if "promotionType=" in pad and not any(f"promotionType={s}" in pad for s in _EIGEN_ACTIES):
            continue

        inhoud = _haal_json(sessie, koppen, f"{_BASIS_URL}/{pad}")
        if inhoud is None:
            log.warning("Hoofdstuk '%s' van de bonusfolder overgeslagen.", hoofdstuk.get("description"))
            mislukt += 1
            continue

        for regel in inhoud.get("bonusGroupOrProducts") or []:
            groep = regel.get("bonusGroup")
            if not groep or groep.get("future"):
                continue
            segment_id = groep.get("segmentId")
            if segment_id:
                segmenten[segment_id] = groep

        time.sleep(_PAUZE_SECONDEN)

    log.info(
        "  %s aanbiedingen in de folder van %s t/m %s.",
        len(segmenten), periode.get("bonusStartDate"), periode.get("bonusEndDate"),
    )
    return list(segmenten.values()), mislukt


def _producten(
    sessie: requests.Session,
    koppen: dict[str, str],
    segment: dict[str, Any],
    datum: str,
) -> list[dict[str, Any]] | None:
    """De losse producten die onder één aanbieding vallen."""
    inhoud = _haal_json(
        sessie, koppen, f"{_BASIS_URL}/{_SEGMENT_PAD}",
        segmentId=segment["segmentId"], date=datum,
    )
    if inhoud is None:
        return None
    return inhoud.get("products") or []


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


def _alle_producten(
    sessie: requests.Session,
    koppen: dict[str, str],
    segmenten: list[dict[str, Any]],
    datum: str,
) -> Iterator[dict[str, Any]]:
    """Loopt alle aanbiedingen langs en levert hun producten stuk voor stuk."""
    mislukt = 0

    for nummer, segment in enumerate(segmenten, start=1):
        producten = _producten(sessie, koppen, segment, datum)
        if producten is None:
            mislukt += 1
            log.warning(
                "Aanbieding '%s' overgeslagen.", segment.get("segmentDescription") or segment.get("segmentId")
            )
        else:
            yield from producten

        if nummer % 50 == 0:
            log.info("  %s van de %s aanbiedingen uitgelezen.", nummer, len(segmenten))
        time.sleep(_PAUZE_SECONDEN)

    if segmenten and mislukt / len(segmenten) > _MAX_MISLUKT_DEEL:
        raise AlbertHeijnFout(
            f"{mislukt} van de {len(segmenten)} aanbiedingen konden niet worden "
            "opgehaald; de oogst is te onvolledig om te vertrouwen."
        )


def haal_op() -> list[Aanbieding]:
    """
    Haalt alle weekaanbiedingen van Albert Heijn op uit de bonusfolder.

    Stopt met een foutmelding als de folder zelf niet te krijgen is of als een
    te groot deel ervan mislukt. Dat is met opzet: een halve lijst wegschrijven
    is erger dan de lijst van gisteren laten staan.
    """
    sessie = requests.Session()
    token = _anoniem_token(sessie)
    koppen = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
        "X-Application": "AHWEBSHOP",
    }

    periode = _periode(sessie, koppen)
    datum = periode.get("bonusStartDate") or date.today().isoformat()

    segmenten, hoofdstukken_mislukt = _segmenten(sessie, koppen, periode)
    if not segmenten:
        raise AlbertHeijnFout("De bonusfolder van Albert Heijn was leeg.")
    if hoofdstukken_mislukt:
        log.warning("%s hoofdstukken van de folder zijn niet gelukt.", hoofdstukken_mislukt)

    gevonden: dict[str, Aanbieding] = {}
    bekeken = 0

    for product in _alle_producten(sessie, koppen, segmenten, datum):
        bekeken += 1
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
