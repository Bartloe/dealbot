"""
===============================================================================
 Dealbot — onze eigen productindeling van twee lagen

 Versie      : 1.0
 Reden       : Elke winkel deelt zijn assortiment anders in. Albert Heijn zegt
               "Koffiebonen", Jumbo zegt "lokaal Koffiebonen", Dirk gooit alles
               op één hoop ("Koffie & cacao") en de Vomar-folder levert helemaal
               geen groep. Daardoor stonden er 2606 losse groepsnamen in de
               keuzelijst en vond je met één zoekvraag nooit alle winkels.

               Hier staat daarom één eigen indeling: hoofdgroep en subgroep, in
               onze eigen woorden. Elk product hangt daaronder, ongeacht wat de
               winkel zelf van zijn indeling vindt.
 Datum       : 03-08-2026 22:05

 Onderdelen:
   INDELING             - de eigen indeling: hoofdgroepen met hun subgroepen
   TREFWOORDEN          - woorden in een productnaam die een subgroep verraden
   Plek                 - waar een product hoort: hoofdgroep + eventuele subgroep
   schoon()             - naam opschonen om te kunnen vergelijken
   subgroepen()         - de subgroepen van één hoofdgroep
   hoofdgroep_van()     - bij welke hoofdgroep hoort deze subgroep
   bestaat()            - is dit een bestaande combinatie?
   uit_naam()           - lees de plek af uit de productnaam (het vangnet)
   plaats()             - de eindregel: winkelgroep eerst, productnaam als vangnet

 Voor het proefstuk bevat de indeling alleen de tak "Koffie & thee". Werkt die
 over alle vijf de winkels, dan is de rest herhaalwerk: takken erbij zetten.
===============================================================================
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# -----------------------------------------------------------------------------
# De eigen indeling.
#
# Het skelet komt van de winkelindeling van Albert Heijn (29 afdelingen met 313
# laden): die is al twee lagen diep, staat in gewoon Nederlands en dekt het hele
# supermarktassortiment. Hij is één keer overgenomen en daarna van ons — hij
# verandert dus niet mee als Albert Heijn morgen iets hernoemt.
#
# Twee bewuste afwijkingen van Albert Heijn:
#   - "Koffiecups" en "Koffiepods" zijn samengevoegd. Voor wie boodschappen doet
#     is dat hetzelfde ding; Senseo-pads zijn wél echt iets anders en blijven los.
#   - "Cacao & chocolademelk" hangt hier onder Koffie & thee. Albert Heijn zet
#     het poeder bij de koffie en de pakken melk bij de zuivel. Dirk en Lidl doen
#     het zoals wij ("Koffie & cacao", "Koffie, thee & cacao"), en wie warme
#     dranken zoekt kijkt op één plek.
# -----------------------------------------------------------------------------
INDELING: dict[str, tuple[str, ...]] = {
    "Koffie & thee": (
        "Koffiebonen",
        "Filterkoffie",
        "Koffiecups",
        "Koffiepads",
        "Oploskoffie",
        "IJskoffie",
        "Koffiemelk & creamer",
        "Thee",
        "IJsthee",
        "Cacao & chocolademelk",
        "Koffie- en theebenodigdheden",
    ),
}

# -----------------------------------------------------------------------------
# Een regel uitleg per subgroep, alleen bedoeld voor de AI die de winkelgroepen
# vertaalt. Zonder die uitleg gokt hij bij de randgevallen, en dan landt de ene
# winkel ergens anders dan de andere.
#
# Alleen invullen waar het echt nodig is; de meeste namen spreken voor zich.
# -----------------------------------------------------------------------------
TOELICHTING: dict[str, str] = {
    "Koffiecups": "harde cups en pods: Nespresso, Dolce Gusto, Tassimo. Ook 'koffiepods'.",
    "Koffiepads": "alleen de zachte ronde pads voor een Senseo-apparaat.",
    "Koffiemelk & creamer": "zuivel om ín de koffie te doen, geen koffie.",
    "Thee": "theezakjes en losse thee om te zetten.",
    "IJsthee": "kant-en-klare koude thee in flessen of blikjes, zoals Lipton Ice Tea.",
    "IJskoffie": "kant-en-klare koude koffie in flesjes of bekers, zoals Starbucks.",
    "Cacao & chocolademelk": "cacaopoeder en chocolademelk. Geen chocoladerepen of -pasta.",
    "Koffie- en theebenodigdheden": "filters, koffiesuiker en siropen. Geen apparaten.",
}

# -----------------------------------------------------------------------------
# Trefwoorden: woorden die in een productnaam de subgroep verraden.
#
# Dit is het vangnet voor de twee winkels waar de winkelgroep tekortschiet: Dirk
# (die niet fijner indeelt dan "Koffie & cacao") en de Vomar-folder (die geen
# groep meelevert). Het langste trefwoord dat past wint, zodat "koffiemelk" niet
# als "koffie" wordt gelezen en "theeworst" niet als "thee".
#
# Bewust géén los woord "koffie" of "thee": dat zegt alleen iets over de
# hoofdgroep, niet over de subgroep. Daar is HOOFD_TREFWOORDEN voor.
# -----------------------------------------------------------------------------
TREFWOORDEN: dict[str, tuple[str, ...]] = {
    "Koffiemelk & creamer": (
        "koffiemelk", "koffieroom", "koffiecreamer", "creamer", "coffee creamer",
        "opschuimmelk", "barista melk", "koffie melk",
    ),
    "Koffiebonen": (
        "koffiebonen", "koffie bonen", "espressobonen", "espresso bonen",
        "bonen koffie", "koffieboon", "hele bonen",
    ),
    "Filterkoffie": (
        "filterkoffie", "filter koffie", "snelfiltermaling", "gemalen koffie",
        "koffie gemalen", "filterzakjes koffie",
    ),
    "Koffiecups": (
        "koffiecups", "koffie cups", "nespresso", "dolce gusto", "koffiecapsules",
        "capsules", "koffiepods", "koffie pods", "lungo", "ristretto",
    ),
    "Koffiepads": (
        "koffiepads", "koffie pads", "senseo", "koffiepad",
    ),
    "Oploskoffie": (
        "oploskoffie", "oplos koffie", "instant koffie", "koffie instant",
        "oploscappuccino", "cappuccino poeder", "latte macchiato poeder",
    ),
    "IJskoffie": (
        "ijskoffie", "ijs koffie", "iced coffee", "cold brew", "frappuccino",
        "ice cappuccino", "iced cappuccino", "iced latte", "chilled coffee",
        "koffie klaar om te drinken",
    ),
    "Thee": (
        "thee", "rooibos", "kruidenthee", "groene thee", "zwarte thee",
        "vruchtenthee", "chai", "earl grey", "kamille",
        # Engelse namen komen los in de schappen voor (Lipton, Pickwick). Ze
        # staan hier alleen met een spatie erin: het kale woord "tea" zit ook in
        # "steak" en zou dan een biefstuk bij de thee zetten.
        "green tea", "black tea", "herbal tea",
    ),
    "IJsthee": (
        "ijsthee", "ijs thee", "ice tea", "iced tea", "fuze tea",
    ),
    "Cacao & chocolademelk": (
        "chocolademelk", "chocolade melk", "cacaopoeder", "cacao poeder",
        "chocomel", "cacao", "warme chocolade", "chocolate drink",
    ),
    "Koffie- en theebenodigdheden": (
        "koffiefilters", "koffie filters", "theefilters", "theezakjes leeg",
        "koffiesiroop", "koffiesiropen", "koffiesuiker", "theelichtje",
    ),
}

# Woorden die alleen de hoofdgroep aanwijzen. Nodig wanneer er helemaal geen
# winkelgroep is (de voorgelezen Vomar-folder) en geen enkel trefwoord past.
HOOFD_TREFWOORDEN: dict[str, tuple[str, ...]] = {
    "Koffie & thee": ("koffie", "thee", "espresso", "cappuccino", "cacao", "koffiebonen"),
}

# Woorden die een trefwoord juist ontkrachten. "Theeworst" is worst, "theedoek"
# is een doek en "theelepel" is bestek — geen van drieën heeft met thee te maken.
UITZONDERINGEN: tuple[str, ...] = (
    "theeworst", "theedoek", "theelepel", "theepot", "theeglas", "theemuts",
    "theelicht", "koffiezetapparaat", "koffiemachine", "koffiemolen", "koffiekop",
    "koffiebeker", "chocoladereep", "chocoladeletter",
)


@dataclass(frozen=True)
class Plek:
    """
    Waar een product in onze indeling hangt.

    De subgroep mag leeg zijn: dan weten we wél de hoofdgroep maar niet de
    precieze plek. Dat is eerlijk bij een winkel als Dirk, die zijn koffiebonen
    en zijn cacao in één groep gooit en waarvan de productnaam niets prijsgeeft.
    """

    hoofdgroep: str
    subgroep: str | None = None
    herkomst: str = ""          # 'winkelgroep', 'productnaam' of 'winkelgroep+productnaam'

    @property
    def volledig(self) -> bool:
        return bool(self.subgroep)


def schoon(tekst: str | None) -> str:
    """
    Maakt een naam vergelijkbaar: kleine letters, geen accenten, enkele spaties.

    Jumbo zet bij een deel van zijn groepen "lokaal" ervoor ("lokaal
    Koffiebonen"). Dat voorvoegsel gaat er hier af, zodat die groep op dezelfde
    plek landt als de gewone. Wat het bij Jumbo precies betekent weten we niet,
    maar voor de indeling maakt het geen verschil: het blijven koffiebonen.
    """
    if not tekst:
        return ""
    plat = unicodedata.normalize("NFKD", tekst)
    plat = "".join(teken for teken in plat if not unicodedata.combining(teken))
    plat = plat.lower().replace("&", " en ")
    plat = re.sub(r"[^a-z0-9]+", " ", plat).strip()
    plat = re.sub(r"^lokaal\s+", "", plat)
    return re.sub(r"\s+", " ", plat)


def hoofdgroepen() -> tuple[str, ...]:
    """Alle hoofdgroepen van onze indeling, op volgorde."""
    return tuple(INDELING)


def subgroepen(hoofdgroep: str) -> tuple[str, ...]:
    """De subgroepen onder één hoofdgroep; leeg als die hoofdgroep niet bestaat."""
    return INDELING.get(hoofdgroep, ())


def hoofdgroep_van(subgroep: str | None) -> str | None:
    """Bij welke hoofdgroep hoort deze subgroep? Niets als hij niet bestaat."""
    if not subgroep:
        return None
    for hoofd, subs in INDELING.items():
        if subgroep in subs:
            return hoofd
    return None


def bestaat(hoofdgroep: str | None, subgroep: str | None = None) -> bool:
    """Is dit een combinatie die in onze indeling voorkomt?"""
    if not hoofdgroep or hoofdgroep not in INDELING:
        return False
    return not subgroep or subgroep in INDELING[hoofdgroep]


def _langste_treffer(naam: str, woordenboek: dict[str, tuple[str, ...]]) -> tuple[str | None, int]:
    """
    Zoekt het langste trefwoord dat in de naam voorkomt.

    Het langste wint omdat de korte woorden in de lange zitten: "koffiemelk"
    bevat "koffie", en zonder deze regel zou een pak koffiemelk bij de bonen
    kunnen belanden.
    """
    beste: str | None = None
    lengte = 0
    for groep, woorden in woordenboek.items():
        for woord in woorden:
            plat = schoon(woord)
            if plat and plat in naam and len(plat) > lengte:
                beste, lengte = groep, len(plat)
    return beste, lengte


def uit_naam(product_naam: str | None) -> Plek | None:
    """
    Leest uit de productnaam af waar het product hoort. Het vangnet.

    Dit is minder zeker dan de winkelindeling en wordt daarom alleen gebruikt
    waar die indeling tekortschiet. Bij twijfel geeft deze functie liever niets
    terug dan een gok: een product op de verkeerde plek is vervelender dan een
    product in de restbak.
    """
    naam = schoon(product_naam)
    if not naam:
        return None

    if any(schoon(woord) in naam for woord in UITZONDERINGEN):
        return None

    subgroep, _ = _langste_treffer(naam, TREFWOORDEN)
    if subgroep:
        return Plek(hoofdgroep_van(subgroep) or "", subgroep, herkomst="productnaam")

    hoofdgroep, _ = _langste_treffer(naam, HOOFD_TREFWOORDEN)
    if hoofdgroep:
        return Plek(hoofdgroep, None, herkomst="productnaam")

    return None


def plaats(
    product_naam: str | None,
    uit_winkelgroep: Plek | None = None,
    winkel_heeft_groep: bool = False,
    gemengd: bool = False,
) -> Plek | None:
    """
    De eindregel: waar hangt dit product?

    De winkelgroep is leidend voor de hoofdgroep. Een winkel zet zijn eigen
    product in zijn eigen indeling, dus dat de bonen bij de koffie liggen klopt
    vrijwel altijd — ook bij een grove indeling als die van Dirk.

    Alleen de fijne plek ontbreekt daar. Die mag de productnaam aanvullen, maar
    uitsluitend met een subgroep die ónder de al vastgestelde hoofdgroep hangt.
    Zo kan één verdwaald woord een product nooit naar een heel andere afdeling
    schieten: "Chocomel chocolademelk" in Dirks koffiegroep landt op
    "Cacao & chocolademelk", maar een pak hagelslag dat daar per ongeluk in zit
    blijft gewoon bij de hoofdgroep staan.

    Belangrijk is het verschil tussen drie soorten winkelgroep.

    1. De winkel levert hélemaal geen groep — de voorgelezen Vomar-folder. Dan is
       de productnaam het enige houvast en beslist die alles.
    2. De winkel levert een groep die niet onder onze indeling valt. Dan heeft de
       winkel al gezegd wat voor product het is en gaan we daar niet overheen.
       Anders belandt "Nivea Men Espresso deodorant" bij de koffie.
    3. De groep is gemengd: er ligt van alles door elkaar, waarvan een deel van
       ons is. "IJskoffie en milkshakes" is zo'n groep. Dan telt een product pas
       mee als de naam zelf laat zien dat het erbij hoort — het voordeel van de
       twijfel gaat hier naar de productnaam, niet naar de groep.

    Levert niets een plek op, dan komt het product in de restbak — zichtbaar,
    zodat we kunnen bijsturen.
    """
    if uit_winkelgroep is None:
        return None if winkel_heeft_groep else uit_naam(product_naam)

    uit_de_naam = uit_naam(product_naam)
    past_eronder = bool(
        uit_de_naam
        and uit_de_naam.subgroep
        and hoofdgroep_van(uit_de_naam.subgroep) == uit_winkelgroep.hoofdgroep
    )

    if gemengd:
        if not past_eronder:
            return None
        return Plek(
            uit_winkelgroep.hoofdgroep,
            uit_de_naam.subgroep,          # type: ignore[union-attr]
            herkomst="gemengde winkelgroep+productnaam",
        )

    if uit_winkelgroep.volledig:
        return uit_winkelgroep

    if past_eronder:
        return Plek(
            uit_winkelgroep.hoofdgroep,
            uit_de_naam.subgroep,          # type: ignore[union-attr]
            herkomst="winkelgroep+productnaam",
        )

    return uit_winkelgroep
