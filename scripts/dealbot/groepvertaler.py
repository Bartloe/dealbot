"""
===============================================================================
 Dealbot — winkelgroepen onder onze eigen indeling hangen

 Versie      : 2.1
 Reden       : De AI kende één soort "past niet precies": gemengd. Daar viel
               zowel "Soepen" onder (grof, maar de afdeling staat vast) als
               "Glutenvrij" (die producten liggen door de hele winkel). Beide
               werden hetzelfde behandeld, en dat kostte 2489 producten: die van
               de grove groepen verdwenen omdat de productnaam niets bewees.

               De AI maakt nu het onderscheid. Een grove groep levert gewoon zijn
               afdeling; die is het vangnet als de productnaam zwijgt. Een
               eigenschapgroep levert géén afdeling — daar zou elke afdeling een
               gok zijn — en daar beslist alleen de productnaam, vrij over alle
               afdelingen heen.
 Datum       : 06-08-2026 01:20

 Vorige      : Een winkelgroep leverde tot nu toe alleen een afdeling en een
               lade op. Het detail dat de winkel er zelf bij zette ging verloren:
               "Toiletpapier Vochtig" werd Huishouden / Toiletpapier, en het
               woord "vochtig" verdween. Daardoor kon je in je profiel wel het
               toiletpapier volgen maar niet alleen het vochtige.

               Dat woord wordt nu bewaard als kenmerk. Het is niet zomaar het
               restje van de groepsnaam: de AI zet het in ónze taal, en krijgt
               de kenmerken die de lade al kent mee met de opdracht om er een
               te hergebruiken als het hetzelfde ding is. Zo levert "Toiletpapier
               - vochtig" bij Albert Heijn hetzelfde kenmerk op als "vochtig
               toiletpapier" bij Jumbo, en krijg je één knopje in plaats van
               drie.
 Datum       : 05-08-2026 14:55

 Onderdelen:
   Koppeling         - één winkelgroep met de plek waar hij onder valt
   OPDRACHT          - wat we de AI precies vragen
   _vorm()           - de vaste vorm waarin het antwoord moet komen
   vertaal()         - een lijst winkelgroepen langs de AI, in blokken
   _lees_antwoord()  - controleert wat er terugkomt tegen onze eigen indeling

 De AI mag nooit iets verzinnen: elk antwoord wordt getoetst aan de indeling in
 indeling.py. Een hoofd- of subgroep die daar niet in staat wordt weggegooid,
 niet stilzwijgend overgenomen. Voor het kenmerk geldt hetzelfde langs een
 andere weg: dat wordt door kenmerken.py opgeschoond en op een al bestaand woord
 van die lade laten vallen.
===============================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from .ai import Vraagbaak
from .indeling import INDELING, TOELICHTING, bestaat, hoofdgroep_van
from .kenmerken import Woordenlijst

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

    Een eigenschapgroep heeft óók geen hoofdgroep, maar om een andere reden: de
    naam noemt geen afdeling maar een eigenschap ("Glutenvrij", "Kerst"), en die
    producten liggen door de hele winkel. Het verschil met "hoort nergens bij
    ons" is dat de producten hier wél meetellen — alleen moet de productnaam
    zelf vertellen waar ze horen.
    """

    winkel_id: int
    productgroep: str
    hoofdgroep: str | None
    subgroep: str | None = None
    eigenschapgroep: bool = False
    herkomst: str = "ai"

    # Wat deze winkelgroep binnen de lade verbijzondert, in onze eigen woorden.
    # Meestal leeg: een groep die precies één lade dekt heeft niets te
    # verbijzonderen. Alleen zinvol naast een subgroep, want zonder lade is
    # "vochtig" niet te plaatsen.
    kenmerk: str | None = None

    def als_rij(self) -> dict[str, Any]:
        return {
            "winkel_id": self.winkel_id,
            "productgroep": self.productgroep,
            "hoofdgroep": self.hoofdgroep,
            "subgroep": self.subgroep,
            "kenmerk": self.kenmerk,
            "eigenschapgroep": self.eigenschapgroep,
            "herkomst": self.herkomst,
        }


OPDRACHT = """Je helpt bij het indelen van supermarktproducten.

Hieronder staat onze eigen productindeling van twee lagen, en daaronder een
lijst met groepsnamen die supermarkten zelf gebruiken. Zeg voor elke groepsnaam
onder welke hoofdgroep en subgroep van ONZE indeling hij valt.

ONZE INDELING:
{indeling}

Er zijn vier soorten antwoord mogelijk. De hoofdvraag die ze uit elkaar houdt:
KUN JE AAN DE GROEPSNAAM ZIEN IN WELKE AFDELING DIT LIGT, zonder de producten
zelf te zien? Bij "Soepen" kan dat. Bij "Glutenvrij" niet — dat ligt door de
hele winkel verspreid.

A. De groepsnaam past precies op één van onze subgroepen.
   Vul hoofdgroep én subgroep in, eigenschapgroep = false.
   Voorbeeld: "Koffiebonen" -> Koffie & thee / Koffiebonen.

B. De groepsnaam wijst wél onze afdeling aan, maar is grover dan onze
   subgroepen. Dit is het gewone geval en veruit het meest voorkomende antwoord.
   Vul alleen de hoofdgroep in, laat subgroep leeg, eigenschapgroep = false.
   Voorbeeld: "Koffie & cacao" -> Koffie & thee / (leeg).
   Voorbeeld: "Soepen" -> Soepen, sauzen & smaakmakers / (leeg).
   Kies B ook als er iets in de groep ligt dat er strikt genomen niet bij hoort.
   In "IJskoffie en milkshakes" zit een milkshake die eigenlijk zuivel is, maar
   de afdeling Koffie & thee klopt voor het grootste deel van de groep, en dat
   is genoeg. We proberen niet elk product apart goed te krijgen; we proberen de
   groep in de goede afdeling te zetten.

C. Eigenschapgroep: de naam zegt niet WAT voor product het is, maar wat het
   ergens van heeft, waar het voor bedoeld is of wanneer je het koopt. Zulke
   producten liggen door de hele winkel verspreid, dus er is geen afdeling om
   te noemen.
   Laat hoofdgroep én subgroep leeg, eigenschapgroep = true.
   Voorbeeld: "Glutenvrij" -> er is glutenvrij brood, glutenvrije pasta en
   glutenvrij bier; één afdeling bestaat niet. Eigenschapgroep.
   Voorbeeld: "Kerst", "Cadeau", "Sinterklaas", "Aanbiedingen van de week".
   Voorbeeld: "High protein", "Suikervrij", "Natuurlijke voeding".
   Voorbeeld: nietszeggende namen die alleen een vorm, kleur of smaak noemen:
   "Wit", "Zoet", "Stukken", "Spray", "Navulling", "Portieverpakkingen". Een
   winkel gebruikt die als filter naast iets anders; los zeggen ze niets. Bij
   "Zoet" kan zowel jam als dessertwijn horen.
   Let op: staat er wél een productsoort bij de eigenschap, dan is het gewoon
   antwoord A of B. "Glutenvrije koek" is koek, "Biologisch zuivel & kaas" is
   zuivel, "Kerst desserts" zijn desserts.

D. De groepsnaam heeft niets met onze indeling te maken.
   Laat hoofdgroep leeg, eigenschapgroep = false. Dit antwoord is zeldzaam
   geworden: onze indeling dekt het hele supermarktassortiment. Gebruik het
   alleen voor wat echt geen boodschap is — een dienst, een spaaractie,
   statiegeld, een afhaalpunt.

HET KENMERK:

Onze subgroepen zijn soms grover dan de groepsnaam van de winkel. "Toiletpapier
Vochtig" valt onder onze subgroep Toiletpapier, maar het woord "vochtig" zegt
iets wat wij anders kwijtraken. Zet dat woord in het veld "kenmerk".

- Eén woord, hooguit twee. In het Nederlands, kleine letters, enkelvoud waar dat
  kan: "vochtig", "pads", "capsules", "halfvol", "lactosevrij", "gerookt".
- Laat het leeg als de groepsnaam niets toevoegt aan onze subgroep. Dat is het
  normale geval. "Koffiebonen" onder Koffiebonen heeft geen kenmerk nodig.
- Herhaal de subgroep niet. Bij "Toiletpapier Vochtig" is het kenmerk "vochtig",
  niet "toiletpapier vochtig".
- Kies géén kenmerk bij antwoord B, C of D: zonder vaste subgroep is er niets om
  het onder te hangen. Bij een eigenschapgroep geldt dat dubbel: daar is zelfs
  de afdeling nog niet bekend.
- Woorden als "overig", "diversen" en "algemeen" zijn geen kenmerk. Laat leeg.

BELANGRIJK — deze kenmerken kennen we al. Gaat jouw groepsnaam over hetzelfde
ding, gebruik dan exact het woord dat er al staat en verzin geen synoniem:

{kenmerken}

REGELS:
- Kies uitsluitend namen die letterlijk in onze indeling staan. Verzin niets.
- Twijfel je tussen B en C, kies dan B. Kun je een afdeling noemen die voor het
  merendeel van de groep klopt, noem hem dan: dan zijn die producten in elk
  geval te vinden. C is alleen voor namen waarbij élke afdeling een gok is.
- Diepvries wint van elke andere afdeling. "Diepvries groente" hoort bij
  Diepvries, niet bij de groente; alleen als de groepsnaam niet zegt dat het uit
  de vriezer komt, gaat het product naar zijn eigen afdeling.
- Glutenvrij, lactosevrij, biologisch en "vrij van" zijn eigenschappen, geen
  afdelingen. Staat er een productsoort bij, deel dan daarop in: "Glutenvrije
  koekjes" horen gewoon bij de koek. Staat de eigenschap er alleen, dan is het
  antwoord C. Alleen waar onze indeling er zelf een plek voor heeft (halal
  vlees, lactosevrije kaas) mag je die kiezen.
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
                        "kenmerk": {"type": "string"},
                        "eigenschapgroep": {"type": "boolean"},
                    },
                    "required": ["groepsnaam", "hoofdgroep", "subgroep",
                                 "kenmerk", "eigenschapgroep"],
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
    inhoud: Any, winkel_id: int, gevraagd: dict[str, str], woordenlijst: Woordenlijst
) -> tuple[list[Koppeling], int]:
    """
    Zet het antwoord van de AI om in koppelingen, en gooit weg wat niet klopt.

    Er wordt op drie dingen gecontroleerd: is de groepsnaam er eentje die we
    gevraagd hebben, bestaat de hoofdgroep in onze indeling, en hangt de subgroep
    werkelijk onder die hoofdgroep. Zo kan een verzonnen naam nooit in de
    database belanden.

    Het kenmerk gaat langs de woordenlijst. Die schoont het op en laat het vallen
    op een woord dat de lade al kent, zodat er geen twee knopjes voor hetzelfde
    ding ontstaan. Een kenmerk dat niets toevoegt verdwijnt daar stilletjes —
    dat is geen fout maar het normale geval.

    "Hoort nergens bij" komt als volwaardige koppeling terug, met een lege
    hoofdgroep. Dat is een antwoord dat bewaard hoort te worden — anders wordt
    dezelfde groepsnaam elke ronde opnieuw gevraagd.

    Geeft de koppelingen terug plus het aantal antwoorden dat is afgekeurd.
    """
    koppelingen: list[Koppeling] = []
    beantwoord: set[str] = set()
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

        # Elke groepsnaam hoort één antwoord te krijgen. Zet de AI er twee neer
        # — de tweede vaak alleen anders geschreven — dan telt het eerste. Twee
        # regels voor dezelfde groep weigert de database namelijk, en dan gaat
        # ook al het goede werk in datzelfde blok verloren.
        if origineel in beantwoord:
            log.debug("Groepsnaam %r kwam twee keer terug; tweede overgeslagen.", origineel)
            afgekeurd += 1
            continue
        beantwoord.add(origineel)

        # Een eigenschapgroep noemt geen afdeling — dat is precies wat hem
        # eigenschapgroep maakt. Noemt de AI er toch een, dan valt die weg:
        # anders belandt alles wat "Glutenvrij" heet alsnog op één hoop.
        eigenschapgroep = bool(regel.get("eigenschapgroep"))
        if eigenschapgroep:
            koppelingen.append(Koppeling(winkel_id, origineel, None,
                                         eigenschapgroep=True))
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

        # Het kenmerk hangt onder de lade, dus zonder vaste lade vervalt het.
        kenmerk = woordenlijst.pas_in(hoofd, sub, regel.get("kenmerk"))

        koppelingen.append(Koppeling(winkel_id, origineel, hoofd, sub,
                                     kenmerk=kenmerk))

    return koppelingen, afgekeurd


def vertaal(
    vraagbaak: Vraagbaak,
    winkel_id: int,
    groepen: list[str],
    winkelnaam: str = "",
    bewaar: Callable[[list[Koppeling]], None] | None = None,
    woordenlijst: Woordenlijst | None = None,
) -> tuple[list[Koppeling], list[str]]:
    """
    Hangt de groepsnamen van één winkel onder onze indeling.

    Gaat in blokken, zodat één mislukt blok de rest niet meesleept. Wat terugkomt
    zijn álle bekeken groepen — ook die nergens bij horen, met een lege
    hoofdgroep. Die worden net zo goed bewaard, zodat er nooit twee keer naar
    dezelfde groepsnaam gevraagd wordt.

    Wie een "bewaar" meegeeft, krijgt elk blok meteen aangeboden zodra het binnen
    is. Dat is er niet voor niets: bij de eerste grote ronde liep het opslaan aan
    het eind vast en waren veertig AI-vragen in één klap kwijt, terwijl de
    dagvoorraad vragen beperkt is. Wat vertaald is, hoort vertaald te blijven.

    De woordenlijst gaat over alle winkels heen en groeit tijdens het vertalen
    door: wat blok 1 aan kenmerken oplevert, krijgt blok 2 mee in zijn opdracht.
    Daarom staat de opdracht binnen de lus en niet erbuiten — bij de eerste ronde
    is de lijst nog leeg en moet hij zich juist tijdens het werk vullen.
    """
    if not groepen:
        return [], []

    if woordenlijst is None:
        woordenlijst = Woordenlijst()

    alles: list[Koppeling] = []
    klachten: list[str] = []
    indeling = _indeling_als_tekst()
    vorm = _vorm()

    for start in range(0, len(groepen), BLOKGROOTTE):
        blok = groepen[start:start + BLOKGROOTTE]
        gevraagd = {naam.lower(): naam for naam in blok}
        nummer = start // BLOKGROOTTE + 1

        bekend = woordenlijst.als_tekst()
        opdracht = OPDRACHT.format(
            indeling=indeling,
            kenmerken=bekend or "(nog geen; je bent de eerste die ze benoemt)",
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

        koppelingen, afgekeurd = _lees_antwoord(
            antwoord.inhoud, winkel_id, gevraagd, woordenlijst
        )
        alles.extend(koppelingen)

        if bewaar and koppelingen:
            bewaar(koppelingen)

        raak = sum(1 for k in koppelingen if k.hoofdgroep)
        met_kenmerk = sum(1 for k in koppelingen if k.kenmerk)
        log.info(
            "  %s blok %s: %s van de %s groepen vallen onder onze indeling%s%s.",
            winkelnaam or winkel_id, nummer, raak, len(blok),
            f", {met_kenmerk} met een kenmerk" if met_kenmerk else "",
            f", {afgekeurd} antwoord(en) afgekeurd" if afgekeurd else "",
        )

    return alles, klachten


def als_json(koppelingen: list[Koppeling]) -> str:
    """De koppelingen als leesbare tekst, om ze te kunnen nakijken."""
    return json.dumps([k.als_rij() for k in koppelingen], ensure_ascii=False, indent=2)
