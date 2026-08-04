"""
===============================================================================
 Dealbot — winkelgroepen onder onze eigen indeling hangen

 Versie      : 1.1
 Reden       : De vijf ketens hebben samen 2606 groepsnamen, elk in hun eigen
               taal. Ze stuk voor stuk met de hand vertalen is geen doen, en per
               product beslissen is verspilling: een groep vertalen dekt in één
               klap duizenden producten en blijft volgende week gewoon gelden.
               Daarom vraagt dit onderdeel het één keer aan de AI en bewaart het
               antwoord.

               Bijgewerkt nu de indeling het hele assortiment dekt. De opdracht
               vertelde de AI nog dat "hoort er niet bij" het meest voorkomende
               antwoord was — dat gold toen alleen koffie en thee in de indeling
               stonden en zou nu duizenden groepen ten onrechte afwijzen. Ook
               staan de twee regels erbij die dwars door alle takken lopen:
               diepvries wint, en glutenvrij is een eigenschap en geen afdeling.
 Datum       : 04-08-2026 00:05

 Onderdelen:
   Koppeling         - één winkelgroep met de plek waar hij onder valt
   OPDRACHT          - wat we de AI precies vragen
   _vorm()           - de vaste vorm waarin het antwoord moet komen
   vertaal()         - een lijst winkelgroepen langs de AI, in blokken
   _lees_antwoord()  - controleert wat er terugkomt tegen onze eigen indeling

 De AI mag nooit iets verzinnen: elk antwoord wordt getoetst aan de indeling in
 indeling.py. Een hoofd- of subgroep die daar niet in staat wordt weggegooid,
 niet stilzwijgend overgenomen.
===============================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .ai import Vraagbaak
from .indeling import INDELING, TOELICHTING, bestaat, hoofdgroep_van

log = logging.getLogger(__name__)

# Zoveel groepsnamen per vraag. Groot genoeg om er weinig vragen voor nodig te
# hebben, klein genoeg om het antwoord overzichtelijk te houden.
BLOKGROOTTE = 60


@dataclass(frozen=True)
class Koppeling:
    """
    Eén winkelgroep met de plek in onze indeling waar hij onder valt.

    De subgroep mag leeg zijn. Dat is het eerlijke antwoord bij een winkelgroep
    die grover is dan onze indeling: Dirks "Koffie & cacao" bevat zowel bonen
    als cacaopoeder, dus daar valt alleen de hoofdgroep met zekerheid over te
    zeggen. De productnaam vult dat later per product aan.

    Ook de hoofdgroep mag leeg zijn, en dat betekent iets anders dan "onbekend":
    het betekent "bekeken, en deze groep hoort nergens bij ons". Die uitkomst
    wordt net zo goed bewaard als een treffer, want anders gaan dezelfde 2500
    afgewezen groepsnamen elke ronde opnieuw langs de AI.
    """

    winkel_id: int
    productgroep: str
    hoofdgroep: str | None
    subgroep: str | None = None
    gemengd: bool = False
    herkomst: str = "ai"

    def als_rij(self) -> dict[str, Any]:
        return {
            "winkel_id": self.winkel_id,
            "productgroep": self.productgroep,
            "hoofdgroep": self.hoofdgroep,
            "subgroep": self.subgroep,
            "gemengd": self.gemengd,
            "herkomst": self.herkomst,
        }


OPDRACHT = """Je helpt bij het indelen van supermarktproducten.

Hieronder staat onze eigen productindeling van twee lagen, en daaronder een
lijst met groepsnamen die supermarkten zelf gebruiken. Zeg voor elke groepsnaam
onder welke hoofdgroep en subgroep van ONZE indeling hij valt.

ONZE INDELING:
{indeling}

Er zijn vier soorten antwoord mogelijk:

A. De groepsnaam past precies op één van onze subgroepen.
   Vul hoofdgroep én subgroep in, gemengd = false.
   Voorbeeld: "Koffiebonen" -> Koffie & thee / Koffiebonen.

B. De groepsnaam gaat helemaal over onze hoofdgroep, maar is grover dan onze
   subgroepen: alles wat erin ligt hoort bij ons, alleen niet in één hokje.
   Vul alleen de hoofdgroep in, laat subgroep leeg, gemengd = false.
   Voorbeeld: "Koffie & cacao" -> Koffie & thee / (leeg).

C. De groep is gemengd: een deel van wat erin ligt hoort bij ons, een ander deel
   hoort ergens anders thuis.
   Vul de hoofdgroep in, laat subgroep leeg, gemengd = true.
   Voorbeeld: "IJskoffie en milkshakes" -> Koffie & thee / (leeg) / gemengd.
   Voorbeeld: "Drinkyoghurt, chocolademelk, ontbijtdranken" -> ook gemengd.

D. De groepsnaam heeft niets met onze indeling te maken.
   Laat hoofdgroep leeg. Dit antwoord is zeldzaam geworden: onze indeling dekt
   het hele supermarktassortiment. Gebruik het alleen voor wat echt geen
   boodschap is — een dienst, een spaaractie, statiegeld, een afhaalpunt.

REGELS:
- Kies uitsluitend namen die letterlijk in onze indeling staan. Verzin niets.
- Twijfel je tussen B en C, kies dan C. Bij een gemengde groep kijken we daarna
  nog naar de productnaam zelf, dus daar gaat niets verloren.
- Diepvries wint van elke andere afdeling. "Diepvries groente" hoort bij
  Diepvries, niet bij de groente; alleen als de groepsnaam niet zegt dat het uit
  de vriezer komt, gaat het product naar zijn eigen afdeling.
- Glutenvrij, lactosevrij, biologisch en "vrij van" zijn eigenschappen, geen
  afdelingen. "Glutenvrije koekjes" horen gewoon bij de koek. Alleen waar onze
  indeling er zelf een plek voor heeft (halal vlees, lactosevrije kaas) mag je
  die kiezen.
- Let op groepsnamen die misleiden. "Theeworst" is worst en heeft niets met thee
  te maken. "Wasmiddel capsules" zijn geen koffiecups.
- Sommige namen beginnen met "lokaal". Negeer dat woord; het zegt niets over wat
  voor product het is.

GROEPSNAMEN:
{groepen}
"""


def _vorm() -> dict[str, Any]:
    """De vaste vorm van het antwoord, zodat er geen los proza terugkomt."""
    return {
        "type": "object",
        "properties": {
            "koppelingen": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "groepsnaam": {"type": "string"},
                        "hoofdgroep": {"type": "string"},
                        "subgroep": {"type": "string"},
                        "gemengd": {"type": "boolean"},
                    },
                    "required": ["groepsnaam", "hoofdgroep", "subgroep", "gemengd"],
                },
            }
        },
        "required": ["koppelingen"],
    }


def _indeling_als_tekst() -> str:
    """
    Onze indeling in een vorm die de AI kan lezen.

    Met de toelichting erachter waar die er is. Dat scheelt gokwerk bij de
    randgevallen: zonder uitleg landen "koffiepods" en "koffiepads" de ene keer
    bij elkaar en de andere keer los.
    """
    regels = []
    for hoofd, subs in INDELING.items():
        regels.append(f"{hoofd}:")
        for sub in subs:
            uitleg = TOELICHTING.get(sub)
            regels.append(f"  - {sub}" + (f"  ({uitleg})" if uitleg else ""))
    return "\n".join(regels)


def _lees_antwoord(
    inhoud: Any, winkel_id: int, gevraagd: dict[str, str]
) -> tuple[list[Koppeling], int]:
    """
    Zet het antwoord van de AI om in koppelingen, en gooit weg wat niet klopt.

    Er wordt op drie dingen gecontroleerd: is de groepsnaam er eentje die we
    gevraagd hebben, bestaat de hoofdgroep in onze indeling, en hangt de subgroep
    werkelijk onder die hoofdgroep. Zo kan een verzonnen naam nooit in de
    database belanden.

    "Hoort nergens bij" komt als volwaardige koppeling terug, met een lege
    hoofdgroep. Dat is een antwoord dat bewaard hoort te worden — anders wordt
    dezelfde groepsnaam elke ronde opnieuw gevraagd.

    Geeft de koppelingen terug plus het aantal antwoorden dat is afgekeurd.
    """
    koppelingen: list[Koppeling] = []
    afgekeurd = 0

    for regel in (inhoud or {}).get("koppelingen", []):
        if not isinstance(regel, dict):
            afgekeurd += 1
            continue

        naam = (regel.get("groepsnaam") or "").strip()
        origineel = gevraagd.get(naam.lower())
        if not origineel:
            log.debug("Groepsnaam %r is niet gevraagd; overgeslagen.", naam)
            afgekeurd += 1
            continue

        hoofd = (regel.get("hoofdgroep") or "").strip()
        if not hoofd:
            koppelingen.append(Koppeling(winkel_id, origineel, None))
            continue

        if not bestaat(hoofd):
            log.debug("Verzonnen hoofdgroep %r bij %r; overgeslagen.", hoofd, origineel)
            afgekeurd += 1
            continue

        sub = (regel.get("subgroep") or "").strip() or None
        if sub and hoofdgroep_van(sub) != hoofd:
            log.debug("Subgroep %r hangt niet onder %r bij %r; alleen de hoofdgroep.",
                      sub, hoofd, origineel)
            sub = None

        # Een gemengde groep heeft per definitie geen vaste subgroep: die moet
        # per product uit de naam komen. Noemt de AI er tóch een, dan valt die
        # weg — anders zou de helft van de groep op de verkeerde plek landen.
        gemengd = bool(regel.get("gemengd"))
        if gemengd:
            sub = None

        koppelingen.append(Koppeling(winkel_id, origineel, hoofd, sub, gemengd))

    return koppelingen, afgekeurd


def vertaal(
    vraagbaak: Vraagbaak,
    winkel_id: int,
    groepen: list[str],
    winkelnaam: str = "",
) -> tuple[list[Koppeling], list[str]]:
    """
    Hangt de groepsnamen van één winkel onder onze indeling.

    Gaat in blokken, zodat één mislukt blok de rest niet meesleept. Wat terugkomt
    zijn álle bekeken groepen — ook die nergens bij horen, met een lege
    hoofdgroep. Die worden net zo goed bewaard, zodat er nooit twee keer naar
    dezelfde groepsnaam gevraagd wordt.
    """
    if not groepen:
        return [], []

    alles: list[Koppeling] = []
    klachten: list[str] = []
    indeling = _indeling_als_tekst()
    vorm = _vorm()

    for start in range(0, len(groepen), BLOKGROOTTE):
        blok = groepen[start:start + BLOKGROOTTE]
        gevraagd = {naam.lower(): naam for naam in blok}
        nummer = start // BLOKGROOTTE + 1

        opdracht = OPDRACHT.format(
            indeling=indeling,
            groepen="\n".join(f"- {naam}" for naam in blok),
        )

        antwoord = vraagbaak.vraag_over_tekst(
            opdracht, vorm, omschrijving=f"{winkelnaam} blok {nummer}"
        )
        if not antwoord.gelukt:
            klacht = f"{winkelnaam or winkel_id} blok {nummer}: {antwoord.fout}"
            log.warning("Groepen niet vertaald — %s", klacht)
            klachten.append(klacht)
            continue

        koppelingen, afgekeurd = _lees_antwoord(antwoord.inhoud, winkel_id, gevraagd)
        alles.extend(koppelingen)
        raak = sum(1 for k in koppelingen if k.hoofdgroep)
        log.info(
            "  %s blok %s: %s van de %s groepen vallen onder onze indeling%s.",
            winkelnaam or winkel_id, nummer, raak, len(blok),
            f", {afgekeurd} antwoord(en) afgekeurd" if afgekeurd else "",
        )

    return alles, klachten


def als_json(koppelingen: list[Koppeling]) -> str:
    """De koppelingen als leesbare tekst, om ze te kunnen nakijken."""
    return json.dumps([k.als_rij() for k in koppelingen], ensure_ascii=False, indent=2)
