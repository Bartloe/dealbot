"""
===============================================================================
 Dealbot — aanbiedingen en schapprijzen ophalen bij Picnic

 Versie      : 1.0
 Reden       : Picnic is de zesde winkel. Hij heeft geen webwinkel en geen
               folder: zijn hele assortiment zit alleen in zijn app, achter een
               inlog met tweestapsverificatie. Dealbot gebruikt daarom een
               eenmaal geverifieerde sleutel (PICNIC_TOKEN) en loopt daarmee de
               winkel af zoals bij Albert Heijn: afdeling voor afdeling, lade
               voor lade.
 Datum       : 05-08-2026 12:10

 Eén ronde levert alles tegelijk: de aanbiedingen van deze week, de gewone
 schapprijzen én de winkelindeling. De winkel wordt daarom maar één keer
 afgelopen; het resultaat blijft binnen deze draai bewaard.

 Twee dingen zijn eigen aan deze bron:
   - Picnic antwoordt met een beschrijving van zijn app-scherm, niet met kale
     productgegevens. Een aanbieding is te herkennen aan het gele vlaggetje op
     de tegel; dáár staat ook de actietekst in ("1+1 gratis", "20% korting").
   - Een rode prijs is géén bewijs van een aanbieding: het label
     "Prijskampioen" — een blijvend lage prijs — is ook rood.

 Onderdelen:
   haal_op()            - de aanbiedingen van deze week plus de winkelindeling
   haal_assortiment()   - alle producten met hun gewone schapprijs
   _oogsten()           - loopt de winkel af; doet dat één keer per draai
   _afdelingen()        - de afdelingen (25) uit de zoekpagina
   _laden()             - de laden onder één afdeling
   _tegels()            - vist de producttegels uit een pagina
   _teksten()           - de teksten van één tegel, met kleur, maat en vlaggetje
   _uit_tegel()         - vertaalt één tegel naar productgegevens
   _week()              - de looptijd van een actie: maandag tot en met zondag
===============================================================================
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable, Iterator

import requests

from ..model import Aanbieding, Assortiment, Oogst, Standaardprijs, maak_aanbieding, maak_standaardprijs
from ..normalisatie import lees_inhoud

log = logging.getLogger(__name__)

WINKEL_ID = 7
WINKEL_NAAM = "Picnic"

_BASIS = "https://storefront-prod.nl.picnicinternational.com/api/15"

# De app-versie waarmee we ons melden. Zonder deze regels weigert Picnic.
_KOPPEN = {
    "User-Agent": "okhttp/4.9.0",
    "x-picnic-agent": "30100;1.15.232",
    "x-picnic-did": "3C417201548B2E3B",
}

# De sleutel komt uit de omgeving. Hij is niet met een wachtwoord alleen te
# maken: Picnic vraagt bij elke verse inlog om een code per sms of e-mail, en
# die kan een ochtendronde niet beantwoorden. Vandaar één keer met de hand
# verifiëren en de sleutel daarna bewaren.
_SLEUTEL_NAAM = "PICNIC_TOKEN"

# Kleuren waarmee Picnic zijn tegels opmaakt. Ze zijn de enige aanwijzing die
# hij geeft over wat een tekst betekent.
_VLAG = "#fbd92b"          # het gele vlaggetje: dit is een aanbieding
_OUDE_PRIJS = "rgba(0, 0, 0, 0.4)"   # de doorgestreepte prijs
_INHOUD = "#787570"        # de verpakking ("500 gram", maar ook "XL" en "NL")
_PRIJS_MAAT = 14           # de prijs staat altijd in deze tekstgrootte

# De lade "Acties" staat in elke afdeling en herhaalt wat er in de gewone laden
# al staat. Overslaan, anders krijgt een product "Acties" als productgroep.
_GEEN_GROEP = {"acties"}

_POGINGEN = 3
_WACHT_NA_FOUT = 2.0

# Picnic zet de deur even op slot als er te snel achter elkaar wordt gevraagd:
# een kale 403-pagina, ongeveer een halve minuut lang. Vandaar een korte pauze
# tussen twee vragen, en flink wachten als het tóch gebeurt.
_PAUZE = 0.4
_WACHT_BIJ_REM = (20.0, 40.0, 80.0)

# Mislukt meer dan dit deel van de laden, dan is de oogst niet te vertrouwen en
# blijft de lijst van gisteren liever staan.
_MAX_MISLUKT = 0.2

_GETAL = re.compile(r"^\d+(?:[.,]\d{1,2})?$")
_KLEURCODE = re.compile(r"#\(#[0-9a-fA-F]{3,8}\)")
_L1 = re.compile(r"id=L1-category-page-root,category_id=([\w-]+)")
_L2 = re.compile(r"id=L2-category-page-root,category_id=([\w-]+)")


class PicnicFout(RuntimeError):
    """Het ophalen bij Picnic is niet gelukt."""


@dataclass(frozen=True)
class _Tekst:
    """Eén stukje tekst van een tegel, met wat de opmaak erover zegt."""

    tekst: str
    kleur: str | None
    maat: int | None
    op_vlaggetje: bool


@dataclass
class _Product:
    """Wat er van één producttegel te lezen valt."""

    bron_id: str
    naam: str
    merk: str | None
    productgroep: str
    afdeling: str
    prijs: float
    oude_prijs: float | None
    actie_tekst: str | None
    inhoud_tekst: str | None
    afbeelding_url: str | None

    @property
    def is_aanbieding(self) -> bool:
        return self.actie_tekst is not None


# Eén ronde levert zowel de aanbiedingen als de schapprijzen. De winkel aflopen
# kost ruim driehonderd verzoeken, dus dat gebeurt één keer per draai en het
# resultaat blijft hier staan.
_geheugen: tuple[list[_Product], list[str]] | None = None


def _sleutel() -> str:
    """De bewaarde sleutel, of een melding die vertelt wat er moet gebeuren."""
    sleutel = (os.environ.get(_SLEUTEL_NAAM) or "").strip()
    if not sleutel:
        raise PicnicFout(
            f"{_SLEUTEL_NAAM} ontbreekt. Picnic laat alleen ingelogde gebruikers "
            "toe en vraagt bij elke verse inlog om een code; de sleutel moet dus "
            "één keer met de hand worden aangemaakt."
        )
    return sleutel


def _is_sleutelfout(antwoord: requests.Response) -> bool:
    """
    Weigert Picnic ons vanwege de sleutel, of houdt hij ons alleen even tegen?

    Het verschil zit in de vorm van het antwoord. Een inhoudelijke weigering
    komt van de ingang zelf en is netjes verpakt ("AUTH_INVALID_CRED"). De
    snelheidsrem komt van de portier ervoor en stuurt een kale webpagina terug.
    Dat onderscheid telt: een sleutelprobleem lost zichzelf nooit op, een rem
    wel.
    """
    if not antwoord.headers.get("content-type", "").startswith("application/json"):
        return False
    try:
        code = ((antwoord.json() or {}).get("error") or {}).get("code") or ""
    except ValueError:
        return False
    return code.startswith("AUTH") or "FACTOR" in code


def _vraag(sessie: requests.Session, pad: str) -> dict[str, Any]:
    """
    Stelt één vraag aan de app-ingang van Picnic, met een paar pogingen.

    Een verlopen sleutel krijgt een eigen melding: dat is geen storing die
    morgen vanzelf over is, maar iets wat met de hand hersteld moet worden.
    """
    laatste = ""

    for poging in range(1, _POGINGEN + 1):
        time.sleep(_PAUZE)
        try:
            antwoord = sessie.get(f"{_BASIS}/{pad}", timeout=60)
        except requests.RequestException as fout:
            laatste = str(fout)
            log.warning("Picnic niet bereikbaar (%s), poging %s van %s: %s",
                        pad, poging, _POGINGEN, fout)
            time.sleep(_WACHT_NA_FOUT * poging)
            continue

        if antwoord.status_code in (401, 403) and _is_sleutelfout(antwoord):
            raise PicnicFout(
                f"Picnic laat ons niet meer binnen ({antwoord.status_code}). De "
                f"sleutel {_SLEUTEL_NAAM} is verlopen of ingetrokken; er moet "
                "opnieuw met een code worden ingelogd."
            )

        if antwoord.status_code in (403, 429):
            wacht = _WACHT_BIJ_REM[min(poging, len(_WACHT_BIJ_REM)) - 1]
            laatste = "de snelheidsrem van Picnic"
            log.info("Picnic remt ons af; %.0f seconden wachten (poging %s van %s).",
                     wacht, poging, _POGINGEN)
            time.sleep(wacht)
            continue

        if antwoord.ok:
            try:
                inhoud = antwoord.json()
            except ValueError as fout:
                raise PicnicFout(f"Picnic gaf een onleesbaar antwoord bij {pad}.") from fout
            if not isinstance(inhoud, dict):
                raise PicnicFout(f"Picnic gaf een onverwacht antwoord bij {pad}.")
            return inhoud

        laatste = f"foutcode {antwoord.status_code}"
        log.warning("Picnic gaf %s bij %s, poging %s van %s.",
                    antwoord.status_code, pad, poging, _POGINGEN)
        time.sleep(_WACHT_NA_FOUT * poging)

    raise PicnicFout(f"Kon {pad} niet ophalen bij Picnic ({laatste}).")


def _titel(pagina: dict[str, Any]) -> str:
    """De naam van een afdeling of lade, zoals die boven het scherm staat."""
    return ((pagina.get("header") or {}).get("title") or "").strip()


def _schoon(markdown: str) -> str:
    """Haalt de kleurcodes en onzichtbare tekens uit een stukje opmaaktaal."""
    return _KLEURCODE.sub("", markdown).replace("​", "").replace("**", "").strip()


def _wandel(knoop: Any) -> Iterator[dict[str, Any]]:
    """Loopt elke tak van een pagina langs."""
    if isinstance(knoop, dict):
        yield knoop
        for waarde in knoop.values():
            yield from _wandel(waarde)
    elif isinstance(knoop, list):
        for waarde in knoop:
            yield from _wandel(waarde)


def _verwijzingen(pagina: dict[str, Any], patroon: re.Pattern[str]) -> list[str]:
    """De nummers achter alle doorverwijzingen van één soort, zonder dubbele."""
    gevonden: list[str] = []
    for knoop in _wandel(pagina):
        doel = knoop.get("target")
        if not isinstance(doel, str):
            continue
        gevonden.extend(patroon.findall(doel))

    gezien: set[str] = set()
    return [nummer for nummer in gevonden
            if not (nummer in gezien or gezien.add(nummer))]


def _tegels(pagina: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """
    Vist de producttegels uit een pagina.

    Picnic hangt bij elke tegel een blokje voor de schermlezer, met het
    productnummer en de naam erin. Het blok waar dat in zit, is de tegel zelf —
    daar staan de prijs, het merk en de verpakking in.
    """
    gevonden: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def loop(knoop: Any, ouder: dict[str, Any] | None) -> None:
        if isinstance(knoop, dict):
            if knoop.get("contentType") == "SELLING_UNIT" and ouder is not None:
                gevonden.append((knoop, ouder))
            for waarde in knoop.values():
                loop(waarde, knoop)
        elif isinstance(knoop, list):
            for waarde in knoop:
                loop(waarde, ouder)

    loop(pagina, None)
    return gevonden


def _teksten(tegel: dict[str, Any]) -> list[_Tekst]:
    """
    Alle teksten van één tegel, met kleur, tekstgrootte en het gele vlaggetje.

    Picnic geeft niet mee wat een tekst betékent; de opmaak is de enige
    aanwijzing. Daarom gaat die hier mee naar boven.
    """
    uit: list[_Tekst] = []

    def loop(knoop: Any, op_vlaggetje: bool) -> None:
        if isinstance(knoop, dict):
            geel = op_vlaggetje or knoop.get("backgroundColor") == _VLAG
            inhoud = knoop.get("markdown")
            if isinstance(inhoud, str):
                schoon = _schoon(inhoud)
                if schoon:
                    opmaak = knoop.get("textAttributes") or {}
                    uit.append(_Tekst(schoon, opmaak.get("color"), opmaak.get("size"), geel))
            for waarde in knoop.values():
                loop(waarde, geel)
        elif isinstance(knoop, list):
            for waarde in knoop:
                loop(waarde, op_vlaggetje)

    loop(tegel, False)
    return uit


def _bedrag(tekst: str) -> float | None:
    """Zet "10.79" om naar een bedrag; alles wat geen getal is valt af."""
    if not _GETAL.match(tekst):
        return None
    try:
        waarde = float(tekst.replace(",", "."))
    except ValueError:
        return None
    return waarde if waarde > 0 else None


def _merk(kaart: dict[str, Any], naam: str) -> str | None:
    """
    Het merk, uit het blokje voor de schermlezer ("Intens koffiebonen, van
    Douwe Egberts"). Op de tegel zelf staat het merk zonder enig kenmerk tussen
    de andere teksten, en dan is het niet van een smaakomschrijving te
    onderscheiden.

    Bij onverpakte groente en fruit zet Picnic de herkomst in dat veld ("Uit
    Nederland"). Dat is geen merk, en het zou het koppelen van hetzelfde product
    tussen winkels in de weg zitten: de sleutel waarop dat gebeurt is merk plus
    productnaam, en dan vindt "Uit Nederland aardbeien" de aardbeien van Albert
    Heijn niet meer.
    """
    label = ((kaart.get("unavailableAccessibility") or {}).get("accessibilityLabel") or "")
    _, scheiding, merk = label.partition(", van ")
    if not scheiding:
        return None

    merk = merk.strip()
    if not merk or merk.lower() == naam.lower() or merk.lower().startswith("uit "):
        return None
    return merk


def _afbeelding(tegel: dict[str, Any]) -> str | None:
    """De productfoto. Het plaatje van de tegelachtergrond blijft eruit."""
    for knoop in _wandel(tegel):
        if knoop.get("id") != "selling-unit-image":
            continue
        for onder in _wandel(knoop):
            nummer = (onder.get("source") or {}).get("id")
            if isinstance(nummer, str) and "/" not in nummer:
                return f"{_BASIS.rsplit('/api/', 1)[0]}/static/images/{nummer}/medium.png"
    return None


def _uit_tegel(
    kaart: dict[str, Any], tegel: dict[str, Any], afdeling: str, groep: str
) -> _Product | None:
    """
    Vertaalt één producttegel naar productgegevens.

    Geeft niets terug als er geen prijs of geen naam op staat; zo'n tegel is een
    plaatje of een verwijzing, geen product.
    """
    nummer = kaart.get("sellingUnitId")
    naam = (kaart.get("productName") or "").strip()
    if not nummer or not naam:
        return None

    teksten = _teksten(tegel)

    prijs = next((_bedrag(t.tekst) for t in teksten
                  if t.maat == _PRIJS_MAAT and _bedrag(t.tekst) is not None), None)
    if prijs is None:
        return None

    oude_prijs = next((_bedrag(t.tekst) for t in teksten
                       if t.kleur == _OUDE_PRIJS and _bedrag(t.tekst) is not None), None)

    # Het gele vlaggetje maakt van een tegel een aanbieding, en draagt de
    # actietekst bij zich. Zonder vlaggetje is het gewoon de schapprijs.
    actie_tekst = next((t.tekst for t in teksten if t.op_vlaggetje), None)

    # Onder de verpakking staan ook losse kreten ("XL", "NL"); we nemen de
    # eerste die als hoeveelheid te lezen is.
    inhoud_tekst = next((t.tekst for t in teksten
                         if t.kleur == _INHOUD and lees_inhoud(t.tekst)), None)

    return _Product(
        bron_id=str(nummer),
        naam=naam,
        merk=_merk(kaart, naam),
        productgroep=groep,
        afdeling=afdeling,
        prijs=prijs,
        oude_prijs=oude_prijs,
        actie_tekst=actie_tekst,
        inhoud_tekst=inhoud_tekst,
        afbeelding_url=_afbeelding(tegel),
    )


def _afdelingen(sessie: requests.Session) -> list[str]:
    """De nummers van de afdelingen, zoals ze op de zoekpagina staan."""
    pagina = _vraag(sessie, "pages/search-page-root")
    nummers = _verwijzingen(pagina, _L1)
    if not nummers:
        raise PicnicFout("Picnic gaf geen enkele afdeling terug.")
    return nummers


def _laden(sessie: requests.Session, afdeling: str) -> tuple[str, list[str]]:
    """De naam van een afdeling en de nummers van de laden eronder."""
    pagina = _vraag(sessie, f"pages/L1-category-page-root?category_id={afdeling}")
    return _titel(pagina), _verwijzingen(pagina, _L2)


def _oogsten(voortgang: Callable[[str], None] | None = None) -> tuple[list[_Product], list[str]]:
    """
    Loopt de hele winkel af: elke afdeling, elke lade, elk product.

    Dat kost ruim driehonderd verzoeken en een minuut of vijf, maar levert in
    één keer de aanbiedingen, de schapprijzen én de winkelindeling. Een lade die
    stukloopt slaan we over; loopt meer dan een vijfde stuk, dan is de oogst niet
    te vertrouwen en houden we ermee op.
    """
    global _geheugen
    if _geheugen is not None:
        return _geheugen

    sessie = requests.Session()
    sessie.headers.update(_KOPPEN)
    sessie.headers["x-picnic-auth"] = _sleutel()

    afdelingen = _afdelingen(sessie)
    log.info("%s: %s afdelingen gevonden.", WINKEL_NAAM, len(afdelingen))

    producten: dict[str, _Product] = {}
    groepen: list[str] = []
    bekeken = 0
    mislukt = 0
    dubbel = 0

    for nummer in afdelingen:
        try:
            afdeling, laden = _laden(sessie, nummer)
        except PicnicFout as fout:
            log.warning("Afdeling %s van Picnic overgeslagen: %s", nummer, fout)
            mislukt += 1
            continue

        for lade in laden:
            bekeken += 1
            try:
                pagina = _vraag(sessie, f"pages/L2-category-page-root?category_id={lade}")
            except PicnicFout as fout:
                log.warning("Lade %s van Picnic overgeslagen: %s", lade, fout)
                mislukt += 1
                continue

            groep = _titel(pagina)
            if not groep or groep.lower() in _GEEN_GROEP:
                continue
            if groep not in groepen:
                groepen.append(groep)

            for kaart, tegel in _tegels(pagina):
                try:
                    product = _uit_tegel(kaart, tegel, afdeling, groep)
                except (KeyError, TypeError, ValueError) as fout:
                    log.warning("Product %s van Picnic overgeslagen: %s",
                                kaart.get("sellingUnitId"), fout)
                    continue
                if product is None:
                    continue
                if product.bron_id in producten:
                    dubbel += 1
                    # Een product kan in twee laden liggen. De eerste plek wint,
                    # behalve als de tweede wél een aanbieding blijkt.
                    if not product.is_aanbieding:
                        continue
                producten[product.bron_id] = product

            if voortgang and bekeken % 25 == 0:
                voortgang(f"{bekeken} laden bekeken, {len(producten)} producten")

    if bekeken and mislukt / max(bekeken, 1) > _MAX_MISLUKT:
        raise PicnicFout(
            f"{mislukt} van de {bekeken} laden bij Picnic liepen stuk; "
            "de oogst is niet compleet genoeg om weg te schrijven."
        )
    if not producten:
        raise PicnicFout("Picnic gaf geen enkel product terug.")

    log.info(
        "%s: %s laden bekeken, %s producten (%s in de aanbieding, %s dubbel, %s mislukt).",
        WINKEL_NAAM, bekeken, len(producten),
        sum(1 for p in producten.values() if p.is_aanbieding), dubbel, mislukt,
    )

    _geheugen = (list(producten.values()), groepen)
    return _geheugen


def _week() -> tuple[str, str]:
    """
    De looptijd van een actie bij Picnic: maandag tot en met zondag.

    Picnic zet elke maandagochtend nieuwe acties klaar die tot zondagavond
    gelden, en geeft bij een aanbieding zelf geen datums mee. Deze week is dus
    afgeleid, niet afgelezen.
    """
    vandaag = date.today()
    maandag = vandaag - timedelta(days=vandaag.weekday())
    return maandag.isoformat(), (maandag + timedelta(days=6)).isoformat()


def _naar_aanbieding(product: _Product, van: str, tot: str) -> Aanbieding:
    """
    Vertaalt een product met vlaggetje naar een aanbieding.

    Twee soorten acties, en het verschil bepaalt hoe de prijs telt. Staat er een
    doorgestreepte prijs bij, dan is de prijs op de tegel de actieprijs. Anders
    is het een voorwaardelijke actie ("1+1 gratis", "2 voor €5") en is de prijs
    op de tegel de gewone prijs; wat je per stuk betaalt rekent Dealbot zelf uit
    aan de hand van de actietekst.
    """
    verlaagd = product.oude_prijs is not None

    return maak_aanbieding(
        winkel_id=WINKEL_ID,
        bron_id=product.bron_id,
        product_naam=product.naam,
        merk=product.merk,
        productgroep=product.productgroep,
        actie_tekst=product.actie_tekst,
        actieprijs=product.prijs if verlaagd else None,
        normale_prijs=product.oude_prijs if verlaagd else product.prijs,
        inhoud_tekst=product.inhoud_tekst,
        geldig_van=van,
        geldig_tot=tot,
        afbeelding_url=product.afbeelding_url,
    )


def haal_op() -> Oogst:
    """
    Haalt alle aanbiedingen op die deze week bij Picnic lopen.

    Picnic publiceert geen folder en geen actiepagina met datums: de acties zijn
    te herkennen aan het gele vlaggetje op de producttegel. Ze lopen van maandag
    tot en met zondag.
    """
    producten, groepen = _oogsten()
    van, tot = _week()

    aanbiedingen = [_naar_aanbieding(product, van, tot)
                    for product in producten if product.is_aanbieding]

    if not aanbiedingen:
        raise PicnicFout("Picnic had deze ronde geen enkele aanbieding.")

    zonder_kiloprijs = sum(1 for a in aanbiedingen if a.prijs_per_eenheid is None)
    log.info(
        "%s: %s aanbiedingen, waarvan %s zonder kiloprijs; %s productgroepen.",
        WINKEL_NAAM, len(aanbiedingen), zonder_kiloprijs, len(groepen),
    )

    return Oogst(aanbiedingen, groepen)


def haal_assortiment() -> Assortiment:
    """
    Haalt alle producten van Picnic op met hun gewone schapprijs.

    Komt uit dezelfde ronde als de aanbiedingen. Producten die deze week in de
    actie liggen krijgen hier bewust hun gewóne prijs mee: op de
    standaardprijzen-pagina hoort te staan wat iets kost als er geen actie is.
    Bij een verlaagde prijs is dat de doorgestreepte prijs.
    """
    producten, _ = _oogsten()

    schap: list[Standaardprijs] = []
    for product in producten:
        schap.append(maak_standaardprijs(
            winkel_id=WINKEL_ID,
            bron_id=product.bron_id,
            product_naam=product.naam,
            prijs=product.oude_prijs if product.oude_prijs is not None else product.prijs,
            merk=product.merk,
            afdeling=product.afdeling,
            productgroep=product.productgroep,
            inhoud_tekst=product.inhoud_tekst,
            afbeelding_url=product.afbeelding_url,
        ))

    zonder_kiloprijs = sum(1 for p in schap if p.prijs_per_eenheid is None)
    log.info(
        "%s: %s schapprijzen, waarvan %s zonder kiloprijs.",
        WINKEL_NAAM, len(schap), zonder_kiloprijs,
    )

    # De winkelindeling gaat hier bewust niet mee: die staat al in de Oogst van
    # haal_op(), en van daaruit komt hij in de keuzelijst van het profielscherm.
    return Assortiment(schap, [])
