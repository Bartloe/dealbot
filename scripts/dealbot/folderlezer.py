"""
===============================================================================
 Dealbot — een digitale folder uitlezen met behulp van AI

 Versie      : 1.1
 Reden       : De geldigheidsperiode ging mis op de eerste echte folder. Die van
               Vomar staat vol pagina's met alleen weekendacties ("donderdag 6
               t/m zaterdag 8"), en dat zijn er meer dan de ene omslag met de
               echte looptijd. Elke pagina houdt nu zijn eigen periode; de folder
               als geheel loopt van de vroegste tot de laatste dag.
 Reden (1.0) : Sommige ketens publiceren hun aanbiedingen alleen als folder.
               In zo'n PDF staan productnamen en bedragen los van elkaar over
               de plaatjes heen ("99 3." voor € 3,99), dus met gewone code is er
               niets van te maken. Een AI die naar de pagina kíjkt wél. Deze
               module doet dat voor elke keten hetzelfde: pagina's maken,
               laten aflezen en er onze eigen aanbiedingen van maken.
 Datum       : 03-08-2026 10:55

 Twee valkuilen zitten er ingebakken, allebei gezien in de folder van Vomar:
   1. De doorgestreepte prijs bij "1+1 gratis" is de prijs van twéé stuks
      (7,58 doorgestreept, 3,79 groot, terwijl één pak gewoon 3,79 is). Daarom
      vraagt de AI niet om een uitgerekende stuksprijs, maar om het bedrag én
      voor hoeveel stuks dat geldt. Het rekenwerk doen wij; AI's rekenen slecht.
   2. Het paginanummer dat in de folder gedrukt staat is niet het nummer van de
      pagina in het bestand (blad 1 van de PDF droeg nummer 32). Wij tellen zelf.

 Onderdelen:
   Folderoogst        - de aanbiedingen uit één folder, met de geldigheidsperiode
   paginas_uit_pdf()  - maakt van elk blad een afbeelding, zonder extra software
   lees_folder()      - de hele folder langs, pagina voor pagina
   _naar_aanbieding() - één afgelezen artikel naar onze eigen vorm
   _stuksprijs()      - het bedrag omrekenen naar de prijs voor één stuk
   _folderperiode()   - van de vroegste tot de laatste dag die er gelezen is
===============================================================================
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date

from .ai import Vraagbaak
from .model import Aanbieding, maak_aanbieding

log = logging.getLogger(__name__)

# Hoe scherp de pagina's worden. 150 dpi is ruim genoeg om de kleine centen
# boven de grote euro's te lezen en houdt een pagina rond de 300 kB.
SCHAAL = 150 / 72

# Boven deze breedte gaat er alleen maar tijd en geld in zitten zonder dat de
# AI het beter gaat lezen.
MAX_BREEDTE = 1600

# De vorm waarin de AI moet antwoorden. Hiermee kan hij geen proza terugsturen
# waar wij bedragen verwachten.
ANTWOORDVORM = {
    "type": "object",
    "properties": {
        "geldig_van": {"type": "string",
                       "description": "Begindatum van de acties als 2026-08-02, of leeg"},
        "geldig_tot": {"type": "string",
                       "description": "Einddatum van de acties als 2026-08-08, of leeg"},
        "artikelen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_naam": {"type": "string"},
                    "merk": {"type": "string"},
                    "inhoud": {"type": "string"},
                    "normale_prijs": {"type": "number"},
                    "actie_bedrag": {"type": "number"},
                    "bedrag_geldt_voor_aantal": {"type": "integer"},
                    "actie_tekst": {"type": "string"},
                    "alleen_met_app": {"type": "boolean"},
                },
                "required": ["product_naam", "actie_tekst", "bedrag_geldt_voor_aantal"],
            },
        },
    },
    "required": ["artikelen"],
}

OPDRACHT = """\
Je kijkt naar één pagina uit de papieren weekfolder van supermarkt {winkel}.
Schrijf alle aanbiedingen op die op deze pagina staan. Vandaag is het {vandaag}.

Zo lees je de prijzen:
- De centen zweven vaak klein rechtsboven het grote eurogetal: een grote 3 met een
  kleine 79 is 3.79.
- Een doorgestreept bedrag is de normale prijs, het grote gekleurde bedrag is de
  actieprijs.
- LET OP bij "1+1 gratis" en "2e halve prijs": het grote bedrag geldt daar meestal
  voor het hele pakket (twee stuks). Zet dan bedrag_geldt_voor_aantal op 2.
  Bij "2 voor 5.00" zet je bedrag_geldt_voor_aantal op 2 en actie_bedrag op 5.00.
  Bij een gewone prijs per stuk of per pak is bedrag_geldt_voor_aantal gewoon 1.
- Reken zelf niets uit en verzin geen bedragen. Staat er geen prijs, laat het veld
  dan leeg.

Verder:
- inhoud: neem letterlijk over wat er staat, bijvoorbeeld "pak 500 gram",
  "2 flessen a 1 liter", "per stuk", "alle soorten".
- actie_tekst: de actie zoals hij er staat, bijvoorbeeld "1+1 gratis",
  "2e halve prijs", "tot 58% korting", "per pak".
- alleen_met_app: alleen waar als er uitdrukkelijk staat dat de korting via de app
  of de klantenkaart moet worden geactiveerd.
- geldig_van en geldig_tot: alleen invullen als de geldigheidsperiode op deze
  pagina staat ("geldig van zondag 2 t/m zaterdag 8 augustus"). Gebruik hele
  datums met jaartal.

Staat er een keuzelijst bij één prijs ("Kies & Mix", "keuze uit", gevolgd door
een opsomming), schrijf dan elk genoemd product apart op, elk met diezelfde prijs
en actie. Iemand zoekt namelijk op "nectarines", niet op "zomerfruit".

Sla over, dit zijn géén aanbiedingen:
- Prijsvergelijkingen met andere supermarkten: pagina's met kassabonnen naast
  elkaar, of lange lijstjes met gewone winkelprijzen om te laten zien dat deze
  winkel goedkoper is. Ook al staan er tientallen producten met bedragen op.
- Sfeerteksten, winkeladressen, openingstijden, recepten, vacatures, spaaracties
  en winacties.
"""


@dataclass
class Folderoogst:
    """De aanbiedingen uit één folder, met de periode waarin ze gelden."""

    aanbiedingen: list[Aanbieding] = field(default_factory=list)
    geldig_van: str | None = None
    geldig_tot: str | None = None
    paginas: int = 0
    gelezen: int = 0                          # pagina's die een antwoord opleverden
    fouten: list[str] = field(default_factory=list)


def paginas_uit_pdf(pdf: bytes, eerste: int = 1, laatste: int = 0) -> list[bytes]:
    """
    Maakt van elk blad van de PDF een afbeelding (JPEG).

    Hiervoor is met opzet pypdfium2 gekozen en niet poppler: dat is een gewoon
    pakket dat met pip meekomt, dus het werkt op de laptop én op GitHub zonder
    dat er losse programma's naast geïnstalleerd hoeven te worden.
    """
    try:
        import pypdfium2
    except ImportError as fout:  # pragma: no cover - alleen bij een kale installatie
        raise RuntimeError(
            "De bibliotheek pypdfium2 is niet geïnstalleerd; zonder die bibliotheek "
            "is een folder niet in pagina's op te delen."
        ) from fout

    document = pypdfium2.PdfDocument(pdf)
    try:
        tot = laatste if laatste and laatste <= len(document) else len(document)
        afbeeldingen: list[bytes] = []

        for nummer in range(eerste, tot + 1):
            blad = document[nummer - 1]
            plaatje = blad.render(scale=SCHAAL).to_pil()
            if plaatje.width > MAX_BREEDTE:
                hoogte = round(plaatje.height * MAX_BREEDTE / plaatje.width)
                plaatje = plaatje.resize((MAX_BREEDTE, hoogte))

            buffer = io.BytesIO()
            plaatje.convert("RGB").save(buffer, format="JPEG", quality=85)
            afbeeldingen.append(buffer.getvalue())

        return afbeeldingen
    finally:
        document.close()


def lees_folder(
    pdf: bytes,
    *,
    winkel_id: int,
    winkel_naam: str,
    vraagbaak: Vraagbaak | None = None,
    eerste_pagina: int = 1,
    laatste_pagina: int = 0,
    folder_url: str | None = None,
    bron_voorvoegsel: str = "folder",
) -> Folderoogst:
    """
    Leest een hele folder uit en levert er onze eigen aanbiedingen bij op.

    Gaat één pagina mis, dan gaat de rest gewoon door: liever een folder waarin
    een pagina ontbreekt dan helemaal geen aanbiedingen. Loopt de AI helemaal
    vast (geen sleutels meer), dan stopt het lezen wel — verder proberen kost
    dan alleen maar tijd.
    """
    vraagbaak = vraagbaak or Vraagbaak()
    kan, reden = vraagbaak.beschikbaar()
    if not kan:
        raise RuntimeError(f"De folder van {winkel_naam} kan niet gelezen worden: {reden}")

    afbeeldingen = paginas_uit_pdf(pdf, eerste_pagina, laatste_pagina)
    log.info("%s: folder van %s pagina's klaargezet om te laten aflezen.",
             winkel_naam, len(afbeeldingen))

    oogst = Folderoogst(paginas=len(afbeeldingen))
    periodes: list[tuple[str, str]] = []
    gevonden: dict[str, Aanbieding] = {}
    vandaag = date.today().isoformat()

    for volgnummer, afbeelding in enumerate(afbeeldingen, start=eerste_pagina):
        antwoord = vraagbaak.vraag_over_afbeelding(
            afbeelding,
            OPDRACHT.format(winkel=winkel_naam, vandaag=vandaag),
            ANTWOORDVORM,
            omschrijving=f"pagina {volgnummer}",
        )

        if not antwoord.gelukt:
            log.warning("%s: pagina %s niet gelezen: %s", winkel_naam, volgnummer, antwoord.fout)
            oogst.fouten.append(f"pagina {volgnummer}: {antwoord.fout}")
            if not vraagbaak.beschikbaar()[0]:
                log.error("%s: het lezen is gestopt bij pagina %s — %s",
                          winkel_naam, volgnummer, vraagbaak.beschikbaar()[1])
                break
            continue

        oogst.gelezen += 1
        pagina = antwoord.inhoud if isinstance(antwoord.inhoud, dict) else {}

        # De periode staat per pagina, en dat is geen formaliteit: een folder van
        # een week bevat vaak pagina's met alleen weekendacties. Die krijgen hier
        # meteen hun eigen kortere periode mee.
        van, tot = _datum(pagina.get("geldig_van")), _datum(pagina.get("geldig_tot"))
        if van and tot and van <= tot:
            periodes.append((van, tot))
        else:
            van = tot = None

        nieuw = 0
        for artikel in pagina.get("artikelen") or []:
            aanbieding = _naar_aanbieding(
                artikel, winkel_id=winkel_id, pagina=volgnummer,
                folder_url=folder_url, voorvoegsel=bron_voorvoegsel,
            )
            if aanbieding is None:
                continue
            aanbieding.geldig_van, aanbieding.geldig_tot = van, tot
            if aanbieding.bron_id not in gevonden:
                nieuw += 1
            gevonden.setdefault(aanbieding.bron_id, aanbieding)

        log.info("%s: pagina %s van %s gelezen — %s aanbiedingen.",
                 winkel_naam, volgnummer, len(afbeeldingen) + eerste_pagina - 1, nieuw)

    oogst.aanbiedingen = list(gevonden.values())
    oogst.geldig_van, oogst.geldig_tot = _folderperiode(periodes)

    # Pagina's waarop geen periode stond, vallen terug op die van de folder.
    for aanbieding in oogst.aanbiedingen:
        if not aanbieding.geldig_van:
            aanbieding.geldig_van = oogst.geldig_van
            aanbieding.geldig_tot = oogst.geldig_tot

    log.info(
        "%s: %s aanbiedingen uit %s van de %s pagina's; %s met kilo- of literprijs. "
        "Kosten: %s AI-vragen, %s tokens.",
        winkel_naam, len(oogst.aanbiedingen), oogst.gelezen, oogst.paginas,
        sum(1 for a in oogst.aanbiedingen if a.prijs_per_eenheid is not None),
        vraagbaak.aanroepen, vraagbaak.tokens,
    )
    return oogst


def _naar_aanbieding(artikel: dict, *, winkel_id: int, pagina: int,
                     folder_url: str | None, voorvoegsel: str) -> Aanbieding | None:
    """Vertaalt één afgelezen artikel naar onze eigen vorm; None bij onbruikbaars."""
    naam = str(artikel.get("product_naam") or "").strip()
    if not naam:
        return None

    normaal = _bedrag(artikel.get("normale_prijs"))
    prijs = _stuksprijs(_bedrag(artikel.get("actie_bedrag")),
                        artikel.get("bedrag_geldt_voor_aantal"))
    actie_tekst = str(artikel.get("actie_tekst") or "").strip() or None

    if prijs is None and normaal is None:
        # Zonder enig bedrag valt er niets te vergelijken; dat is geen aanbieding
        # maar een plaatje.
        return None

    if artikel.get("alleen_met_app"):
        actie_tekst = f"{actie_tekst} (alleen met de app)" if actie_tekst else "alleen met de app"

    aanbieding = maak_aanbieding(
        winkel_id=winkel_id,
        bron_id=f"{voorvoegsel}-p{pagina}-{_sleutelnaam(naam, artikel.get('inhoud'))}",
        product_naam=naam,
        merk=str(artikel.get("merk") or "").strip() or None,
        actie_tekst=actie_tekst,
        actieprijs=prijs,
        normale_prijs=normaal,
        inhoud_tekst=str(artikel.get("inhoud") or "").strip() or None,
        product_url=folder_url,
    )
    return aanbieding


def _stuksprijs(bedrag: float | None, voor_aantal) -> float | None:
    """
    Rekent het afgedrukte bedrag om naar de prijs voor één stuk.

    Bij "1+1 gratis" staat er één bedrag voor twee stuks; wie dat niet deelt,
    zet zo'n aanbieding twee keer zo duur in de lijst als hij is.
    """
    if bedrag is None:
        return None
    try:
        aantal = int(voor_aantal)
    except (TypeError, ValueError):
        aantal = 1
    if aantal < 1 or aantal > 12:            # boven de twaalf is het een leesfout
        aantal = 1
    return round(bedrag / aantal, 4)


def _bedrag(waarde) -> float | None:
    """Een bedrag van nul of minder betekent "niet gelezen", niet "gratis"."""
    try:
        bedrag = float(waarde)
    except (TypeError, ValueError):
        return None
    return round(bedrag, 4) if bedrag > 0 else None


def _sleutelnaam(naam: str, inhoud) -> str:
    """
    Een korte, herkenbare sleutel voor in het bron_id.

    Twee keer dezelfde folder ophalen hoort dezelfde regels op te leveren en geen
    dubbele lijst, dus de sleutel moet uit het artikel zelf komen en niet uit een
    volgnummer.
    """
    ruw = f"{naam} {inhoud or ''}".lower()
    schoon = re.sub(r"[^a-z0-9]+", "-", ruw).strip("-")
    return schoon[:60] or "artikel"


def _datum(waarde) -> str | None:
    """Alleen een echte datum als 2026-08-02 telt; de rest laten we vallen."""
    tekst = str(waarde or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tekst):
        return None
    try:
        date.fromisoformat(tekst)
    except ValueError:
        return None
    return tekst


def _folderperiode(periodes: list[tuple[str, str]]) -> tuple[str | None, str | None]:
    """
    De periode van de folder als geheel: van de eerste dag tot de laatste.

    Niet de meest voorkomende periode, want die zit ernaast: een weekfolder staat
    vol pagina's met alleen weekendacties ("van donderdag 6 t/m zaterdag 8"), en
    dat zijn er zomaar meer dan de ene omslag met de echte looptijd. De vroegste
    begindatum hoort bij de folder, de laatste einddatum ook.

    Staat er nergens een periode, dan blijft hij leeg en vult de bron zelf iets
    in aan de hand van het weeknummer.
    """
    if not periodes:
        return None, None
    return min(van for van, _ in periodes), max(tot for _, tot in periodes)
